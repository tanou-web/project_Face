import logging
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAdminUser
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.events.models import Event
from apps.events.serializers import EventListSerializer, EventDetailSerializer, PhotoItemSerializer, EventPatchSerializer
from apps.media.serializers import MyPhotosResponseSerializer
from apps.participants.models import Participant, FaceReference, PhotoMatch
from apps.participants.utils import normalize_phone
from apps.faces.tasks import match_participant_to_event

logger = logging.getLogger(__name__)

def find_participant(participant_id=None, phone=None):
    """
    Recherche robuste d'un participant par son ID ou son numéro de téléphone.
    Le numéro est normalisé au format E.164 (+226...) avant la recherche.
    """
    if participant_id:
        try:
            p = Participant.objects.filter(pk=int(participant_id)).first()
            if p:
                return p
        except (ValueError, TypeError):
            pass

    if phone:
        # Normaliser le numéro pour correspondre au format stocké en base
        normalized = normalize_phone(phone)
        if normalized:
            p = Participant.objects.filter(phone=normalized).first()
            if p:
                return p

        # Fallback : correspondance exacte sur la valeur brute (compatibilité anciennes données)
        raw = phone.strip()
        p = Participant.objects.filter(phone=raw).first()
        if p:
            return p

    return None

from django.db.models import Count, Q

@extend_schema(
    tags=["Événements"],
    summary="Lister les événements publics",
    description="Retourne la liste des événements publics en ligne. Peut être filtré par organisation via `?org=<slug_organisation>` pour afficher la page dédiée d'un organisateur.",
    parameters=[
        OpenApiParameter(
            name="org",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Slug de l'organisation pour n'afficher que ses événements publics (ex: 'faso-business-club')"
        )
    ]
)
class EventListView(generics.ListAPIView):
    serializer_class = EventListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Event.objects.filter(status="en_ligne")
        org_slug = self.request.query_params.get("org")
        if org_slug:
            qs = qs.filter(organization__slug=org_slug)
        return qs.annotate(
            annotated_photos_count=Count('photos', filter=Q(photos__is_public=True)),
            annotated_participants_count=Count('photos__matched_participants', distinct=True)
        ).order_by("-date")

class EventDetailView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @extend_schema(
        tags=["Événements"],
        summary="Détail d'un événement",
        description="Récupère la fiche détaillée d'un événement avec sa galerie de photos et sa vidéo.",
        responses={200: EventDetailSerializer}
    )
    def get(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        serializer = EventDetailSerializer(event, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        tags=["Administration"],
        summary="Mise à jour partielle d'un événement",
        description="Permet à l'organisateur / admin de modifier les informations d'un événement.",
        request=EventPatchSerializer,
        responses={200: EventDetailSerializer}
    )
    def patch(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        from apps.organizations.permissions import get_user_organization, get_user_role
        user_org = get_user_organization(request.user)
        user_role = get_user_role(request.user, user_org)
        # Seul owner ou manager peut modifier un événement (photographer = 403)
        if not (request.user.is_superuser or (event.organization == user_org and user_role in ["owner", "manager"])):
            return Response({"detail": "Vous n'avez pas l'autorisation de modifier cet événement."}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        for field in ["name", "tagline", "description", "city", "venue", "date", "status", "accent_color", "accent_text_color", "organizer_name", "organizer_about", "organizer_website", "organizer_phone"]:
            if field in data:
                setattr(event, field, data[field])
        if "highlights" in data and isinstance(data["highlights"], list):
            event.highlights = data["highlights"]
        event.save()
        serializer = EventDetailSerializer(event, context={"request": request})
        return Response(serializer.data)

class EventPhotosView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Événements"],
        summary="Galerie de photos publiques d'un événement",
        description="Liste l'ensemble des photos publiques d'un événement.",
        responses={200: PhotoItemSerializer(many=True)}
    )
    def get(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        photos = event.photos.filter(is_public=True).order_by("-created_at")
        serializer = PhotoItemSerializer(photos, many=True, context={"request": request})
        return Response(serializer.data)

class MyPhotosView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Participants"],
        summary="Photos matchées du participant",
        description=(
            "Retourne les photos reconnues pour un participant donné sur un événement.\n"
            "Prend en charge `?participant={id}` ou `?phone={numéro WhatsApp}` pour garantir "
            "le bon fonctionnement même lorsque le frontend n'a pas encore persisté l'identifiant."
        ),
        parameters=[
            OpenApiParameter(
                name="participant",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="ID unique du participant retourné lors du POST /participants/"
            ),
            OpenApiParameter(
                name="phone",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Numéro WhatsApp du participant (ex: '+226 70123456')"
            ),
        ],
        responses={200: MyPhotosResponseSerializer}
    )
    def get(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        participant_id = request.query_params.get("participant")
        phone = request.query_params.get("phone")

        participant = find_participant(participant_id, phone)
        if not participant:
            return Response({"status": "no_reference", "photos": []})

        if participant.match_status == "no_reference":
            # Auto-récupération si une FaceReference a été injectée
            if FaceReference.objects.filter(participant=participant).exists():
                participant.match_status = "pending"
                participant.save()
            else:
                return Response({"status": "no_reference", "photos": []})

        if participant.match_status == "pending":
            if FaceReference.objects.filter(participant=participant).exists():
                try:
                    match_participant_to_event(participant.id, event.slug)
                    participant.refresh_from_db()
                except Exception as e:
                    logger.warning(f"Matching direct en attente: {e}")
            if participant.match_status == "pending":
                return Response({"status": "pending", "photos": []})

        # Statut ready : renvoyer les photos matchées
        matches = PhotoMatch.objects.filter(
            participant=participant,
            photo__event=event,
            photo__is_public=True,
        ).select_related("photo").order_by("-photo__created_at")

        photos = [
            {
                "id": str(m.photo.id),
                "src": request.build_absolute_uri(m.photo.file.url) if m.photo.file else "",
                "legend": m.photo.legend,
                "isPublic": m.photo.is_public,
            }
            for m in matches
        ]

        return Response({"status": "ready", "photos": photos})
