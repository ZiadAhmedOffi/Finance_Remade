from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Fund, ModelInput, InvestmentDeal, CurrentDeal
from decimal import Decimal

User = get_user_model()

class FundModelTest(TestCase):
    def test_model_input_creation_on_fund_create(self):
        """Test that ModelInput is created when a Fund is created via signals."""
        user = User.objects.create_user(email="test@example.com", password="password", is_active=True)
        fund = Fund.objects.create(name="Test Fund", created_by=user)
        
        self.assertTrue(ModelInput.objects.filter(fund=fund).exists())
        model_input = ModelInput.objects.get(fund=fund)
        self.assertEqual(model_input.target_fund_size, 100000000.00)

class FundCalculationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test_calcs@example.com", password="password", is_active=True)
        from users.models import Role, UserRoleAssignment
        self.admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", defaults={"is_system_role": True})
        UserRoleAssignment.objects.get_or_create(user=self.user, role=self.admin_role)
        self.fund = Fund.objects.create(name="Calc Fund", created_by=self.user)

    def test_investment_deal_post_money_valuation(self):
        """Verify that InvestmentDeal exit_valuation uses POST-money."""
        deal = InvestmentDeal.objects.create(
            fund=self.fund,
            company_name="Future Co",
            amount_invested=Decimal("1000000"), # 1M
            entry_valuation=Decimal("4000000"),  # 4M PRE -> 5M POST
            base_factor=Decimal("2.00"),         # 2x on company
            selected_scenario="BASE"
        )
        
        # Ownership should be 1 / (1 + 4) = 20%
        from .serializers import InvestmentDealSerializer
        serializer = InvestmentDealSerializer(deal)
        data = serializer.data
        
        # Post-money = 5M. Factor 2x -> Exit Valuation = 10M.
        # Ownership = 20% -> Exit Value = 2M.
        self.assertEqual(data["post_money_ownership"], 20.0)
        self.assertEqual(float(data["exit_valuation"]), 10000000.0)
        self.assertEqual(float(data["exit_value"]), 2000000.0)

    def test_current_deal_moic_post_money(self):
        """Verify that CurrentDeal MOIC uses POST-money."""
        deal = CurrentDeal.objects.create(
            fund=self.fund,
            company_name="Current Co",
            amount_invested=Decimal("2000000"), # 2M
            entry_valuation=Decimal("8000000"),  # 8M PRE -> 10M POST
            latest_valuation=Decimal("15000000") # 15M current company valuation
        )
        
        # Fund Ownership = 2M / 10M = 20%
        # Fund value = 20% * 15M = 3M.
        # Fund MOIC = 3M / 2M = 1.5x.
        from .serializers import CurrentDealSerializer
        serializer = CurrentDealSerializer(deal)
        data = serializer.data
        
        self.assertEqual(data["post_money_ownership"], 20.0)
        self.assertEqual(data["moic"], 1.5)
        self.assertEqual(float(data["final_exit_amount"]), 3000000.0)

    def test_fund_performance_prognosis_only(self):
        """Verify that dashboard metrics only include prognosis deals."""
        # Create one current deal
        CurrentDeal.objects.create(
            fund=self.fund,
            company_name="Past Co",
            amount_invested=Decimal("1000000"),
            entry_valuation=Decimal("9000000"),
            latest_valuation=Decimal("10000000")
        )
        # Create one prognosis deal
        InvestmentDeal.objects.create(
            fund=self.fund,
            company_name="Future Co",
            amount_invested=Decimal("500000"),
            entry_valuation=Decimal("4500000"), # 10% ownership
            base_factor=Decimal("2.00"),
            selected_scenario="BASE"
        )
        
        from rest_framework.test import APIRequestFactory, force_authenticate
        from .views import FundPerformanceView
        
        factory = APIRequestFactory()
        request = factory.get(f'/api/funds/{self.fund.id}/performance/')
        force_authenticate(request, user=self.user)
        
        view = FundPerformanceView.as_view()
        response = view(request, fund_id=str(self.fund.id))
        
        self.assertEqual(response.status_code, 200)
        dashboard = response.data["dashboard"]
        
        # Prognosis only: total_invested should be 500,000, not 1,500,000
        self.assertEqual(float(dashboard["total_invested"]), 500000.0)
        self.assertEqual(dashboard["total_deals"], 1) # Only 1 prognosis deal
