from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from users.models import UserRoleAssignment, User
from users.services.audit_service import AuditService


@receiver(post_save, sender=UserRoleAssignment)
def log_role_assignment(sender, instance, created, **kwargs):
    if created:
        AuditService.log(
            actor=instance.assigned_by,
            action="ROLE_ASSIGNED",
            target_user=instance.user,
            fund=instance.fund,
            metadata={"role": instance.role.name}
        )


@receiver(post_delete, sender=UserRoleAssignment)
def log_role_removal(sender, instance, **kwargs):
    AuditService.log(
        actor=None,
        action="ROLE_REMOVED",
        target_user=instance.user,
        fund=instance.fund,
        metadata={"role": instance.role.name}
    )


@receiver(post_save, sender=User)
def log_soft_delete(sender, instance, **kwargs):
    if instance.is_deleted:
        AuditService.log(
            actor=None,
            action="USER_SOFT_DELETED",
            target_user=instance,
        )