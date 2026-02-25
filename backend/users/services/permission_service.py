from users.models import UserRoleAssignment


class PermissionService:

    # -----------------------------
    # Core Role Check
    # -----------------------------
    @staticmethod
    def has_role(user, role_name, fund=None):
        if not user or user.is_deleted or not user.is_active:
            return False

        return UserRoleAssignment.objects.filter(
            user=user,
            role__name=role_name,
            fund=fund
        ).exists()

    # -----------------------------
    # System Roles
    # -----------------------------
    @staticmethod
    def is_super_admin(user):
        return PermissionService.has_role(user, "SUPER_ADMIN")

    @staticmethod
    def is_access_manager(user):
        return PermissionService.has_role(user, "ACCESS_MANAGER")

    # -----------------------------
    # Fund Roles
    # -----------------------------
    @staticmethod
    def is_sc_member(user, fund):
        return PermissionService.has_role(user, "SC_MEMBER", fund)

    @staticmethod
    def is_investor(user, fund):
        return PermissionService.has_role(user, "INVESTOR", fund)

    # -----------------------------
    # Business Logic Rules
    # -----------------------------
    @staticmethod
    def can_edit_fund(user, fund):
        return (
            PermissionService.is_super_admin(user)
            or PermissionService.is_sc_member(user, fund)
        )

    @staticmethod
    def can_view_fund(user, fund):
        return (
            PermissionService.can_edit_fund(user, fund)
            or PermissionService.is_investor(user, fund)
        )

    @staticmethod
    def can_assign_roles(user):
        return (
            PermissionService.is_super_admin(user)
            or PermissionService.is_access_manager(user)
        )

    @staticmethod
    def can_remove_roles(user):
        return ( PermissionService.is_super_admin(user)
            or PermissionService.is_access_manager(user)
        )