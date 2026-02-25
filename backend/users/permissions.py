from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from users.services.permission_service import PermissionService


class IsSuperAdmin(BasePermission):
    """
    Allows access only to SUPER_ADMIN users.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return PermissionService.is_super_admin(request.user)


class IsAccessManager(BasePermission):
    """
    Allows access to ACCESS_MANAGER or SUPER_ADMIN.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return (
            PermissionService.is_super_admin(request.user)
            or PermissionService.is_access_manager(request.user)
        )


class FundPermission(BasePermission):
    """
    Object-level permission for Fund access.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # SAFE METHODS → View permissions
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return PermissionService.can_view_fund(user, obj)

        # WRITE METHODS → Edit permissions
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return PermissionService.can_edit_fund(user, obj)

        return False


class RoleRequired(BasePermission):
    """
    Generic reusable role permission.
    Views must define:
        required_roles = ["ROLE_NAME"]
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        required_roles = getattr(view, "required_roles", [])

        if not required_roles:
            return False

        return PermissionService.has_any_role(
            request.user,
            required_roles
        )