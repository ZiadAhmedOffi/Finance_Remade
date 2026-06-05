from django.db import transaction
from ..models import RealEstateReport
from users.services.audit_service import AuditService

class RealEstateReportService:
    @staticmethod
    @transaction.atomic
    def create_report(*, actor, data, ip_address=None):
        from ..api.serializers import RealEstateReportSerializer
        
        serializer = RealEstateReportSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(created_by=actor)
        
        AuditService.log(
            actor=actor,
            action="RE_REPORT_CREATED",
            metadata={"report_id": str(report.id), "name": report.name, "portfolio_id": str(report.portfolio.id)},
            ip=ip_address
        )
        return report

    @staticmethod
    @transaction.atomic
    def update_report(*, actor, report, data, ip_address=None):
        from ..api.serializers import RealEstateReportSerializer
        
        serializer = RealEstateReportSerializer(report, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        
        AuditService.log(
            actor=actor,
            action="RE_REPORT_UPDATED",
            metadata={"report_id": str(report.id), "name": report.name, "portfolio_id": str(report.portfolio.id)},
            ip=ip_address
        )
        return report

    @staticmethod
    @transaction.atomic
    def delete_report(*, actor, report, ip_address=None):
        report_id = str(report.id)
        report_name = report.name
        portfolio_id = str(report.portfolio.id)
        
        AuditService.log(
            actor=actor,
            action="RE_REPORT_DELETED",
            metadata={"report_id": report_id, "name": report_name, "portfolio_id": portfolio_id},
            ip=ip_address
        )
        report.delete()
        return True

    @staticmethod
    @transaction.atomic
    def regenerate_report(*, actor, report, ip_address=None):
        report.status = "GENERATING"
        report.save()
        
        # Real-world: trigger async task. For now, sync mock.
        report.status = "ACTIVE"
        report.static_url = f"/reports/re/{report.slug}/index.html"
        report.save()
        
        AuditService.log(
            actor=actor,
            action="RE_REPORT_GENERATED",
            metadata={"report_id": str(report.id), "slug": report.slug, "portfolio_id": str(report.portfolio.id)},
            ip=ip_address
        )
        return report
