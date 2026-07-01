from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from compliance.models import ComplianceState
from compliance.services.profile_service import ComplianceProfileService
from real_estate.models import RealEstateAssumptions, RealEstatePortfolio
from users.models import Role, User, UserRoleAssignment


class RealEstateComplianceGatingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            email="re-admin@example.com",
            password="password123",
            is_active=True,
            status="ACTIVE",
        )
        self.investor_user = User.objects.create_user(
            email="re-investor@example.com",
            password="password123",
            is_active=True,
            status="ACTIVE",
        )

        super_admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", is_system_role=True)
        investor_role, _ = Role.objects.get_or_create(name="INVESTOR", is_system_role=True)
        UserRoleAssignment.objects.create(user=self.admin_user, role=super_admin_role)

        self.portfolio = RealEstatePortfolio.objects.create(name="Compliance Portfolio", created_by=self.admin_user)
        RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date="2024-01-01",
            acquisition_fee_percentage=Decimal("0.00"),
            default_appreciation_rate=Decimal("0.00"),
            default_vacancy_rate=Decimal("0.00"),
            maintenance_percentage_of_value=Decimal("0.00"),
        )
        UserRoleAssignment.objects.create(
            user=self.investor_user,
            role=investor_role,
            real_estate_portfolio=self.portfolio,
        )

        self.client.force_authenticate(user=self.admin_user)

    def _approve_investor(self, user):
        profile = ComplianceProfileService.ensure_individual_profile_for_user(user, create_case=True)
        profile.current_state = ComplianceState.APPROVED
        profile.operability_blocked = False
        profile.save(update_fields=["current_state", "operability_blocked", "updated_at"])
        case = profile.cases.order_by("-opened_at").first()
        case.state = ComplianceState.APPROVED
        case.save(update_fields=["state"])

    def test_real_estate_investor_action_blocked_without_approved_compliance(self):
        response = self.client.post(
            reverse("real-estate-portfolio-investor-actions", kwargs={"pk": self.portfolio.id}),
            {
                "investor": str(self.investor_user.id),
                "type": "PRIMARY_INVESTMENT",
                "year": 2024,
                "amount": "50000.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Compliance gate denied", response.data["error"])

    def test_real_estate_investor_action_allowed_after_approval(self):
        self._approve_investor(self.investor_user)

        response = self.client.post(
            reverse("real-estate-portfolio-investor-actions", kwargs={"pk": self.portfolio.id}),
            {
                "investor": str(self.investor_user.id),
                "type": "PRIMARY_INVESTMENT",
                "year": 2024,
                "amount": "50000.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
