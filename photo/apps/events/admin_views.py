from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.events.models import Event
from apps.media.models import Photo
from apps.media.serializers import SingleFileUploadSerializer
from apps.participants.models import Participant, FaceReference, PhotoMatch

class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Administration"],
        summary="Statistiques globales",
        description="Retourne le nombre total d'événements, photos, participants et téléchargements.",
        responses={200: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        events_count = Event.objects.count()
        photos_count = Photo.objects.count()
        participants_count = Participant.objects.count()
        downloads_count = PhotoMatch.objects.count()

        return Response({
            "events": events_count,
            "photos": photos_count,
            "participants": participants_count,
            "downloads": downloads_count,
        })

class AdminContactsView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Administration"],
        summary="Liste des contacts participants",
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
        event_slug = request.query_params.get("event")
        if event_slug:
            event = get_object_or_404(Event, slug=event_slug)
            participant_ids = PhotoMatch.objects.filter(photo__event=event).values_list("participant_id", flat=True).distinct()
            participants = Participant.objects.filter(id__in=participant_ids).order_by("-created_at")
            event_name = event.name
        else:
            participants = Participant.objects.all().order_by("-created_at")
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
    permission_classes = [IsAdminUser]
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
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "Aucun fichier fourni."}, status=status.HTTP_400_BAD_REQUEST)

        event.logo = file_obj
        event.save()
        logo_url = request.build_absolute_uri(event.logo.url)
        return Response({"logoUrl": logo_url})
