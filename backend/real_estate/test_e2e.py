from django.test import TestCase
from django.contrib.auth import get_user_model
from real_estate.models import RealEstatePortfolio, RealEstateAssumptions
from real_estate.services.portfolio_service import PortfolioService
from real_estate.selectors.portfolio_selectors import PortfolioSelectors
import uuid

User = get_user_model()

class RealEstateE2ETests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(email="admin@finance.com", password="password123")

    def test_portfolio_lifecycle_e2e(self):
        """
        Tests the full lifecycle of a Real Estate Portfolio:
        Creation -> Assumption Generation -> Assumption Update -> Verification.
        """
        # 1. Create Portfolio
        portfolio_name = f"E2E Portfolio {uuid.uuid4().hex[:6]}"
        data = {
            "name": portfolio_name,
            "description": "E2E Test Description",
            "region": "Middle East"
        }
        
        portfolio = PortfolioService.create_portfolio(actor=self.actor, data=data)
        
        # 2. Verify Creation and Automatic Assumptions
        self.assertIsNotNone(portfolio.id)
        self.assertTrue(RealEstateAssumptions.objects.filter(portfolio=portfolio).exists())
        
        # 3. Update Assumptions
        update_data = {
            "active_scenario": "BULL",
            "default_appreciation_rate": "5.00",
            "forecast_horizon": 12
        }
        PortfolioService.update_assumptions(actor=self.actor, portfolio=portfolio, data=update_data)
        
        # 4. Verify Updates
        updated_portfolio = PortfolioSelectors.get_portfolio_by_id(portfolio.id)
        assumptions = updated_portfolio.assumptions
        self.assertEqual(assumptions.active_scenario, "BULL")
        self.assertEqual(float(assumptions.default_appreciation_rate), 5.00)
        self.assertEqual(assumptions.forecast_horizon, 12)
