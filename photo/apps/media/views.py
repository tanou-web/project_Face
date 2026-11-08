"""
Vues opérationnelles pour l'upload, le traitement et la suppression des médias d'événements.

Ce module orchestre le pipeline complet d'ingestion de photos :
1. `make_thumbnail` : Génération de miniatures avec redressement automatique de l'orientation EXIF.
2. `AdminMediaUploadView` : Réception de lots de photos, validation de sécurité, extraction biométrique
   et déclenchement de la réconciliation asynchrone Celery avec les participants.
3. `AdminMediaDeleteView` : Suppression étanche d'une photo et nettoyage effectif des fichiers sur disque.
"""

import os
import logging
from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiTypes

from apps.events.models import Event
from apps.media.models import Photo
from apps.media.serializers import MultiFileUploadSerializer, PhotoPatchSerializer, AdminPhotoListSerializer
from apps.media.validators import validate_uploaded_image
from apps.faces.tasks import index_event_photos
from apps.organizations.permissions import IsOrganizationMember, get_user_organization

logger = logging.getLogger(__name__)


def make_thumbnail(file_obj):
    """
    Génère une miniature allégée (max 400x400) au format JPEG.

    Traitement critique d'orientation :
    Les smartphones et reflex modernes enregistrent l'orientation de prise de vue
    dans les métadonnées EXIF (orientation 3, 6 ou 8). Si l'image n'est pas redressée
    via `ImageOps.exif_transpose`, la photo apparaît tournée de 90° ou 180° dans le navigateur.
    La conversion en mode 'RGB' évite toute exception lors de l'enregistrement en JPEG
    si la photo originale contient un canal alpha transparent (RGBA/PNG).
    """
    try:
        file_obj.seek(0)
        img = Image.open(file_obj)
        # Redressement automatique selon les métadonnées de rotation du capteur photo
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        # Rééchantillonnage de haute fidélité LANCZOS pour préserver le piqué des visages
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        thumb_io = BytesIO()
        img.save(thumb_io, format="JPEG", quality=85)
        base_name = os.path.basename(file_obj.name)
        name, _ = os.path.splitext(base_name)
        return ContentFile(thumb_io.getvalue(), name=f"{name}_thumb.jpg")
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la miniature: {e}")
        return None


