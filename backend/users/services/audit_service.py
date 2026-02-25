from users.models import AuditLog

class AuditService:

    @staticmethod
    def log(actor, action, target_user=None, fund=None, metadata=None, ip=None):
        AuditLog.objects.create(
            actor=actor,
            action=action,
            target_user=target_user,
            fund=fund,
            metadata=metadata or {},
            ip_address=ip,
        )