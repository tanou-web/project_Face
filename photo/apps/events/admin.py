from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "city", "date", "status", "organizer_name")
    list_filter = ("status", "city", "date")
    search_fields = ("name", "slug", "organizer_name", "description")
    prepopulated_fields = {"slug": ("name",)}
