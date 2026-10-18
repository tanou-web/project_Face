from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.events.models import Event
from apps.media.models import Photo
from apps.media.serializers import SingleFileUploadSerializer
from apps.participants.models import Participant, FaceReference, PhotoMatch
from apps.organizations.permissions import IsOrganizationMember

class AdminStatsView(APIView):
    permission_classes = [IsOrganizationMember]

    @extend_schema(
        tags=["Administration"],
        summary="Statistiques globales de l'organisation",
        description="Retourne le nombre total d'événements, photos, participants et téléchargements de l'organisation.",
        responses={200: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        user = request.user
        if user.is_superuser:
            events_qs = Event.objects.all()
            photos_qs = Photo.objects.all()
            participants_count = Participant.objects.count()
            downloads_count = PhotoMatch.objects.count()
        else:
            org = user.organization
            events_qs = Event.objects.filter(organization=org)
            photos_qs = Photo.objects.filter(event__organization=org)
            participant_ids = PhotoMatch.objects.filter(
                photo__event__organization=org
            ).values_list("participant_id", flat=True).distinct()
            participants_count = Participant.objects.filter(id__in=participant_ids).count()
            downloads_count = PhotoMatch.objects.filter(photo__event__organization=org).count()

        events_count = events_qs.count()
        photos_count = photos_qs.count()

        return Response({
            "events": events_count,
            "photos": photos_count,
            "participants": participants_count,
            "downloads": downloads_count,
        })

class AdminContactsView(APIView):
    permission_classes = [IsOrganizationMember]

    @extend_schema(
        tags=["Administration"],
        summary="Liste des contacts participants de l'organisation",
        description="Récupère les coordonnées des participants et indique si leur référence faciale est valide.",
        parameters=[
            OpenApiParameter(
                name="event",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filtrer les participants par slug d'événement"
            )
        ],
        responses={200: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        user = request.user
        event_slug = request.query_params.get("event")

        if event_slug:
            event = get_object_or_404(Event, slug=event_slug)
            # Vérification Multi-Tenant
            if not user.is_superuser and hasattr(user, "organization") and event.organization != user.organization:
                return Response({"detail": "Accès refusé pour cet événement."}, status=status.HTTP_403_FORBIDDEN)
            participant_ids = PhotoMatch.objects.filter(photo__event=event).values_list("participant_id", flat=True).distinct()
            participants = Participant.objects.filter(id__in=participant_ids).order_by("-created_at")
            event_name = event.name
        else:
            if user.is_superuser:
                participants = Participant.objects.all().order_by("-created_at")
            else:
                org = user.organization
                participant_ids = PhotoMatch.objects.filter(
                    photo__event__organization=org
                ).values_list("participant_id", flat=True).distinct()
                participants = Participant.objects.filter(id__in=participant_ids).order_by("-created_at")
            event_name = "Tous les événements"

        # Vérification des FaceReference existantes
        face_ref_ids = set(FaceReference.objects.values_list("participant_id", flat=True))

        data = []
        for p in participants:
            has_ref = p.id in face_ref_ids
            date_str = p.created_at.strftime("%d/%m/%Y") if p.created_at else ""
            data.append({
                "id": p.id,
                "firstName": p.first_name,
                "lastName": p.last_name,
                "phone": p.phone,
                "event": event_name,
                "hasFaceReference": has_ref,
                "valid": has_ref,
                "date": date_str,
            })

        return Response(data)

class AdminLogoUploadView(APIView):
    permission_classes = [IsOrganizationMember]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Administration"],
        summary="Upload de logo pour un événement",
        description="Upload d'un logo (champ `file`) et mise à jour de l'événement.",
        request=SingleFileUploadSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    def post(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        # Vérification Multi-Tenant
        is_owner = hasattr(request.user, "organization") and event.organization == request.user.organization
        if not (request.user.is_staff or is_owner):
            return Response({"detail": "Vous n'avez pas l'autorisation de modifier cet événement."}, status=status.HTTP_403_FORBIDDEN)

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "Aucun fichier fourni."}, status=status.HTTP_400_BAD_REQUEST)

        event.logo = file_obj
        event.save()
        logo_url = request.build_absolute_uri(event.logo.url)
        return Response({"logoUrl": logo_url})

from django.db.models import Count, Q
from apps.events.serializers import EventListSerializer, EventCreateSerializer, EventDetailSerializer
from apps.organizations.permissions import get_user_organization, get_user_role, IsOrganizationManagerOrOwner

class AdminEventsView(APIView):
    """
    Gestion des événements réservée à l'organisation connectée :
    - GET /admin/events/ : Ne renvoie QUE les événements de l'organisation connectée (isolée du public).
    - POST /admin/events/ : Création d'un nouvel événement rattaché automatiquement à l'organisation (Réservé Owner & Manager).
    """
    permission_classes = [IsOrganizationMember]

    @extend_schema(
        tags=["Administration"],
        summary="Lister les événements de l'organisation",
        description="Ne renvoie que les événements appartenant à l'organisation de l'utilisateur connecté (aucun événement des autres clients n'apparaît).",
        responses={200: EventListSerializer(many=True)}
    )
    def get(self, request):
        user = request.user
        if user.is_superuser:
            qs = Event.objects.all()
        else:
            org = get_user_organization(user)
            if not org:
                return Response([])
            qs = Event.objects.filter(organization=org)

        qs = qs.annotate(
            annotated_photos_count=Count('photos', filter=Q(photos__is_public=True)),
            annotated_participants_count=Count('photos__matched_participants', distinct=True)
        ).order_by("-date")

        serializer = EventListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        tags=["Administration"],
        summary="Créer un événement pour l'organisation",
        description="Crée un nouvel événement et l'associe automatiquement à l'organisation connectée. Seuls les rôles 'owner' et 'manager' sont autorisés ('photographer' reçoit 403 Forbidden).",
        request=EventCreateSerializer,
        responses={201: EventDetailSerializer, 403: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        user = request.user
        org = get_user_organization(user)
        role = get_user_role(user, org)

        # Vérification stricte des rôles : le photographe ne peut pas créer d'événement
        if not (user.is_superuser or role in ["owner", "manager"]):
            return Response(
                {"detail": "Accès refusé : seuls les gestionnaires et propriétaires peuvent créer un événement."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = EventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save(organization=org)

        response_serializer = EventDetailSerializer(event, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

