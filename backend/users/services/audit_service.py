from users.models import AuditLog

class AuditService:
    """
    Centralized service for logging audit events across the system.
    """

    @staticmethod
    def log(actor, action, target_user=None, fund=None, metadata=None, ip=None):
        """
        Creates a basic AuditLog entry with specified actor, action, and target.
        """
        AuditLog.objects.create(
            actor=actor,
            action=action,
            target_user=target_user,
            fund=fund,
            metadata=metadata or {},
            ip_address=ip,
        )

    @staticmethod
    def log_event(actor, action, target_model=None, target_id=None, description=None, ip_address=None):
        """
        Specialized log method for general events (like access denied).
        Maps generic parameters to AuditLog model.
        """
        metadata = {
            "target_model": target_model,
            "target_id": str(target_id) if target_id else None,
            "description": description,
        }
        
        AuditLog.objects.create(
            actor=actor,
            action=action,
            metadata=metadata,
            ip_address=ip_address,
        )