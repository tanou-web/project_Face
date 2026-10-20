"""
Configuration de l'application Django 'media'.
Prend en charge le stockage des photos, des vidéos et l'indexation faciale.
"""

from django.apps import AppConfig


class MediaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.media'
    verbose_name = "Médias & Photographies"
