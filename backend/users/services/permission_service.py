from users.models import UserRoleAssignment


class PermissionService:
    """
    Centralized service for managing and validating user roles and permissions.
    """

    # -----------------------------
    # Core Role Check
    # -----------------------------
    @staticmethod
    def has_role(user, role_name, fund=None, real_estate_portfolio=None):
        """
        Generic check to see if a user has a specific role, 
        optionally tied to a specific fund or real estate portfolio.
        """
        if not user or user.is_deleted or not user.is_active:
            return False

        return UserRoleAssignment.objects.filter(
            user=user,
            role__name=role_name,
            fund=fund,
            real_estate_portfolio=real_estate_portfolio
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
        return PermissionService.has_role(user, "STEERING_COMMITTEE", fund=fund)

    @staticmethod
    def is_investor(user, fund):
        """ Checks if user is an Investor for a specific fund. """
        return PermissionService.has_role(user, "INVESTOR", fund=fund)

    # -----------------------------
    # Real Estate Roles
    # -----------------------------
    @staticmethod
    def is_portfolio_manager(user, portfolio):
        """ Checks if user is a Portfolio Manager for a specific RE portfolio. """
        return PermissionService.has_role(user, "PORTFOLIO_MANAGER", real_estate_portfolio=portfolio)

    @staticmethod
    def is_re_investor(user, portfolio):
        """ Checks if user is an Investor for a specific RE portfolio. """
        return PermissionService.has_role(user, "INVESTOR", real_estate_portfolio=portfolio)

    # -----------------------------
    # Business Logic Rules - Funds
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

    # -----------------------------
    # Business Logic Rules - Real Estate
    # -----------------------------
    @staticmethod
    def can_edit_re_portfolio(user, portfolio):
        """ Determines if a user has permissions to modify RE portfolio details. """
        return (
            PermissionService.is_super_admin(user)
            or PermissionService.is_portfolio_manager(user, portfolio)
        )

    @staticmethod
    def can_view_re_portfolio(user, portfolio):
        """ Determines if a user has permissions to view RE portfolio details. """
        return (
            PermissionService.can_edit_re_portfolio(user, portfolio)
            or PermissionService.is_re_investor(user, portfolio)
        )

    # -----------------------------
    # Bookkeeping Permissions
    # -----------------------------
    @staticmethod
    def can_view_ledger(user, portfolio):
        """ Determines if a user can view the bookkeeping ledger. """
        return PermissionService.can_view_re_portfolio(user, portfolio)

    @staticmethod
    def can_edit_ledger(user, portfolio):
        """ Determines if a user can add/edit ledger transactions. """
        return PermissionService.can_edit_re_portfolio(user, portfolio)

    @staticmethod
    def can_finalize_ledger(user, portfolio):
        """ Determines if a user can close/finalize a fiscal year. """
        return PermissionService.can_edit_re_portfolio(user, portfolio)

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