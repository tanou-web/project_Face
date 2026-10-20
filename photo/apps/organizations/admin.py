"""
Configuration de l'interface d'administration Django pour le module SaaS Organisations.

Permet aux superadministrateurs de :
- Consulter et modérer les organisations clientes (activer/désactiver les accès).
- Visualiser les membres affiliés et leurs rôles (RBAC).
- Auditer l'historique des invitations générées et leurs états de consommation.
"""

from django.contrib import admin
from apps.organizations.models import Organization, OrganizationMembership, Invitation


class OrganizationMembershipInline(admin.TabularInline):
    """Permet de visualiser et gérer les collaborateurs directement depuis la fiche organisation."""
    model = OrganizationMembership
    extra = 1


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Administration des tenants / organisations clientes."""
    list_display = ("name", "slug", "owner", "is_active", "created_at")
    search_fields = ("name", "slug", "owner__username", "owner__email")
    list_filter = ("is_active", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [OrganizationMembershipInline]


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    """Administration des rôles des membres au sein des organisations."""
    list_display = ("user", "organization", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("user__username", "user__email", "organization__name")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    """Surveillance des invitations et des liens de définition de mot de passe."""
    list_display = ("organization", "role", "email", "phone", "is_used", "expires_at", "created_at")
    list_filter = ("role", "is_used", "created_at")
    search_fields = ("email", "phone", "token", "organization__name")
