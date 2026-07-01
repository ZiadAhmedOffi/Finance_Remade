from rest_framework.permissions import BasePermission

from users.services.permission_service import PermissionService


class IsComplianceStaff(BasePermission):
    """
    Placeholder permission for the dedicated compliance role model.
    Phase 1 scaffolding keeps this simple until compliance-specific role
    assignments are wired into the authorization layer.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return bool(
            request.user.is_staff
            or PermissionService.is_super_admin(request.user)
            or PermissionService.is_access_manager(request.user)
        )
