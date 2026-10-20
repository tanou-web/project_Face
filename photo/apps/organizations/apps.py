"""
Configuration de l'application Django 'organizations'.
Prend en charge le domaine SaaS multi-tenant, la gestion des équipes et les invitations.
"""

from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.organizations"
    verbose_name = "Organisations & SaaS"
