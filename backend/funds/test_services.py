from django.test import TestCase
from django.contrib.auth import get_user_model
from funds.models import Fund, ModelInput, RiskAssessment, Report, FundLog
from funds.services.fund_service import FundService
from funds.services.risk_assessment_service import RiskAssessmentService
from funds.services.report_service import ReportService
from decimal import Decimal

User = get_user_model()

class ServiceIntegrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="service_test@example.com", password="password", is_active=True)
        from users.models import Role, UserRoleAssignment
        self.admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", defaults={"is_system_role": True})
        UserRoleAssignment.objects.get_or_create(user=self.user, role=self.admin_role)

    def test_fund_service_create_fund(self):
        data = {
            "name": "New Fund",
            "tag": "VC",
            "status": "FUTURE"
        }
        fund = FundService.create_fund(actor=self.user, data=data)
        self.assertEqual(fund.name, "New Fund")
        self.assertEqual(fund.created_by, self.user)
        self.assertTrue(FundLog.objects.filter(target_fund=fund, action="FUND_CREATED").exists())

    def test_fund_service_update_fund(self):
        fund = Fund.objects.create(name="Old Name", created_by=self.user)
        data = {"name": "Updated Name", "status": "ESTABLISHED"}
        updated_fund = FundService.update_fund(actor=self.user, fund=fund, data=data)
        self.assertEqual(updated_fund.name, "Updated Name")
        self.assertEqual(updated_fund.status, "ESTABLISHED")
        self.assertTrue(FundLog.objects.filter(target_fund=fund, action="FUND_STATUS_UPDATED").exists())
        self.assertTrue(FundLog.objects.filter(target_fund=fund, action="FUND_INFO_UPDATED").exists())

    def test_risk_assessment_service_batch_upsert(self):
        fund = Fund.objects.create(name="Risk Fund", created_by=self.user)
        data = [
            {"company_name": "Co A", "execution_capacity_score": 8.0},
            {"company_name": "Co B", "market_validation_score": 7.0}
        ]
        results = RiskAssessmentService.batch_upsert_risk_assessments(fund=fund, data=data)
        self.assertEqual(len(results), 2)
        self.assertEqual(RiskAssessment.objects.filter(fund=fund).count(), 2)
        
        # Update existing
        update_data = [{"company_name": "Co A", "execution_capacity_score": 9.0}]
        RiskAssessmentService.batch_upsert_risk_assessments(fund=fund, data=update_data)
        self.assertEqual(RiskAssessment.objects.get(fund=fund, company_name="Co A").execution_capacity_score, 9.0)

    def test_report_service_lifecycle(self):
        fund = Fund.objects.create(name="Report Fund", created_by=self.user)
        report_data = {
            "name": "Quarterly Report",
            "slug": "q-report",
            "fund": fund.id,
            "report_type": "DYNAMIC",
            "config_json": {}
        }
        report = ReportService.create_report(actor=self.user, data=report_data)
        self.assertEqual(report.name, "Quarterly Report")
        
        # Regenerate
        ReportService.regenerate_report(actor=self.user, report=report)
        report.refresh_from_db()
        self.assertEqual(report.status, "ACTIVE")
        self.assertIsNotNone(report.static_url)
        
        # Delete
        ReportService.delete_report(actor=self.user, report=report)
        self.assertFalse(Report.objects.filter(id=report.id).exists())
