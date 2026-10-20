"""
Sérialiseurs pour l'exposition et la manipulation des Événements et Médias associés.

Ce module structure la transformation des données entre les modèles ORM et les payloads JSON :
1. `PhotoItemSerializer` & `VideoItemSerializer` : Objets médias avec résolution d'URL absolue.
2. `EventListSerializer` : Vue synthétique optimisée pour le catalogue (évite le problème N+1).
3. `EventDetailSerializer` : Fiche complète incluant la galerie photo publique et la vidéo.
4. `EventCreateSerializer` & `EventPatchSerializer` : Validation pour la création et mise à jour (PATCH).
"""

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from apps.events.models import Event
from apps.media.models import Photo, Video
from apps.participants.models import PhotoMatch

# Dictionnaire de traduction des mois en français.
# Pourquoi cette approche :
# Sur les conteneurs Linux allégés (Docker / Render), les locales système comme fr_FR.UTF-8
# ne sont pas toujours installées par défaut. Cette fonction pure Python garantit un formatage
# irréprochable ('25 octobre 2026') sans dépendre des paramètres régionaux de l'OS hôte.
FRENCH_MONTHS = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}

def format_french_date(date_obj):
    """Formate un objet datetime.date en chaîne française lisible (ex: '15 novembre 2026')."""
    if not date_obj:
        return ""
    month_str = FRENCH_MONTHS.get(date_obj.month, "")
    return f"{date_obj.day} {month_str} {date_obj.year}".strip()


class PhotoItemSerializer(serializers.ModelSerializer):
    """
    Sérialiseur d'une photo individuelle destinée à la galerie.
    Résout l'URL absolue complète en préfixant le protocole et le domaine (build_absolute_uri).
    """
    id = serializers.CharField(source="pk")
    src = serializers.SerializerMethodField()
    isPublic = serializers.BooleanField(source="is_public")

    class Meta:
        model = Photo
        fields = ["id", "src", "legend", "isPublic"]

    @extend_schema_field(OpenApiTypes.URI)
    def get_src(self, obj) -> str:
        request = self.context.get("request")
        if obj.file:
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return ""


class VideoItemSerializer(serializers.ModelSerializer):
    """
    Sérialiseur de la vidéo promotionnelle ou récapitulative de l'événement.
    """
    src = serializers.SerializerMethodField()
    sizeLabel = serializers.CharField(source="size_label")

    class Meta:
        model = Video
        fields = ["src", "title", "duration", "sizeLabel"]

    @extend_schema_field(OpenApiTypes.URI)
    def get_src(self, obj) -> str:
        request = self.context.get("request")
        if obj.file:
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return ""


class EventListSerializer(serializers.ModelSerializer):
    """
    Sérialiseur optimisé pour l'affichage en liste (Catalogue public ou Dashboard admin).

    Optimisation clé :
    Ne charge pas la collection complète des photos (laisse le champ 'photos' vide) afin de ne pas
    télécharger des milliers d'objets en mémoire lors du listing. Les décomptes sont pré-calculés
    via les annotations ORM ('annotated_photos_count', 'annotated_participants_count') pour éliminer
    les requêtes SQL redondantes (problème N+1).
    """
    logoUrl = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    dateLabel = serializers.SerializerMethodField()
    theme = serializers.SerializerMethodField()
    organizer = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    photosCount = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "slug", "name", "tagline", "description",
            "logoUrl", "city", "venue", "date", "dateLabel",
            "status", "cover", "theme", "organizer",
            "highlights", "photos", "video", "participants", "photosCount"
        ]

    @extend_schema_field(OpenApiTypes.URI)
    def get_logoUrl(self, obj) -> str | None:
        request = self.context.get("request")
        if obj.logo:
            return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url
        return None

    @extend_schema_field(OpenApiTypes.URI)
    def get_cover(self, obj) -> str | None:
        request = self.context.get("request")
        if obj.cover:
            return request.build_absolute_uri(obj.cover.url) if request else obj.cover.url
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_dateLabel(self, obj) -> str:
        return format_french_date(obj.date)

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_theme(self, obj) -> dict:
        """Expose les variables CSS de couleurs pour l'habillage dynamique de la page événement."""
        return {
            "accent": obj.accent_color or "oklch(0.578 0.221 27.5)",
            "accentForeground": obj.accent_text_color or "oklch(0.99 0 0)",
        }

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_organizer(self, obj) -> dict:
        """Structure les métadonnées de l'organisateur hôte de l'événement."""
        request = self.context.get("request")
        logo_url = None
        if obj.organizer_logo:
            logo_url = request.build_absolute_uri(obj.organizer_logo.url) if request else obj.organizer_logo.url

        return {
            "name": obj.organizer_name,
            "logoUrl": logo_url,
            "about": obj.organizer_about,
            "website": obj.organizer_website,
            "phone": obj.organizer_phone,
        }

    @extend_schema_field(PhotoItemSerializer(many=True))
    def get_photos(self, obj) -> list:
        # Retourne une liste vide dans le listing pour préserver la bande passante
        return []

    @extend_schema_field(VideoItemSerializer)
    def get_video(self, obj):
        return None

    @extend_schema_field(OpenApiTypes.INT)
    def get_participants(self, obj) -> int:
        """Décompte des participants uniques ayant au moins une photo matchée."""
        if hasattr(obj, 'annotated_participants_count'):
            return obj.annotated_participants_count
        return PhotoMatch.objects.filter(photo__event=obj).values("participant").distinct().count()

    @extend_schema_field(OpenApiTypes.INT)
    def get_photosCount(self, obj) -> int:
        """Nombre total de photos publiées pour cet événement."""
        if hasattr(obj, 'annotated_photos_count'):
            return obj.annotated_photos_count
        return obj.photos.count()


