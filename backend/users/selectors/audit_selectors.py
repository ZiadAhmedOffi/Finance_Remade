from users.models import AuditLog

def get_all_audit_logs():
    return AuditLog.objects.all().select_related("actor", "target_user", "fund").order_by("-timestamp")
