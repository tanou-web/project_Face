from rest_framework import permissions

class IsOrganizationMember(permissions.BasePermission):
    """
    Vérifie que l'utilisateur est authentifié et possède une organisation active (ou est superuser).
    """
    message = "Accès refusé : vous devez posséder une organisation active."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        return hasattr(request.user, "organization") and request.user.organization.is_active

class IsEventOrganizationOwner(permissions.BasePermission):
    """
    Vérifie que l'utilisateur connecté est le propriétaire de l'organisation associée à l'événement.
    """
    message = "Accès refusé : vous n'êtes pas le propriétaire de cet événement."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        return hasattr(request.user, "organization") and request.user.organization.is_active

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        # Si l'objet est un Event
        if hasattr(obj, "organization"):
            return obj.organization == getattr(request.user, "organization", None)
            
        # Si l'objet est une Photo liée à un Event
        if hasattr(obj, "event"):
            return obj.event.organization == getattr(request.user, "organization", None)
            
        return False
