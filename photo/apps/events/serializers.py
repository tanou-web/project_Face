from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from apps.events.models import Event
from apps.media.models import Photo, Video
from apps.participants.models import PhotoMatch

FRENCH_MONTHS = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}

def format_french_date(date_obj):
    if not date_obj:
        return ""
    month_str = FRENCH_MONTHS.get(date_obj.month, "")
    return f"{date_obj.day} {month_str} {date_obj.year}".strip()

class PhotoItemSerializer(serializers.ModelSerializer):
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
        return {
            "accent": obj.accent_color or "oklch(0.578 0.221 27.5)",
            "accentForeground": obj.accent_text_color or "oklch(0.99 0 0)",
        }

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_organizer(self, obj) -> dict:
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
        return []

    @extend_schema_field(VideoItemSerializer)
    def get_video(self, obj):
        return None

    @extend_schema_field(OpenApiTypes.INT)
    def get_participants(self, obj) -> int:
        if hasattr(obj, 'annotated_participants_count'):
            return obj.annotated_participants_count
        return PhotoMatch.objects.filter(photo__event=obj).values("participant").distinct().count()

    @extend_schema_field(OpenApiTypes.INT)
    def get_photosCount(self, obj) -> int:
        if hasattr(obj, 'annotated_photos_count'):
            return obj.annotated_photos_count
        return obj.photos.count()

class EventDetailSerializer(EventListSerializer):
    @extend_schema_field(PhotoItemSerializer(many=True))
    def get_photos(self, obj):
        request = self.context.get("request")
        public_photos = obj.photos.filter(is_public=True).order_by("-created_at")
        return PhotoItemSerializer(public_photos, many=True, context={"request": request}).data

    @extend_schema_field(VideoItemSerializer)
    def get_video(self, obj):
        request = self.context.get("request")
        if hasattr(obj, "video") and obj.video:
            return VideoItemSerializer(obj.video, context={"request": request}).data
        return None

class EventPatchSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, help_text="Nom de l'événement")
    tagline = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    venue = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=["en_ligne", "traitement", "archive"], required=False)
    accent_color = serializers.CharField(required=False)
    accent_text_color = serializers.CharField(required=False)
    organizer_name = serializers.CharField(required=False)
    organizer_about = serializers.CharField(required=False)
    organizer_website = serializers.URLField(required=False)
    organizer_phone = serializers.CharField(required=False)
    highlights = serializers.ListField(child=serializers.CharField(), required=False)