class EventDetailSerializer(EventListSerializer):
    """
    Sérialiseur détaillé pour la consultation d'un événement spécifique.
    Hérite de EventListSerializer en chargeant cette fois la galerie réelle de photos publiques.
    """
    @extend_schema_field(PhotoItemSerializer(many=True))
    def get_photos(self, obj):
        request = self.context.get("request")
        # Seules les photos validées (is_public=True) sont exposées sur la fiche détaillée
        public_photos = obj.photos.filter(is_public=True).order_by("-created_at")
        return PhotoItemSerializer(public_photos, many=True, context={"request": request}).data

    @extend_schema_field(VideoItemSerializer)
    def get_video(self, obj):
        request = self.context.get("request")
        if hasattr(obj, "video") and obj.video:
            return VideoItemSerializer(obj.video, context={"request": request}).data
        return None


class EventPatchSerializer(serializers.Serializer):
    """
    Validation pour la mise à jour partielle (PATCH) d'un événement par son organisateur.
    Tous les champs sont optionnels : permet de modifier uniquement la date, le statut ou le nom.
    """
    name = serializers.CharField(required=False, help_text="Nom de l'événement")
    tagline = serializers.CharField(required=False, help_text="Sous-titre d'accroche")
    description = serializers.CharField(required=False, help_text="Description de l'événement")
    city = serializers.CharField(required=False, help_text="Ville de l'événement")
    venue = serializers.CharField(required=False, help_text="Lieu de réception")
    date = serializers.DateField(required=False, help_text="Date de l'événement (YYYY-MM-DD)")
    status = serializers.ChoiceField(choices=["en_ligne", "traitement", "archive"], required=False)
    accent_color = serializers.CharField(required=False, help_text="Couleur accent (ex: oklch(...))")
    accent_text_color = serializers.CharField(required=False, help_text="Couleur texte accent")
    organizer_name = serializers.CharField(required=False)
    organizer_about = serializers.CharField(required=False)
    organizer_website = serializers.URLField(required=False)
    organizer_phone = serializers.CharField(required=False)
    highlights = serializers.ListField(child=serializers.CharField(), required=False)


class EventCreateSerializer(serializers.ModelSerializer):
    """
    Validation pour la création d'un événement par un 'owner' ou 'manager' de l'organisation.
    Applique des valeurs par défaut sécurisées (statut 'traitement' pour masquer l'événement
    tant que les photos ne sont pas prêtes).
    """
    class Meta:
        model = Event
        fields = [
            "name", "slug", "tagline", "description", "city", "venue",
            "date", "status", "accent_color", "accent_text_color",
            "organizer_name", "organizer_about", "organizer_website",
            "organizer_phone", "highlights"
        ]
        extra_kwargs = {
            "slug": {"required": False},
            "tagline": {"required": False, "default": ""},
            "description": {"required": False, "default": ""},
            "venue": {"required": False, "default": ""},
            "status": {"required": False, "default": "traitement"},
            "accent_color": {"required": False, "default": "oklch(0.578 0.221 27.5)"},
            "accent_text_color": {"required": False, "default": "oklch(0.99 0 0)"},
            "organizer_name": {"required": False, "default": ""},
            "highlights": {"required": False, "default": list},
        }

