from django.test import TestCase
from unittest.mock import patch
from datetime import datetime
from decimal import Decimal
from .models import Fund, ModelInput, CurrentDeal
from .logic import get_total_fund_portfolio

class IRRReductionTest(TestCase):
    def setUp(self):
        # Create a fund
        self.fund = Fund.objects.create(name="IRR Test Fund")
        
        # Create model inputs
        self.model_inputs = ModelInput.objects.create(
            fund=self.fund,
            inception_year=2020,
            fund_life=10,
            management_fee=0, # Simplify
            admin_cost=0
        )
        
        # Create a current deal
        # Invest 1,000,000 in 2020.
        # entry_valuation = 4,000,000 => post-money = 5,000,000.
        # Ownership = 20%.
        # latest_valuation = 10,000,000.
        # MOIC = 10M / 5M = 2.0x.
        # Holding period (if current_year is 2024) = 4 years.
        # Current IRR = (2.0)^(1/4) - 1 = 18.92% (approx).
        self.deal = CurrentDeal.objects.create(
            fund=self.fund,
            company_name="Test Company",
            entry_year=2020,
            amount_invested=Decimal("1000000.00"),
            entry_valuation=Decimal("4000000.00"),
            latest_valuation=Decimal("10000000.00"),
            latest_valuation_year=2023
        )

    @patch('funds.logic.datetime')
    @patch('funds.views.datetime')
    def test_irr_reduction_compounding(self, mock_datetime_views, mock_datetime_logic):
        # Mock current year as 2024
        mock_now = datetime(2024, 1, 1)
        mock_datetime_views.now.return_value = mock_now
        mock_datetime_logic.now.return_value = mock_now
        
        # Calculate current portfolio value in 2023 (before reduction starts)
        # 2020: 1M injection. 
        # IRR (r) is such that 1M * (1+r)^3 = 2M (since 20% of 10M is 2M in 2023)
        # wait, the logic uses c_gross_exit_value which is sum of final_exit_amount.
        # final_exit_amount = ownership % * latest_valuation = 0.2 * 10M = 2M.
        # c_total_invested = 1M.
        # c_irr = solve_implied_return_rate({2020: 1M}, 2023, 2M)
        # 1M * (1+r)^(2023-2020) = 2M => (1+r)^3 = 2 => 1+r = 1.2599 => r = 0.2599
        
        # 2020: PV = 1M
        # 2021: PV = 1M * (1+r) = 1.2599M
        # 2022: PV = 1.2599M * (1+r) = 1.5874M
        # 2023: PV = 1.5874M * (1+r) = 2.0M
        
        # 2024 (current year):
        # Reduction Factor = 0.75 ^ (2024 - 2024 + 1) = 0.75
        # Effective IRR = 0.2599 * 0.75 = 0.194925
        # Appreciation = 2M * 0.194925 = 0.38985M
        # PV 2024 = 2M + 0.38985M = 2.38985M
        
        # 2025:
        # Reduction Factor = 0.75 ^ (2025 - 2024 + 1) = 0.75^2 = 0.5625
        # Effective IRR = 0.2599 * 0.5625 = 0.14619
        # Appreciation = 2.38985M * 0.14619 = 0.34937M
        # PV 2025 = 2.38985M + 0.34937M = 2.73922M
        
        pv_2023 = get_total_fund_portfolio(self.fund, 2023)
        self.assertAlmostEqual(pv_2023, 2000000.0, places=1)
        
        pv_2024 = get_total_fund_portfolio(self.fund, 2024)
        r = (2.0 ** (1.0/3.0)) - 1.0
        expected_pv_2024 = 2000000.0 * (1 + r * 0.75)
        self.assertAlmostEqual(pv_2024, expected_pv_2024, places=1)
        
        pv_2025 = get_total_fund_portfolio(self.fund, 2025)
        expected_pv_2025 = expected_pv_2024 * (1 + r * (0.75 ** 2))
        self.assertAlmostEqual(pv_2025, expected_pv_2025, places=1)
