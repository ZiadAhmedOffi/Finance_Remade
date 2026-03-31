from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Fund, ModelInput, InvestmentDeal, CurrentDeal
from decimal import Decimal
from datetime import datetime
from .views import calculate_irr

User = get_user_model()

class IRRCalculationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="irr_test@example.com", password="password", is_active=True)
        from users.models import Role, UserRoleAssignment
        self.admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", defaults={"is_system_role": True})
        UserRoleAssignment.objects.get_or_create(user=self.user, role=self.admin_role, fund=None)
        
        self.fund = Fund.objects.create(name="IRR Fund", created_by=self.user)
        self.model_inputs = ModelInput.objects.get(fund=self.fund)
        self.model_inputs.inception_year = 2024
        self.model_inputs.exit_horizon = 5
        self.model_inputs.save()

    def test_current_irr_logic(self):
        """Test the current IRR calculation logic."""
        real_moic = 2.0
        exit_horizon = 5.0
        # Expected IRR = 2.0 ^ (1/5) - 1 = 1.148698 - 1 = 0.148698...
        expected_irr = (2.0 ** (1.0/5.0)) - 1.0
        calculated_irr = calculate_irr(real_moic, exit_horizon)
        self.assertAlmostEqual(calculated_irr, expected_irr, places=6)

    def test_new_irr_logic(self):
        """Verify IRR in FundPerformanceView response (new logic)."""
        # Create a current deal
        # inception_year = 2024, current_year = 2026
        # wait_time = (2026-1-2024) * 1M / 1M = 1.0
        CurrentDeal.objects.create(
            fund=self.fund,
            company_name="Deal 1",
            amount_invested=Decimal("1000000"),
            entry_valuation=Decimal("0"),
            latest_valuation=Decimal("2000000"),
            entry_year=2024
        )
        
        from rest_framework.test import APIRequestFactory, force_authenticate
        from .views import FundPerformanceView
        
        factory = APIRequestFactory()
        request = factory.get(f'/api/funds/{self.fund.id}/performance/')
        force_authenticate(request, user=self.user)
        
        view = FundPerformanceView.as_view()
        response = view(request, fund_id=str(self.fund.id))
        
        self.assertEqual(response.status_code, 200)
        c_metrics = response.data["current_deals_metrics"]
        
        # In my setup: current_year = 2026 (assumed by datetime.now().year if I run it now in 2026)
        # Wait, what is the current year in the test environment?
        # Today's date is March 31, 2026.
        current_year = datetime.now().year # 2026
        inception_year = 2024
        wait_time = float(current_year - 1 - inception_year) # 1.0
        
        real_moic = c_metrics["real_moic"]
        moic = c_metrics["moic"]
        # Expected IRR = moic ^ (1/1.0) - 1 = moic - 1
        expected_irr = (float(moic) ** (1.0/wait_time)) - 1.0
        self.assertAlmostEqual(c_metrics["irr"], expected_irr, places=6)
        self.assertAlmostEqual(c_metrics["irr"], float(moic) - 1.0, places=6)