class AdminMediaUploadView(APIView):
    """
    Point d'entrée principal pour l'envoi de photos de reportage par les photographes.
    Accepte soit un champ unique 'file', soit un envoi multiple 'files'.
    Gère la chaîne complète : Sécurité -> Miniature -> Sauvegarde -> IA faciale -> Celery.
    """
    permission_classes = [IsOrganizationMember]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = 'admin_media'

    @extend_schema(
        tags=["Administration"],
        summary="Upload multiple de photos avec indexation faciale",
        description=(
            "Téléversement d'une ou plusieurs photos pour un événement (champ `files`).\n"
            "Pour chaque fichier :\n"
            "1. Enregistre le média original.\n"
            "2. Crée la miniature Pillow (400x400 max) avec correction EXIF.\n"
            "3. Met en file l'extraction des visages et des embeddings 512D (`FaceIndex`).\n"
            "4. Actualise le matching en tâche de fond pour les participants déjà inscrits."
        ),
        request=MultiFileUploadSerializer,
        responses={
            201: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            503: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        user_org = get_user_organization(request.user)

        # Contrôle multi-tenant : L'utilisateur doit appartenir à l'organisation de l'événement
        # (les rôles owner, manager et photographer sont tous autorisés à uploader des médias)
        if not (request.user.is_superuser or (event.organization and event.organization == user_org)):
            return Response(
                {"detail": "Vous n'avez pas l'autorisation d'ajouter des photos à cet événement."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Récupération tolérante des fichiers envoyés sous le nom 'files' ou 'file'
        files = request.FILES.getlist("files")
        if not files:
            single_file = request.FILES.get("file")
            if single_file:
                files = [single_file]

        if not files:
            return Response({"error": "Aucun fichier reçu (champ 'files' attendu)."}, status=status.HTTP_400_BAD_REQUEST)

        # Option : définir si le lot de photos est public dans la galerie (par défaut True)
        is_public_param = request.data.get("isPublic")
        if is_public_param is None:
            is_public_param = request.data.get("is_public")
        if is_public_param is not None:
            if isinstance(is_public_param, str):
                default_is_public = is_public_param.lower() in ("true", "1", "yes")
            else:
                default_is_public = bool(is_public_param)
        else:
            default_is_public = True

        processed_count = 0
        processed_photo_ids = []
        upload_errors = []
        server_errors = []
        indexing_errors = []
        for uploaded_file in files:
            try:
                # 0. Validation stricte de sécurité (taille, extension, type MIME, intégrité Pillow)
                validate_uploaded_image(uploaded_file, max_mb=25)

                # 1. Génération de la miniature avec redressement EXIF
                thumb_content = make_thumbnail(uploaded_file)
                uploaded_file.seek(0)

                # 2. Sauvegarde de la Photo rattachée à l'événement
                photo = Photo(
                    event=event,
                    file=uploaded_file,
                    is_public=default_is_public,
                )
                if thumb_content:
                    photo.thumbnail = thumb_content
                photo.save()
                processed_photo_ids.append(photo.pk)
                processed_count += 1
            except ValidationError as exc:
                upload_errors.append({
                    "file": uploaded_file.name,
                    "error": str(exc.detail),
                })
            except Exception:
                logger.exception("Erreur lors du traitement du fichier %s.", uploaded_file.name)
                server_errors.append(uploaded_file.name)
                upload_errors.append({
                    "file": uploaded_file.name,
                    "error": "Le fichier n'a pas pu être enregistré.",
                })

        if processed_photo_ids:
            try:
                index_event_photos.delay(event.slug, processed_photo_ids)
            except Exception:
                logger.exception(
                    "Photos %s enregistrées, mais impossible de mettre leur indexation en file.",
                    processed_photo_ids,
                )
                indexing_errors.append({
                    "photoIds": processed_photo_ids,
                    "error": "Photos enregistrées, mais indexation non planifiée. Vérifiez le worker Celery et Redis.",
                })

        response_data = {"received": processed_count}
        if processed_count:
            response_data["indexing"] = "queued"
        if indexing_errors:
            response_data["indexing"] = "unavailable"
            response_data["indexingErrors"] = indexing_errors
        if upload_errors:
            response_data["uploadErrors"] = upload_errors
        if processed_count:
            return Response(response_data, status=status.HTTP_201_CREATED)
        if server_errors:
            return Response(response_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Administration"],
        summary="Lister toutes les photos d'un événement (publiques + privées)",
        description=(
            "Retourne la liste intégrale des photos d'un événement, qu'elles soient publiques ou privées.\n"
            "Indispensable pour l'organisateur qui souhaite retrouver et réactiver une photo passée en privé.\n"
            "Chaque photo est représentée par : `id`, `thumbnail`, `isPublic`, `legend`, `createdAt`."
        ),
        responses={200: AdminPhotoListSerializer(many=True)}
    )
    def get(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        user_org = get_user_organization(request.user)

        # Contrôle multi-tenant
        if not (request.user.is_superuser or (event.organization and event.organization == user_org)):
            return Response(
                {"detail": "Vous n'avez pas l'autorisation de consulter les médias de cet événement."},
                status=status.HTTP_403_FORBIDDEN
            )

        photos = (
            Photo.objects
            .filter(event=event)
            .order_by("-created_at")
            .only("id", "thumbnail", "file", "is_public", "legend", "created_at")
        )
        serializer = AdminPhotoListSerializer(photos, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminMediaDeleteView(APIView):
    """
    Gestion individuelle d'une photo : modification (visibilité publique / légende) ou suppression.
    """
    permission_classes = [IsOrganizationMember]

    @extend_schema(
        tags=["Administration"],
        summary="Modifier la visibilité ou la légende d'une photo",
        description="Permet à l'organisateur de choisir si une photo est exposée dans la galerie publique (`isPublic: true/false`) et d'éditer sa légende.",
        request=PhotoPatchSerializer,
        responses={200: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT}
    )
    def patch(self, request, pk):
        photo = get_object_or_404(Photo, pk=pk)
        user_org = get_user_organization(request.user)
        is_member = request.user.is_superuser or (photo.event.organization and photo.event.organization == user_org)
        if not is_member:
            return Response(
                {"detail": "Vous n'avez pas l'autorisation de modifier cette photo."},
                status=status.HTTP_403_FORBIDDEN
            )

        is_public_param = request.data.get("isPublic")
        if is_public_param is None:
            is_public_param = request.data.get("is_public")
        if is_public_param is not None:
            if isinstance(is_public_param, str):
                photo.is_public = is_public_param.lower() in ("true", "1", "yes")
            else:
                photo.is_public = bool(is_public_param)

        if "legend" in request.data:
            photo.legend = request.data["legend"]

        photo.save()
        return Response({
            "id": photo.id,
            "isPublic": photo.is_public,
            "legend": photo.legend,
            "message": "Photo mise à jour avec succès."
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Administration"],
        summary="Suppression d'une photo",
        description="Supprime la photo et tous ses index faciaux associés.",
        responses={200: OpenApiTypes.OBJECT}
    )
    def delete(self, request, pk):
        photo = get_object_or_404(Photo, pk=pk)
        # Vérification Multi-Tenant : seuls les membres de l'organisation hôte peuvent supprimer
        user_org = get_user_organization(request.user)
        is_owner = request.user.is_superuser or (photo.event.organization and photo.event.organization == user_org)
        if not is_owner:
            return Response(
                {"detail": "Vous n'avez pas l'autorisation de supprimer cette photo."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Suppression des fichiers physiques sur le disque pour libérer l'espace de stockage
        if photo.file:
            photo.file.delete(save=False)
        if photo.thumbnail:
            photo.thumbnail.delete(save=False)
        # Suppression en base (entraîne en cascade la suppression des FaceIndex et PhotoMatch)
        photo.delete()
        return Response({"message": "Photo supprimée avec succès."}, status=status.HTTP_200_OK)
