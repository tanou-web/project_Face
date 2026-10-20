"""
Configuration de l'interface d'administration Django pour le module Médias.

Permet de superviser :
- Les photos téléversées et leur statut de visibilité publique
- Les indexations faciales (boîtes englobantes des visages détectés)
- Les vidéos associées aux événements.
"""

from django.contrib import admin
from .models import Photo, FaceIndex, Video


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    """Administration des clichés photographiques."""
    list_display = ("id", "event", "legend", "is_public", "created_at")
    list_filter = ("event", "is_public", "created_at")
    search_fields = ("legend", "event__name")


@admin.register(FaceIndex)
class FaceIndexAdmin(admin.ModelAdmin):
    """Surveillance des visages extraits par le modèle d'intelligence artificielle."""
    list_display = ("id", "photo", "bbox")
    list_filter = ("photo__event",)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """Administration des vidéos officielles d'événements."""
    list_display = ("title", "event", "duration", "size_label")
