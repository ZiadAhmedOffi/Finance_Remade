from funds.models import Report
from users.services.permission_service import PermissionService

def get_reports_by_type(user, report_type="DYNAMIC"):
    if PermissionService.is_super_admin(user):
        return Report.objects.filter(report_type=report_type)
    else:
        from users.models import UserRoleAssignment
        managed_funds = UserRoleAssignment.objects.filter(
            user=user, role__name="STEERING_COMMITTEE"
        ).values_list("fund_id", flat=True)
        return Report.objects.filter(fund_id__in=managed_funds, report_type=report_type)

def get_report_by_id(report_id):
    try:
        return Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return None
