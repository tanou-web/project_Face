from django.contrib import admin
from .models import Participant, FaceReference, PhotoMatch

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "phone", "match_status", "created_at")
    list_filter = ("match_status", "created_at")
    search_fields = ("first_name", "last_name", "phone")

@admin.register(FaceReference)
class FaceReferenceAdmin(admin.ModelAdmin):
    list_display = ("id", "participant", "created_at")
    search_fields = ("participant__first_name", "participant__last_name", "participant__phone")

@admin.register(PhotoMatch)
class PhotoMatchAdmin(admin.ModelAdmin):
    list_display = ("id", "participant", "photo")
    list_filter = ("photo__event",)
    search_fields = ("participant__first_name", "participant__phone", "photo__legend")
