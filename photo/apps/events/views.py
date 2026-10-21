"""
Vues publiques et opérationnelles pour le catalogue d'événements et la recherche de photos.

Ce module implémente :
1. `find_participant` : Recherche tolérante de profil par ID numérique ou numéro de téléphone normalisé.
2. `EventListView` : Catalogue public des événements en ligne (filtrable par studio via `?org=slug`).
3. `EventDetailView` : Fiche détaillée de l'événement et modification (PATCH) par l'organisateur.
4. `EventPhotosView` : Galerie complète des photos publiques de l'événement.
5. `MyPhotosView` : Récupération des photos personnelles d'un participant identifié par IA.
"""

import logging
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAdminUser
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.events.models import Event
from apps.events.serializers import EventListSerializer, EventDetailSerializer, PhotoItemSerializer, EventPatchSerializer
from apps.media.serializers import MyPhotosResponseSerializer
from apps.participants.models import Participant, FaceReference, PhotoMatch
from apps.participants.utils import normalize_phone
from apps.faces.tasks import match_participant_to_event

logger = logging.getLogger(__name__)


import secrets

def find_participant_for_photos(request):
    """
    Identifie de manière sécurisée le participant pour l'accès à ses photos personnelles.

    Règles de sécurité :
    1. Aucun accès n'est autorisé par simple numéro de téléphone (protection de la vie privée).
       Le numéro de téléphone est exclusivement utilisé pour la gestion des contacts (WhatsApp).
    2. L'accès aux photos personnelles requiert le jeton d'accès secret `access_token`
       (transmis via l'en-tête HTTP 'X-Participant-Token' ou le paramètre '?token=').
    3. Si seul un identifiant numérique `?participant={id}` est fourni :
       - Autorisé pour les administrateurs connectés (is_staff).
       - Pour un invité classique, le jeton secret correspondant doit impérativement être fourni.
    """
    token = (
        request.headers.get("X-Participant-Token")
        or request.query_params.get("token")
    )
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    participant_id = request.query_params.get("participant")

    # 1. Identification par jeton secret (recommandé et hautement sécurisé)
    if token:
        participant = Participant.objects.filter(access_token=token).first()
        if participant:
            if participant_id:
                try:
                    if int(participant_id) != participant.id:
                        return None
                except (ValueError, TypeError):
                    return None
            return participant

    # 2. Consultation par ID (exclusivement pour les administrateurs connectés)
    if participant_id and request.user and request.user.is_authenticated and request.user.is_staff:
        try:
            return Participant.objects.filter(pk=int(participant_id)).first()
        except (ValueError, TypeError):
            pass

    return None


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
    """
    Catalogue des événements accessibles au grand public.
    Seuls les événements avec le statut 'en_ligne' sont retournés.
    Le paramètre query `?org=<slug>` permet à une agence d'afficher sa propre vitrine blanche.
    """
    serializer_class = EventListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Event.objects.filter(status="en_ligne")
        org_slug = self.request.query_params.get("org")
        if org_slug:
            qs = qs.filter(organization__slug=org_slug)
        # Pré-agrégation pour optimiser les performances de la page d'accueil
        return qs.annotate(
            annotated_photos_count=Count('photos', filter=Q(photos__is_public=True)),
            annotated_participants_count=Count('photos__matched_participants', distinct=True)
        ).order_by("-date")


class EventDetailView(APIView):
    """
    Fiche détaillée d'un événement :
    - GET : Accessible à tous pour consulter la description et la galerie de photos publiques.
    - PATCH : Réservé à l'organisateur propriétaire pour éditer la date, le lieu ou le statut.
    """
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
        description="Permet à l'organisateur / admin de modifier les informations d'un événement (date, nom, thème, statut).",
        request=EventPatchSerializer,
        responses={200: EventDetailSerializer}
    )
    def patch(self, request, slug):
        """
        Mise à jour partielle des attributs d'un événement.
        Contrôle que l'utilisateur connecté appartient bien à l'organisation hôte
        et détient le rôle 'owner' ou 'manager' ('photographer' reçoit 403 Forbidden).
        """
        event = get_object_or_404(Event, slug=slug)
        from apps.organizations.permissions import get_user_organization, get_user_role
        user_org = get_user_organization(request.user)
        user_role = get_user_role(request.user, user_org)
        
        # Vérification stricte des autorisations multi-tenant
        if not (request.user.is_superuser or (event.organization == user_org and user_role in ["owner", "manager"])):
            return Response(
                {"detail": "Vous n'avez pas l'autorisation de modifier cet événement."},
                status=status.HTTP_403_FORBIDDEN
            )
        data = request.data
        for field in [
            "name", "tagline", "description", "city", "venue",
            "date", "status", "accent_color", "accent_text_color",
            "organizer_name", "organizer_about", "organizer_website", "organizer_phone"
        ]:
            if field in data:
                setattr(event, field, data[field])
        if "highlights" in data and isinstance(data["highlights"], list):
            event.highlights = data["highlights"]
        event.save()
        serializer = EventDetailSerializer(event, context={"request": request})
        return Response(serializer.data)


class EventPhotosView(APIView):
    """
    Galerie de photos publiques d'un événement spécifique.
    Retourne la liste des photos approuvées pour affichage grand public.
    """
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
    """
    Endpoint de récupération des photos personnelles d'un participant (Reconnaissance Faciale).

    Machine à états du participant :
    - 'no_reference' : Le participant n'a pas encore fourni de selfie de référence.
    - 'pending' : Selfie reçu, matching IA en cours ou déclenché à la volée.
    - 'ready' : Traitement terminé, retourne uniquement les photos où le visage du participant apparaît.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Participants"],
        summary="Photos matchées du participant",
        description=(
            "Retourne les photos reconnues par reconnaissance faciale pour un participant sur un événement.\n"
            "Sécurité : L'accès nécessite le jeton secret `access_token` du participant "
            "(reçu lors du scan / enregistrement), transmis via le header `X-Participant-Token` "
            "ou le paramètre `?token=`.\n"
            "Aucune consultation par numéro de téléphone n'est autorisée (numéro réservé au contact WhatsApp organisateur)."
        ),
        parameters=[
            OpenApiParameter(
                name="token",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Jeton secret access_token du participant (reçu lors du POST /participants/)"
            ),
            OpenApiParameter(
                name="X-Participant-Token",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description="Jeton secret access_token du participant"
            ),
            OpenApiParameter(
                name="participant",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="ID du participant (réservé aux administrateurs ou accompagné du token)"
            ),
        ],
        responses={200: MyPhotosResponseSerializer}
    )
    def get(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        participant = find_participant_for_photos(request)
        if not participant:
            return Response({"status": "no_reference", "photos": []})

        # 1. Vérifie si le participant doit d'abord soumettre son selfie
        if participant.match_status == "no_reference":
            if FaceReference.objects.filter(participant=participant).exists():
                participant.match_status = "pending"
                participant.save()
            else:
                return Response({"status": "no_reference", "photos": []})

        # 2. Si le matching est en attente, tente une réconciliation immédiate
        if participant.match_status == "pending":
            if FaceReference.objects.filter(participant=participant).exists():
                try:
                    match_participant_to_event(participant.id, event.slug)
                    participant.refresh_from_db()
                except Exception as e:
                    logger.warning(f"Matching direct en attente: {e}")
            if participant.match_status == "pending":
                return Response({"status": "pending", "photos": []})

        # 3. Statut 'ready' : renvoie la sélection des photos reconnues
        matches = PhotoMatch.objects.filter(
            participant=participant,
            photo__event=event,
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
