from rest_framework import permissions

def get_user_organization(user):
    """
    Retourne l'organisation active associée à l'utilisateur :
    - Soit comme propriétaire (owned_organizations)
    - Soit comme membre via OrganizationMembership
    """
    if not user or not user.is_authenticated:
        return None
    # 1. Vérifie si propriétaire direct
    owned = user.owned_organizations.filter(is_active=True).first()
    if owned:
        return owned
    # 2. Vérifie via adhésion à une organisation
    membership = user.organization_memberships.filter(organization__is_active=True).select_related("organization").first()
    if membership:
        return membership.organization
    return None

def get_user_role(user, organization=None):
    """
    Retourne le rôle effectif de l'utilisateur ('owner', 'manager', 'photographer' ou None).
    """
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return "owner"
    if organization is None:
        organization = get_user_organization(user)
    if not organization:
        return None
    return organization.get_user_role(user)


class IsOrganizationMember(permissions.BasePermission):
    """
    Vérifie que l'utilisateur est authentifié et appartient à une organisation active.
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
    Permission pour les actions de gestion (création/modification d'événements, invitations).
    Rôles autorisés : 'owner', 'manager' (et superuser).
    Rôle exclu (403) : 'photographer'.
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
    Permission stricte pour les actions réservées au propriétaire (ex: supprimer l'organisation, inviter des managers).
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
    Vérifie que l'événement manipulé appartient à l'organisation de l'utilisateur.
    """
    message = "Accès refusé : cet événement n'appartient pas à votre organisation."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        return get_user_organization(request.user) is not None

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        user_org = get_user_organization(request.user)
        if not user_org:
            return False
        
        # Objet Event
        if hasattr(obj, "organization"):
            return obj.organization == user_org
        # Objet Photo
        if hasattr(obj, "event"):
            return obj.event.organization == user_org
        return False
