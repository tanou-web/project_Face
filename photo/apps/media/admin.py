from django.contrib import admin
from .models import Photo, FaceIndex, Video

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "legend", "is_public", "created_at")
    list_filter = ("event", "is_public", "created_at")
    search_fields = ("legend", "event__name")

@admin.register(FaceIndex)
class FaceIndexAdmin(admin.ModelAdmin):
    list_display = ("id", "photo", "bbox")
    list_filter = ("photo__event",)

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "event", "duration", "size_label")
