"""
Interface d'administration Django pour la gestion des Événements.

Permet aux administrateurs de modérer le catalogue des événements,
d'éditer les statuts de publication ('traitement', 'en_ligne', 'archive')
et de filtrer par organisation, ville ou date.
"""

from django.contrib import admin
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Configuration de l'affichage tabulaire des événements dans l'admin Django."""
    list_display = ("name", "organization", "slug", "city", "date", "status", "organizer_name")
    list_filter = ("status", "organization", "city", "date")
    search_fields = ("name", "slug", "organizer_name", "description")
    prepopulated_fields = {"slug": ("name",)}
