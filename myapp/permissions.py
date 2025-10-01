from rest_framework.permissions import BasePermission

class IsVerifiedUser(BasePermission):
    """
    Allows access only to verified users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.email_verified

class IsRoleUser(BasePermission):
    """
    Allows access only to users with specific roles.
    """
    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles

    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                request.user.profile.role in self.allowed_roles)