from django.db import transaction
from funds.models import Report
from users.services.audit_service import AuditService

class ReportService:
    @staticmethod
    @transaction.atomic
    def create_report(*, actor, data, ip_address=None):
        from funds.api.serializers import ReportSerializer
        
        serializer = ReportSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(created_by=actor)
        
        AuditService.log(
            actor=actor,
            action="REPORT_CREATED",
            fund=report.fund,
            metadata={"report_id": str(report.id), "name": report.name},
            ip=ip_address
        )
        return report

    @staticmethod
    @transaction.atomic
    def update_report(*, actor, report, data, ip_address=None):
        from funds.api.serializers import ReportSerializer
        
        serializer = ReportSerializer(report, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        
        AuditService.log(
            actor=actor,
            action="REPORT_UPDATED",
            fund=report.fund,
            metadata={"report_id": str(report.id), "name": report.name},
            ip=ip_address
        )
        return report

    @staticmethod
    @transaction.atomic
    def delete_report(*, actor, report, ip_address=None):
        report_id = str(report.id)
        report_name = report.name
        fund = report.fund
        
        AuditService.log(
            actor=actor,
            action="REPORT_DELETED",
            fund=fund,
            metadata={"report_id": report_id, "name": report_name},
            ip=ip_address
        )
        report.delete()
        return True

    @staticmethod
    @transaction.atomic
    def regenerate_report(*, actor, report, ip_address=None):
        report.status = "GENERATING"
        report.save()
        
        # TODO: Implement actual rendering logic here
        # Mock logic
        report.status = "ACTIVE"
        report.static_url = f"/reports/{report.slug}/index.html"
        report.save()
        
        AuditService.log(
            actor=actor,
            action="REPORT_GENERATED",
            fund=report.fund,
            metadata={"report_id": str(report.id), "slug": report.slug},
            ip=ip_address
        )
        return report
