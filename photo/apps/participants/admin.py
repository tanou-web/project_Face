"""
Configuration de l'interface d'administration Django pour le module Participants et RGPD.

Permet de superviser :
- Les profils des participants et l'état de leur reconnaissance biométrique
- Les métadonnées d'horodatage des références faciales (sans accès aux photos brutes)
- Les correspondances identifiées (PhotoMatch) entre clichés et participants.
"""

from django.contrib import admin
from .models import Participant, FaceReference, PhotoMatch


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    """Administration des comptes invités."""
    list_display = ("id", "first_name", "last_name", "phone", "match_status", "created_at")
    list_filter = ("match_status", "created_at")
    search_fields = ("first_name", "last_name", "phone")


@admin.register(FaceReference)
class FaceReferenceAdmin(admin.ModelAdmin):
    """Supervision des consentements et embeddings biométriques."""
    list_display = ("id", "participant", "created_at")
    search_fields = ("participant__first_name", "participant__last_name", "participant__phone")


@admin.register(PhotoMatch)
class PhotoMatchAdmin(admin.ModelAdmin):
    """Audit des photos associées à chaque participant."""
    list_display = ("id", "participant", "photo")
    list_filter = ("photo__event",)
    search_fields = ("participant__first_name", "participant__phone", "photo__legend")
