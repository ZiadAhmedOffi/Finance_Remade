from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Fund, ModelInput, InvestmentDeal, CurrentDeal
from decimal import Decimal
from datetime import datetime
from .views import solve_implied_return_rate

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
        """Test the new IRR calculation logic (forward compounding)."""
        # Investment at t=0, final value at T=5
        injections = {2024: 100.0}
        final_year = 2029
        final_value = 200.0
        # Expected IRR = 2.0 ^ (1/5) - 1 = 0.148698...
        expected_irr = (2.0 ** (1.0/5.0)) - 1.0
        calculated_irr = solve_implied_return_rate(injections, final_year, final_value)
        self.assertAlmostEqual(calculated_irr, expected_irr, places=6)

    def test_new_irr_logic(self):
        """Verify IRR in FundPerformanceView response (new logic)."""
        # Create a current deal
        # inception_year = 2024, current_year = 2026
        # Injections: 2024: 1M. Exit Value: 2M.
        # Formula: 1M * (1+r)^(2026-2024) = 2M => (1+r)^2 = 2 => r = sqrt(2)-1
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
        
        # In my setup: current_year = 2026 (assumed)
        current_year = datetime.now().year
        inception_year = 2024
        delta_t = current_year - inception_year # 2.0
        
        moic = c_metrics["moic"] # 2.0
        # Expected IRR = moic ^ (1/2.0) - 1
        expected_irr = (float(moic) ** (1.0/delta_t)) - 1.0
        self.assertAlmostEqual(c_metrics["irr"], expected_irr, places=6)
