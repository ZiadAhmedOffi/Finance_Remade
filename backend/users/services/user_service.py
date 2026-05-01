from django.db import transaction
from users.models import User, Role, UserRoleAssignment
from users.services.audit_service import AuditService
from users.services.permission_service import PermissionService
from users.interfaces.fund_interface import FundInterface

class UserService:
    def __init__(self, fund_interface: FundInterface):
        self.fund_interface = fund_interface

    @transaction.atomic
    def approve_user(self, user_id, actor, ip_address):
        try:
            user = User.objects.get(id=user_id, status="PENDING")
        except User.DoesNotExist:
            raise ValueError("User not found or already processed")

        user.status = "ACTIVE"
        user.is_active = True
        user.save(update_fields=["status", "is_active"])

        AuditService.log(
            actor=actor,
            action="USER_APPROVED",
            target_user=user,
            metadata={"description": f"User {user.email} was approved."},
            ip=ip_address,
        )
        return user

    @transaction.atomic
    def reject_user(self, user_id, actor, ip_address):
        try:
            user = User.objects.get(id=user_id, status="PENDING")
        except User.DoesNotExist:
            raise ValueError("User not found or already processed")

        user.status = "REJECTED"
        user.is_active = False
        user.save(update_fields=["status", "is_active"])

        AuditService.log(
            actor=actor,
            action="USER_REJECTED",
            target_user=user,
            metadata={"description": f"User {user.email} was rejected."},
            ip=ip_address,
        )
        return user

    @transaction.atomic
    def deactivate_user(self, user_id, actor, ip_address):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found")

        user.is_active = False
        user.status = "REJECTED"
        user.save()

        AuditService.log(
            actor=actor,
            action="USER_SOFT_DELETED",
            target_user=user,
            metadata={"description": f"User {user.email} was deactivated."},
            ip=ip_address
        )
        return user

    @transaction.atomic
    def reset_password(self, user_id, new_password, actor, ip_address):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found")

        user.set_password(new_password)
        user.save()

        AuditService.log(
            actor=actor,
            action="PASSWORD_RESET",
            target_user=user,
            metadata={"description": f"Password for user {user.email} was reset by super admin."},
            ip=ip_address
        )
        return user

    @transaction.atomic
    def assign_role(self, user_id, role_id, fund_id, actor, ip_address):
        try:
            target_user = User.objects.get(id=user_id)
            role = Role.objects.get(id=role_id)
        except (User.DoesNotExist, Role.DoesNotExist):
            raise ValueError("User or Role not found")

        is_super_admin = PermissionService.is_super_admin(actor)
        
        if role.name in ["SUPER_ADMIN", "ACCESS_MANAGER"] and not is_super_admin:
            raise PermissionError("Only Super Admins can assign Admin/Manager roles.")

        fund = None
        if role.name in ["INVESTOR", "STEERING_COMMITTEE"]:
            if not fund_id:
                raise ValueError(f"Role {role.name} requires a fund.")
            
            fund = self.fund_interface.get_fund_by_id(fund_id)
            if not fund:
                raise ValueError("Fund not found")

        assignment, created = UserRoleAssignment.objects.get_or_create(
            user=target_user,
            role=role,
            fund=fund,
            defaults={"assigned_by": actor}
        )

        if not created:
            return assignment, False

        if not target_user.is_active or target_user.status != "ACTIVE":
            target_user.is_active = True
            target_user.status = "ACTIVE"
            target_user.save(update_fields=["is_active", "status"])

        if fund:
            action_map = {
                "STEERING_COMMITTEE": "SC_MEMBER_ASSIGNED",
                "INVESTOR": "INVESTOR_ASSIGNED",
            }
            self.fund_interface.create_fund_log(
                actor=actor,
                target_fund=fund,
                action=action_map.get(role.name, "ROLE_ASSIGNED"),
                metadata={"user_email": target_user.email, "role": role.name}
            )

        AuditService.log(
            actor=actor,
            action="ROLE_ASSIGNED",
            target_user=target_user,
            fund=fund,
            metadata={"role": role.name},
            ip=ip_address
        )

        return assignment, True

    @transaction.atomic
    def remove_role(self, user_id, role_id, fund_id, actor, ip_address):
        try:
            target_user = User.objects.get(id=user_id)
            role = Role.objects.get(id=role_id)
        except (User.DoesNotExist, Role.DoesNotExist):
            raise ValueError("User or Role not found")

        is_super_admin = PermissionService.is_super_admin(actor)
        
        if role.name in ["SUPER_ADMIN", "ACCESS_MANAGER"] and not is_super_admin:
            raise PermissionError("Only Super Admins can remove Admin/Manager roles.")

        try:
            assignment = UserRoleAssignment.objects.get(
                user=target_user,
                role=role,
                fund=fund_id if fund_id else None
            )
            assignment.delete()
            
            AuditService.log(
                actor=actor,
                action="ROLE_REMOVED",
                target_user=target_user,
                fund=assignment.fund,
                metadata={
                    "role": role.name,
                    "description": f"Role {role.name} was removed from {target_user.email}."
                },
                ip=ip_address
            )

            if fund_id:
                fund = self.fund_interface.get_fund_by_id(fund_id)
                if fund:
                    self.fund_interface.create_fund_log(
                        actor=actor,
                        target_fund=fund,
                        action="ROLE_REMOVED",
                        metadata={"user_email": target_user.email, "role": role.name}
                    )
            
            return True
        except UserRoleAssignment.DoesNotExist:
            raise ValueError("Role assignment not found")
