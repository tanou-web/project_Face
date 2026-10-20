"""
Vues pour l'enregistrement des participants, l'ingestion biométrique et la conformité RGPD.

Ce module gère le cycle de vie complet des invités :
1. `_check_participant_ownership` : Authentification allégée sans mot de passe via jeton cryptographique SHA-256.
2. `ParticipantView` : Identification ou inscription (Upsert) basée sur le numéro WhatsApp.
3. `FaceReferenceView` : Ingestion sécurisée du selfie, extraction de l'embedding 512D et destruction de l'image source.
4. `ParticipantDeleteView` : Droit à l'oubli intégral (effacement complet des données personnelles).
"""

import logging
import hashlib
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.participants.models import Participant, FaceReference
from apps.participants.serializers import ParticipantSerializer
from apps.participants.utils import normalize_phone, validate_phone
from apps.media.serializers import SingleFileUploadSerializer
from apps.media.validators import validate_uploaded_image
from apps.events.models import Event
from apps.faces.utils import validate_selfie, extract_single_embedding
from apps.faces.tasks import match_participant_to_event

logger = logging.getLogger(__name__)


def _check_participant_ownership(request, participant: Participant) -> bool:
    """
    Vérifie la légitimité de l'usager à modifier ou supprimer ses données personnelles.

    Mécanisme d'autorisation RGPD :
    Les participants n'ayant pas de mot de passe à mémoriser pour simplifier leur parcours,
    le client frontend transmet un jeton de preuve dans l'en-tête HTTP 'X-Participant-Token'
    (calculé par empreinte SHA-256 de son numéro de téléphone).
    Les administrateurs système (is_staff) sont également autorisés à effectuer ces opérations.
    """
    if request.user and request.user.is_authenticated and request.user.is_staff:
        return True
    token = request.headers.get("X-Participant-Token", "")
    expected = hashlib.sha256(participant.phone.encode()).hexdigest()
    return token == expected


