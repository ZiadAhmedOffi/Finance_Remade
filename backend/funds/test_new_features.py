from django.test import TestCase
from django.contrib.auth import get_user_model
from funds.models import Fund, InvestmentDeal, ModelInput
from funds.utils import calculators
from decimal import Decimal

User = get_user_model()

class NewFeaturesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test_new@example.com", password="password", is_active=True)
        from users.models import Role, UserRoleAssignment
        self.admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", defaults={"is_system_role": True})
        UserRoleAssignment.objects.get_or_create(user=self.user, role=self.admin_role)
        self.fund = Fund.objects.create(name="New Features Fund", created_by=self.user, status="FUTURE", target_appreciation=15.0)

    def test_investment_deal_type(self):
        deal = InvestmentDeal.objects.create(
            fund=self.fund,
            company_name="Test Co",
            amount_invested=100000,
            entry_valuation=1000000,
            investment_type="VENTURE_DEBT"
        )
        self.assertEqual(deal.investment_type, "VENTURE_DEBT")
        self.assertEqual(dict(InvestmentDeal.INVESTMENT_TYPE_CHOICES)["VENTURE_DEBT"], "Venture Debt")

    def test_trajectory_calculation_for_future_fund(self):
        # Setup parameters
        start_year = 2024
        end_year = 2026
        current_year = 2024
        fund_end_year = 2030
        c_injections = {2024: 100.0}
        p_injections = {}
        safe_c_irr = 0.2
        safe_p_irr = 0.2
        target_appreciation = 15.0 # 15%

        # Test Future Fund (should use target_appreciation as constant 15%)
        trajectory = calculators.calculate_nav_trajectory(
            start_year, end_year, current_year, fund_end_year,
            c_injections, p_injections,
            safe_c_irr, safe_p_irr,
            is_future=True,
            target_appreciation=target_appreciation
        )

        # Yr 2024: c_pv = 100 + (0 * 0.15) = 100
        # Yr 2025: c_pv = 100 + (100 * 0.15) = 115
        # Yr 2026: c_pv = 115 + (115 * 0.15) = 132.25

        self.assertEqual(trajectory[0]["year"], 2024)
        self.assertAlmostEqual(trajectory[0]["c_pv"], 100.0)
        self.assertAlmostEqual(trajectory[0]["irr"], 0.15)

        self.assertEqual(trajectory[1]["year"], 2025)
        self.assertAlmostEqual(trajectory[1]["c_pv"], 115.0)
        self.assertAlmostEqual(trajectory[1]["irr"], 0.15)

        self.assertEqual(trajectory[2]["year"], 2026)
        self.assertAlmostEqual(trajectory[2]["c_pv"], 132.25)
        self.assertAlmostEqual(trajectory[2]["irr"], 0.15)

    def test_trajectory_calculation_for_established_fund(self):
        # Setup parameters
        start_year = 2024
        end_year = 2025
        current_year = 2024
        fund_end_year = 2030
        c_injections = {2024: 100.0}
        p_injections = {}
        safe_c_irr = 0.2
        safe_p_irr = 0.2

        # Test Established Fund (should use IRR with decay)
        trajectory = calculators.calculate_nav_trajectory(
            start_year, end_year, current_year, fund_end_year,
            c_injections, p_injections,
            safe_c_irr, safe_p_irr,
            is_future=False
        )

        # Yr 2024: effective_irr = 0.2 * (0.75^1) = 0.15
        # Yr 2024: c_pv = 100 + (0 * 0.15) = 100
        # Yr 2025: effective_irr = 0.2 * (0.75^2) = 0.1125
        # Yr 2025: c_pv = 100 + (100 * 0.1125) = 111.25

        self.assertEqual(trajectory[0]["year"], 2024)
        self.assertAlmostEqual(trajectory[0]["c_pv"], 100.0)
        self.assertAlmostEqual(trajectory[0]["irr"], 0.15)

        self.assertEqual(trajectory[1]["year"], 2025)
        self.assertAlmostEqual(trajectory[1]["c_pv"], 111.25)
        self.assertAlmostEqual(trajectory[1]["irr"], 0.1125)

    def test_api_view_future_fund(self):
        # Create a deal
        InvestmentDeal.objects.create(
            fund=self.fund,
            company_name="Future Co",
            amount_invested=Decimal("100000"),
            entry_valuation=Decimal("900000"),
            investment_type="EQUITY",
            entry_year=2024,
            exit_year=2029
        )
        
        from rest_framework.test import APIRequestFactory, force_authenticate
        from funds.api.views import FundPerformanceView
        
        factory = APIRequestFactory()
        request = factory.get(f'/api/funds/{self.fund.id}/performance/')
        force_authenticate(request, user=self.user)
        
        view = FundPerformanceView.as_view()
        response = view(request, fund_id=str(self.fund.id))
        
        self.assertEqual(response.status_code, 200)
        perf_table = response.data["dashboard"]["performance_table"]
        
        # Check that IRR in perf_table is target_appreciation / 100 = 0.15
        for entry in perf_table:
            if entry["year"] >= 2024:
                self.assertAlmostEqual(entry["irr"], 0.15)
        
        # Check that investment_type is in investment_deals
        deals = response.data["investment_deals"]
        self.assertEqual(deals[0]["investment_type"], "EQUITY")
