from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from compliance.models import (
    ComplianceAuditEvent,
    ComplianceCase,
    ComplianceState,
    EvidenceDocument,
    MonitoringEvent,
    RiskAssessment,
    ReviewTask,
    ScreeningCheck,
)
from compliance.services.profile_service import ComplianceProfileService
from users.models import Role, User, UserRoleAssignment


class ComplianceWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.applicant_client = APIClient()
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="password123",
            first_name="Manager",
            last_name="User",
            is_active=True,
            status="ACTIVE",
        )
        self.applicant = User.objects.create_user(
            email="applicant@example.com",
            password="password123",
            first_name="Applicant",
            last_name="User",
            is_active=True,
            status="ACTIVE",
        )
        access_manager_role, _ = Role.objects.get_or_create(name="ACCESS_MANAGER", defaults={"is_system_role": True})
        UserRoleAssignment.objects.create(user=self.manager, role=access_manager_role)

        self.profile = ComplianceProfileService.ensure_individual_profile_for_user(self.applicant, create_case=True)
        self.case = self.profile.cases.order_by("-opened_at").first()

        self.client.force_authenticate(user=self.manager)
        self.applicant_client.force_authenticate(user=self.applicant)

    def test_assign_task_request_info_and_approve_case(self):
        assign_response = self.client.post(
            reverse("compliance-admin-case-assign-task", kwargs={"case_id": self.case.id}),
            {
                "task_type": "INITIAL_REVIEW",
                "priority": "HIGH",
                "reason": "Initial analyst review",
            },
            format="json",
        )
        self.assertEqual(assign_response.status_code, status.HTTP_201_CREATED)
        self.case.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.case.state, ComplianceState.IN_REVIEW)
        self.assertEqual(self.profile.current_state, ComplianceState.IN_REVIEW)
        self.assertEqual(ReviewTask.objects.filter(case=self.case).count(), 1)

        request_info_response = self.client.post(
            reverse("compliance-admin-case-request-information", kwargs={"case_id": self.case.id}),
            {"notes": "Need proof of address."},
            format="json",
        )
        self.assertEqual(request_info_response.status_code, status.HTTP_200_OK)
        self.case.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.case.state, ComplianceState.WAITING_FOR_APPLICANT)
        self.assertEqual(self.profile.current_state, ComplianceState.WAITING_FOR_APPLICANT)
        self.assertTrue(ReviewTask.objects.filter(case=self.case, task_type="REQUEST_INFORMATION").exists())

        approve_response = self.client.post(
            reverse("compliance-admin-case-approve", kwargs={"case_id": self.case.id}),
            {"notes": "Applicant satisfied all requirements."},
            format="json",
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.case.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.case.state, ComplianceState.APPROVED)
        self.assertEqual(self.profile.current_state, ComplianceState.APPROVED)
        self.assertFalse(self.profile.operability_blocked)
        self.assertTrue(
            ComplianceAuditEvent.objects.filter(case=self.case, event_type="CASE_APPROVED").exists()
        )

    def test_evidence_upload_and_risk_assessment(self):
        evidence_response = self.applicant_client.post(
            reverse("compliance-case-evidence", kwargs={"case_id": self.case.id}),
            {
                "document_type": "PROOF_OF_ADDRESS",
                "storage_mode": "APP_REFERENCE",
                "storage_reference": "secure://docs/proof-of-address.pdf",
            },
            format="json",
        )
        self.assertEqual(evidence_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(EvidenceDocument.objects.filter(case=self.case, document_type="PROOF_OF_ADDRESS").exists())

        risk_response = self.client.post(
            reverse("compliance-admin-case-risk-assessment", kwargs={"case_id": self.case.id}),
            {
                "risk_tier": "HIGH",
                "triggered_rules": ["ENTITY_OWNERSHIP_OPACITY", "PEP_MATCH_REVIEW"],
                "score_snapshot": {"score": 82, "weights": {"pep": 40, "ownership": 42}},
            },
            format="json",
        )
        self.assertEqual(risk_response.status_code, status.HTTP_201_CREATED)
        self.case.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.case.risk_tier, "HIGH")
        self.assertEqual(self.profile.current_risk_tier, "HIGH")
        self.assertTrue(RiskAssessment.objects.filter(case=self.case, risk_tier="HIGH").exists())

    def test_restrict_and_lift_case(self):
        approve_response = self.client.post(
            reverse("compliance-admin-case-approve", kwargs={"case_id": self.case.id}),
            {"notes": "Approved before alert."},
            format="json",
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

        restrict_response = self.client.post(
            reverse("compliance-admin-case-restrict", kwargs={"case_id": self.case.id}),
            {
                "restriction_type": "FULL_ACCOUNT_RESTRICTION",
                "reason_code": "SANCTIONS_ALERT",
                "notes": "Vendor alert pending review.",
            },
            format="json",
        )
        self.assertEqual(restrict_response.status_code, status.HTTP_201_CREATED)
        restriction_id = restrict_response.data["id"]

        self.case.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.case.state, ComplianceState.RESTRICTED)
        self.assertEqual(self.profile.current_state, ComplianceState.RESTRICTED)
        self.assertTrue(self.profile.operability_blocked)

        lift_response = self.client.post(
            reverse("compliance-admin-restriction-lift", kwargs={"restriction_id": restriction_id}),
            {"notes": "False positive cleared."},
            format="json",
        )
        self.assertEqual(lift_response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()
        self.case.refresh_from_db()
        self.assertEqual(self.profile.current_state, ComplianceState.APPROVED)
        self.assertFalse(self.profile.operability_blocked)
        self.assertEqual(self.case.state, ComplianceState.APPROVED)

    def test_vendor_submission_sync_and_rescreen(self):
        submit_response = self.applicant_client.post(
            reverse("compliance-case-submit", kwargs={"case_id": self.case.id}),
            {},
            format="json",
        )
        self.assertEqual(submit_response.status_code, status.HTTP_202_ACCEPTED)
        vendor_case_id = submit_response.data["id"]

        self.case.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.case.state, ComplianceState.WAITING_FOR_VENDOR)
        self.assertEqual(self.profile.current_state, ComplianceState.WAITING_FOR_VENDOR)
        self.assertGreater(ScreeningCheck.objects.filter(case=self.case).count(), 0)

        sync_response = self.client.post(
            reverse("compliance-admin-vendor-case-sync", kwargs={"vendor_case_id": vendor_case_id}),
            {
                "payload": {
                    "external_case_id": submit_response.data["external_case_id"],
                    "sync_status": "SYNCED",
                    "screenings": [
                        {
                            "check_type": "IDENTITY",
                            "outcome": "PASSED",
                            "summary": "Identity matched successfully.",
                        },
                        {
                            "check_type": "SANCTIONS",
                            "outcome": "PASSED",
                            "summary": "No sanctions hit.",
                        },
                    ],
                }
            },
            format="json",
        )
        self.assertEqual(sync_response.status_code, status.HTTP_202_ACCEPTED)

        self.case.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.case.state, ComplianceState.IN_REVIEW)
        self.assertEqual(self.profile.current_state, ComplianceState.IN_REVIEW)
        self.assertTrue(
            ScreeningCheck.objects.filter(case=self.case, check_type="IDENTITY", outcome="PASSED").exists()
        )
        self.assertTrue(
            ReviewTask.objects.filter(case=self.case, task_type="INITIAL_REVIEW", status="OPEN").exists()
        )

        rescreen_response = self.client.post(
            reverse("compliance-admin-profile-rescreen", kwargs={"profile_id": self.profile.id}),
            {"source": "manual_refresh"},
            format="json",
        )
        self.assertEqual(rescreen_response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(
            ComplianceCase.objects.filter(profile=self.profile, case_type="ONGOING_MONITORING").exists()
        )
        self.assertTrue(
            MonitoringEvent.objects.filter(profile=self.profile, event_type="PERIODIC_REVIEW_DUE").exists()
        )

    @override_settings(COMPLIANCE_PRIMARY_VENDOR_WEBHOOK_SECRET="top-secret")
    def test_primary_vendor_webhook_updates_case(self):
        submit_response = self.client.post(
            reverse("compliance-admin-case-submit-vendor", kwargs={"case_id": self.case.id}),
            {},
            format="json",
        )
        self.assertEqual(submit_response.status_code, status.HTTP_202_ACCEPTED)

        self.client.force_authenticate(user=None)
        webhook_response = self.client.post(
            reverse("compliance-primary-vendor-webhook"),
            {
                "external_case_id": submit_response.data["external_case_id"],
                "sync_status": "SYNCED",
                "screenings": [
                    {
                        "check_type": "IDENTITY",
                        "outcome": "PASSED",
                        "summary": "Webhook identity pass.",
                    }
                ],
            },
            format="json",
            HTTP_X_COMPLIANCE_WEBHOOK_SECRET="top-secret",
        )
        self.assertEqual(webhook_response.status_code, status.HTTP_202_ACCEPTED)

        self.case.refresh_from_db()
        self.assertEqual(self.case.state, ComplianceState.IN_REVIEW)
        self.assertTrue(
            ScreeningCheck.objects.filter(case=self.case, check_type="IDENTITY", outcome="PASSED").exists()
        )
