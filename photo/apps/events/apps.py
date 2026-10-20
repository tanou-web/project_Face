"""
Configuration de l'application Django 'events'.
Gère les événements, les fiches descriptives, les statuts et les thèmes graphiques.
"""

from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.events'
    verbose_name = "Événements & Catalogues"
