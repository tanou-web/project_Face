"""
Classes de permissions et fonctions utilitaires pour le contrôle d'accès Multi-Tenant (RBAC).

Ce module centralise la logique de sécurité garantissant qu'un utilisateur ne peut accéder
qu'aux données (statistiques, événements, médias) appartenant à sa propre organisation.

Niveaux de permissions :
- `IsOrganizationMember` : L'utilisateur appartient à une organisation active.
- `IsOrganizationManagerOrOwner` : Autorise les opérations de gestion (création d'événements, invitations).
- `IsOrganizationOwner` : Réservé exclusivement au propriétaire légal de l'organisation.
- `IsEventOrganizationOwner` : Contrôle au niveau de l'objet (Object-level) pour les événements et photos.
"""

from rest_framework import permissions


def get_user_organization(user):
    """
    Identifie et retourne l'organisation active à laquelle est rattaché l'utilisateur.

    Stratégie de résolution en 2 temps :
    1. Vérification en tant que propriétaire direct (`owned_organizations`).
    2. Si non propriétaire, vérification via une adhésion active (`organization_memberships`).
    
    Retourne None si l'utilisateur n'est pas authentifié ou n'a aucune organisation active.
    """
    if not user or not user.is_authenticated:
        return None
    # 1. Vérifie si propriétaire direct d'une organisation active
    owned = user.owned_organizations.filter(is_active=True).first()
    if owned:
        return owned
    # 2. Vérifie via adhésion (membership) avec chargement optimisé de la relation (select_related)
    membership = user.organization_memberships.filter(organization__is_active=True).select_related("organization").first()
    if membership:
        return membership.organization
    return None


def get_user_role(user, organization=None):
    """
    Détermine le rôle hiérarchique effectif de l'utilisateur.

    Valeurs possibles :
    - 'owner' : Pleins pouvoirs (propriétaire ou superadministrateur).
    - 'manager' : Gestionnaire d'événements et d'équipe.
    - 'photographer' : Photographe prestataire (upload de médias uniquement).
    - None : Aucun rôle attribué dans l'organisation.
    """
    if not user or not user.is_authenticated:
        return None
    # Les superadministrateurs héritent automatiquement de tous les privilèges
    if user.is_superuser:
        return "owner"
    if organization is None:
        organization = get_user_organization(user)
    if not organization:
        return None
    return organization.get_user_role(user)


class IsOrganizationMember(permissions.BasePermission):
    """
    Permission de base : Exige que l'utilisateur soit connecté et affilié à une organisation active.
    Utilisée pour sécuriser l'accès aux tableaux de bord et aux listes privées d'événements.
    """
    message = "Accès refusé : vous devez appartenir à une organisation active."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        return get_user_organization(request.user) is not None


class IsOrganizationManagerOrOwner(permissions.BasePermission):
    """
    Permission de gestion : Réservée aux rôles 'owner' et 'manager'.

    Bloque explicitement le rôle 'photographer' (qui reçoit une erreur HTTP 403 Forbidden)
    afin qu'un photographe externe ne puisse ni créer d'événement, ni inviter d'autres membres.
    """
    message = "Accès refusé : rôle 'owner' ou 'manager' requis pour cette action."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        org = get_user_organization(request.user)
        if not org:
            return False
        role = get_user_role(request.user, org)
        return role in ["owner", "manager"]


class IsOrganizationOwner(permissions.BasePermission):
    """
    Permission stricte : Réservée uniquement au propriétaire de l'organisation.
    Indispensable pour les opérations critiques comme la suppression de l'organisation
    ou la modification des paramètres de facturation/abonnements.
    """
    message = "Accès refusé : réservé au propriétaire de l'organisation."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        org = get_user_organization(request.user)
        if not org:
            return False
        return get_user_role(request.user, org) == "owner"


class IsEventOrganizationOwner(permissions.BasePermission):
    """
    Permission fine au niveau de l'objet (Object-level Permission).

    Empêche un gestionnaire d'une organisation A de modifier, uploader ou supprimer
    des photos ou des événements appartenant à une organisation B.
    """
    message = "Accès refusé : cet événement n'appartient pas à votre organisation."

    def has_permission(self, request, view):
        # Vérification globale préalable : l'utilisateur doit être membre d'une organisation
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        return get_user_organization(request.user) is not None

    def has_object_permission(self, request, view, obj):
        # Vérification ciblée sur l'instance de l'objet
        if request.user.is_superuser:
            return True
        user_org = get_user_organization(request.user)
        if not user_org:
            return False
        
        # Cas 1 : L'objet inspecté est directement un Événement
        if hasattr(obj, "organization"):
            return obj.organization == user_org
        # Cas 2 : L'objet inspecté est une Photo reliée à un Événement
        if hasattr(obj, "event"):
            return obj.event.organization == user_org
        return False
