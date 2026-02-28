from users.models import UserRoleAssignment


class PermissionService:
    """
    Centralized service for managing and validating user roles and permissions.
    """

    # -----------------------------
    # Core Role Check
    # -----------------------------
    @staticmethod
    def has_role(user, role_name, fund=None):
        """
        Generic check to see if a user has a specific role, 
        optionally tied to a specific fund.
        """
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
        """ Checks if user has the global SUPER_ADMIN role. """
        return PermissionService.has_role(user, "SUPER_ADMIN")

    @staticmethod
    def is_access_manager(user):
        """ Checks if user has the global ACCESS_MANAGER role. """
        return PermissionService.has_role(user, "ACCESS_MANAGER")

    # -----------------------------
    # Fund Roles
    # -----------------------------
    @staticmethod
    def is_sc_member(user, fund):
        """ Checks if user is a Steering Committee member for a specific fund. """
        return PermissionService.has_role(user, "SC_MEMBER", fund)

    @staticmethod
    def is_investor(user, fund):
        """ Checks if user is an Investor for a specific fund. """
        return PermissionService.has_role(user, "INVESTOR", fund)

    # -----------------------------
    # Business Logic Rules
    # -----------------------------
    @staticmethod
    def can_edit_fund(user, fund):
        """ Determines if a user has permissions to modify fund details. """
        return (
            PermissionService.is_super_admin(user)
            or PermissionService.is_sc_member(user, fund)
        )

    @staticmethod
    def can_view_fund(user, fund):
        """ Determines if a user has permissions to view fund details. """
        return (
            PermissionService.can_edit_fund(user, fund)
            or PermissionService.is_investor(user, fund)
        )

    @staticmethod
    def can_assign_roles(user):
        """ Determines if a user has permissions to assign roles to others. """
        return (
            PermissionService.is_super_admin(user)
            or PermissionService.is_access_manager(user)
        )

    @staticmethod
    def can_remove_roles(user):
        """ Determines if a user has permissions to remove roles from others. """
        return ( PermissionService.is_super_admin(user)
            or PermissionService.is_access_manager(user)
        )