import os
import logging
from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiTypes

from apps.events.models import Event
from apps.media.models import Photo, FaceIndex
from apps.media.serializers import MultiFileUploadSerializer
from apps.participants.models import Participant
from apps.faces.utils import extract_embeddings
from apps.faces.tasks import match_participant_to_event

logger = logging.getLogger(__name__)

def make_thumbnail(file_obj):
    """Génère une miniature carrée/redimensionnée max 400x400 avec correction d'orientation EXIF via Pillow"""
    try:
        file_obj.seek(0)
        img = Image.open(file_obj)
        # Corriger automatiquement la rotation de l'appareil photo/smartphone via EXIF
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        thumb_io = BytesIO()
        img.save(thumb_io, format="JPEG", quality=85)
        base_name = os.path.basename(file_obj.name)
        name, _ = os.path.splitext(base_name)
        return ContentFile(thumb_io.getvalue(), name=f"{name}_thumb.jpg")
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la miniature: {e}")
        return None

from apps.media.validators import validate_uploaded_image

from apps.organizations.permissions import IsOrganizationMember

class AdminMediaUploadView(APIView):
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
            "3. Détecte tous les visages et génère les embeddings 512D (`FaceIndex`).\n"
            "4. Actualise automatiquement le matching pour les participants déjà inscrits."
        ),
        request=MultiFileUploadSerializer,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    def post(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        from apps.organizations.permissions import get_user_organization
        user_org = get_user_organization(request.user)
        # Vérification Multi-Tenant : superuser OU tout membre actif de l'organisation (owner, manager, photographer)
        if not (request.user.is_superuser or (event.organization and event.organization == user_org)):
            return Response({"detail": "Vous n'avez pas l'autorisation d'ajouter des photos à cet événement."}, status=status.HTTP_403_FORBIDDEN)
        files = request.FILES.getlist("files")
        if not files:
            single_file = request.FILES.get("file")
            if single_file:
                files = [single_file]

        if not files:
            return Response({"error": "Aucun fichier reçu (champ 'files' attendu)."}, status=status.HTTP_400_BAD_REQUEST)

        processed_count = 0
        for uploaded_file in files:
            try:
                # 0. Validation de sécurité du fichier
                validate_uploaded_image(uploaded_file, max_mb=25)

                # 1. Génération de la miniature avec correction EXIF
                thumb_content = make_thumbnail(uploaded_file)
                uploaded_file.seek(0)

                # 2. Sauvegarde de la Photo
                photo = Photo(
                    event=event,
                    file=uploaded_file,
                    is_public=True,
                )
                if thumb_content:
                    photo.thumbnail = thumb_content
                photo.save()

                # 3. Détection et extraction des visages
                try:
                    if photo.file and os.path.exists(photo.file.path):
                        face_results = extract_embeddings(photo.file.path)
                        for face_data in face_results:
                            FaceIndex.objects.create(
                                photo=photo,
                                embedding=face_data["embedding"],
                                bbox=face_data.get("bbox"),
                            )
                except Exception as ex_face:
                    logger.warning(f"Erreur d'indexation faciale sur photo {photo.id}: {ex_face}")

                processed_count += 1
            except Exception as e:
                logger.error(f"Erreur lors du traitement du fichier {uploaded_file.name}: {e}")

        # 4. Actualiser le matching pour les participants déjà enregistrés avec selfie
        if processed_count > 0:
            existing_participants = Participant.objects.filter(face_reference__isnull=False)
            for p in existing_participants:
                try:
                    match_participant_to_event.delay(p.id, event.slug)
                except Exception:
                    match_participant_to_event(p.id, event.slug)

        return Response({"received": processed_count}, status=status.HTTP_201_CREATED)

class AdminMediaDeleteView(APIView):
    permission_classes = [IsOrganizationMember]

    @extend_schema(
        tags=["Administration"],
        summary="Suppression d'une photo",
        description="Supprime la photo et tous ses index faciaux associés.",
        responses={200: OpenApiTypes.OBJECT}
    )
    def delete(self, request, pk):
        photo = get_object_or_404(Photo, pk=pk)
        # Vérification Multi-Tenant
        is_owner = hasattr(request.user, "organization") and photo.event.organization == request.user.organization
        if not (request.user.is_staff or is_owner):
            return Response({"detail": "Vous n'avez pas l'autorisation de supprimer cette photo."}, status=status.HTTP_403_FORBIDDEN)
        if photo.file:
            photo.file.delete(save=False)
        if photo.thumbnail:
            photo.thumbnail.delete(save=False)
        photo.delete()
        return Response({"message": "Photo supprimée avec succès."}, status=status.HTTP_200_OK)
