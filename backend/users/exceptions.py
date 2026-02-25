from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied, NotAuthenticated
from users.services.audit_service import AuditService


def custom_exception_handler(exc, context):
    """
    Custom exception handler that logs denied access attempts.
    """

    response = exception_handler(exc, context)

    request = context.get("request")
    view = context.get("view")

    if response is None:
        return response

    if isinstance(exc, (PermissionDenied, NotAuthenticated)):

        if request and request.user.is_authenticated:
            AuditService.log_event(
                actor=request.user,
                action="ACCESS_DENIED",
                target_model=view.__class__.__name__,
                target_id=None,
                description=f"Denied attempt on {request.path}",
                ip_address=get_client_ip(request),
            )
        else:
            AuditService.log_event(
                actor=None,
                action="UNAUTHENTICATED_ACCESS_DENIED",
                target_model=view.__class__.__name__,
                target_id=None,
                description=f"Unauthenticated denied attempt on {request.path}",
                ip_address=get_client_ip(request),
            )

    return response


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")