class ParticipantView(APIView):
    """
    Point d'entrée pour l'identification ou l'inscription (Upsert) des participants.
    Si le numéro existe déjà, les coordonnées sont mises à jour sans créer de doublon.
    """
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(
        tags=["Participants"],
        summary="Identifier ou enregistrer un participant (Login / Upsert)",
        description=(
            "Enregistre un participant ou retourne son profil s'il existe déjà grâce à son numéro WhatsApp (`phone`).\n"
            "Le numéro est automatiquement normalisé au format E.164 (+226XXXXXXXXX).\n"
            "Si aucun indicatif n'est fourni, +226 (Burkina Faso) est ajouté par défaut.\n"
            "Retourne l'ID unique requis pour les interactions suivantes."
        ),
        request=ParticipantSerializer,
        responses={
            201: ParticipantSerializer,
            200: ParticipantSerializer,
            400: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request):
        first_name = request.data.get("firstName", "").strip()
        last_name = request.data.get("lastName", "").strip()
        phone_raw = request.data.get("phone", "").strip()

        if not phone_raw:
            return Response(
                {"error": "Le numéro de téléphone WhatsApp est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Normalisation automatique au format international E.164 (+226...)
        phone_result = validate_phone(phone_raw)
        if not phone_result["valid"]:
            return Response(
                {"error": phone_result["error"]},
                status=status.HTTP_400_BAD_REQUEST
            )
        phone = phone_result["phone"]

        # Création ou récupération idempotente (Upsert)
        participant, created = Participant.objects.get_or_create(
            phone=phone,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
            }
        )

        # Si le participant existait déjà, mise à jour des noms si modifiés
        if not created:
            updated = False
            if first_name and participant.first_name != first_name:
                participant.first_name = first_name
                updated = True
            if last_name and participant.last_name != last_name:
                participant.last_name = last_name
                updated = True
            if updated:
                participant.save()

        serializer = ParticipantSerializer(participant)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class FaceReferenceView(APIView):
    """
    Ingestion du selfie biométrique de référence et gestion du consentement.
    - POST : Réception du selfie, validation qualité, extraction vectorielle 512D et destruction du fichier source.
    - DELETE : Révocation du consentement biométrique (suppression de l'empreinte faciale).
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = 'face_upload'

    @extend_schema(
        tags=["Participants"],
        summary="Uploader le selfie de référence",
        description=(
            "Reçoit le selfie de référence du participant (JPEG ou PNG via champ `file`).\n"
            "1. Vérifie la qualité (taille >= 200x200, netteté >= 50, 1 seul visage centré).\n"
            "2. Extrait l'embedding 512 dimensions InsightFace.\n"
            "3. **Supprime immédiatement l'image brute (conformité RGPD)**.\n"
            "4. Déclenche le matching asynchrone sur l'événement (`?event={slug}`)."
        ),
        request=SingleFileUploadSerializer,
        parameters=[
            OpenApiParameter(
                name="event",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Slug de l'événement concerné pour le matching ciblé"
            )
        ],
        responses={
            202: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request, pk):
        participant = get_object_or_404(Participant, pk=pk)
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "Aucun fichier image fourni (champ 'file')."}, status=status.HTTP_400_BAD_REQUEST)

        # 0. Validation défensive du fichier (taille max 10 Mo, en-têtes valides)
        try:
            validate_uploaded_image(file, max_mb=10)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        content = file.read()

        # 1. Validation qualité du selfie (visage unique, netteté, dimensions minimales)
        validation = validate_selfie(content)
        if not validation["valid"]:
            return Response({"error": validation["error"]}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Extraction du vecteur biométrique 512D par le modèle IA
        embedding = extract_single_embedding(content)
        if embedding is None:
            return Response({"error": "Impossible d'extraire un visage unique."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Sauvegarde de la projection vectorielle (Privacy-by-Design : zéro photo brute en base)
        FaceReference.objects.update_or_create(
            participant=participant,
            defaults={"embedding": embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)},
        )

        # 4. Suppression immédiate de l'image brute en mémoire vive
        del content

        # 5. Transition d'état : le matching est désormais en attente
        participant.match_status = "pending"
        participant.save()

        # 6. Déclenchement de la comparaison asynchrone via Celery
        event_slug = request.query_params.get("event") or request.data.get("event")
        if event_slug:
            # Matching ciblé sur l'événement actif
            try:
                match_participant_to_event.delay(participant.pk, event_slug)
            except Exception as e:
                logger.warning(f"Celery indisponible, exécution directe: {e}")
                match_participant_to_event(participant.pk, event_slug)
        else:
            # Matching global sur tous les événements actifs
            events = Event.objects.exclude(status="archive")
            for ev in events:
                try:
                    match_participant_to_event.delay(participant.pk, ev.slug)
                except Exception:
                    match_participant_to_event(participant.pk, ev.slug)

        return Response({"status": "processing"}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        tags=["Participants"],
        summary="Supprimer la référence faciale (RGPD)",
        description=(
            "Supprime l'embedding facial du participant et réinitialise son statut à 'no_reference'.\n"
            "Accessible par l'admin (JWT) ou le participant lui-même via header `X-Participant-Token` "
            "(SHA256 de son numéro de téléphone)."
        ),
        responses={200: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT}
    )
    def delete(self, request, pk):
        """Supprime l'empreinte biométrique tout en conservant le profil du participant."""
        participant = get_object_or_404(Participant, pk=pk)
        if not _check_participant_ownership(request, participant):
            return Response(
                {"error": "Accès refusé. Token RGPD ou authentification admin requis."},
                status=status.HTTP_403_FORBIDDEN
            )
        FaceReference.objects.filter(participant=participant).delete()
        participant.match_status = "no_reference"
        participant.save()
        return Response({"message": "Référence faciale supprimée avec succès."}, status=status.HTTP_200_OK)


class ParticipantDeleteView(APIView):
    """
    Mise en œuvre du Droit à l'oubli intégral (Article 17 du RGPD).
    Supprime définitivement le compte usager, son empreinte faciale et l'ensemble de ses correspondances.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Participants"],
        summary="Droit à l'oubli intégral (RGPD)",
        description=(
            "Supprime définitivement le participant ainsi que toutes ses données et associations.\n"
            "Accessible par l'admin (JWT) ou le participant lui-même via header `X-Participant-Token` "
            "(SHA256 de son numéro de téléphone)."
        ),
        responses={200: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT}
    )
    def delete(self, request, pk):
        participant = get_object_or_404(Participant, pk=pk)
        if not _check_participant_ownership(request, participant):
            return Response(
                {"error": "Accès refusé. Token RGPD ou authentification admin requis."},
                status=status.HTTP_403_FORBIDDEN
            )
        # La suppression en cascade efface également FaceReference et PhotoMatch
        participant.delete()
        return Response({"message": "Participant et données associées supprimés avec succès."}, status=status.HTTP_200_OK)
