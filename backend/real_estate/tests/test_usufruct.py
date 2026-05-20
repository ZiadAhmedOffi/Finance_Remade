from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from ..models import RealEstatePortfolio, RealEstateAssumptions, Property, UsufructDetails
from ..selectors.property_selectors import PropertySelector
from ..selectors.portfolio_dashboard_selectors import PortfolioDashboardSelector
from ..selectors.cash_flow_selectors import CashFlowSelectors

User = get_user_model()

class UsufructPropertyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.portfolio = RealEstatePortfolio.objects.create(name="Test Portfolio", created_by=self.user)
        self.assumptions = RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date=date(2023, 1, 1),
            forecast_horizon=5,
            default_appreciation_rate=Decimal("5.00"),
            default_rental_growth_rate=Decimal("3.00"),
            property_mgmt_fee_percentage=Decimal("0.00"),
            maintenance_percentage_of_value=Decimal("0.00")
        )

    def test_usufruct_metrics(self):
        """Verify individual metrics for a usufruct property in Year 1."""
        reference_date = date(2023, 6, 1) # Still Year 1
        purchase_date = date(2023, 1, 1)
        
        prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Usufruct Prop",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="USUFRUCT",
            purchase_date=purchase_date,
            purchase_price=None,
            monthly_rent=None,
            acq_fee_percentage=Decimal("0.00"),
            appreciation_rate_percentage=Decimal("10.00"),
            vacancy_rate_percentage=Decimal("10.00"),
            size=Decimal("100.00")
        )

        UsufructDetails.objects.create(
            property=prop,
            insurance_cost=Decimal("1000.00"),
            prep_cost=Decimal("50000.00"),
            outflow_monthly_rent=Decimal("2000.00"),
            annual_ops_cost=Decimal("2000.00"),
            inflow_monthly_rent=Decimal("5000.00"),
        )
        
        metrics = PropertySelector.calculate_metrics(prop, reference_date)
        
        # In Year 1, annual_rent should be 0
        self.assertEqual(metrics['metrics']['annual_rent'], Decimal("0.00"))
        # Effective rent should be 0
        self.assertEqual(metrics['metrics']['effective_rent'], Decimal("0.00"))
        # NOI in Year 1 = 0 - (2000 * 12) - 2000 - 1000 = -27000
        self.assertEqual(metrics['metrics']['noi'], Decimal("-27000.00"))
        
        # Test Year 2
        reference_date_y2 = date(2024, 1, 1)
        metrics_y2 = PropertySelector.calculate_metrics(prop, reference_date_y2)
        # In Year 2, annual_rent should be 5000 * 12 = 60000 (no growth in this test setup for simplicity)
        self.assertEqual(metrics_y2['metrics']['annual_rent'], Decimal("60000.00"))
        # NOI in Year 2 = 54000 (effective) - 24000 (outflow rent) - 2000 (ops) = 28000
        # (Insurance is excluded in Year 2+)
        self.assertEqual(metrics_y2['metrics']['noi'], Decimal("28000.00"))

    def test_portfolio_aggregation_excludes_usufruct(self):
        """Verify usufruct is excluded from total market value but included in rent in Year 2."""
        purchase_date = date(2023, 1, 1)
        reference_date = date(2024, 1, 1) # Year 2 to see rent
        
        # 1. Normal property
        Property.objects.create(
            portfolio=self.portfolio,
            name="Normal Prop",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="HELD",
            purchase_date=purchase_date,
            purchase_price=Decimal("1000000.00"),
            monthly_rent=Decimal("5000.00"),
            acq_fee_percentage=Decimal("0.00"),
            appreciation_rate_percentage=Decimal("0.00"),
            vacancy_rate_percentage=Decimal("0.00"),
            size=100
        )
        
        # 2. Usufruct property
        u_prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Usufruct Prop",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="USUFRUCT",
            purchase_date=purchase_date,
            purchase_price=None,
            monthly_rent=None,
            acq_fee_percentage=Decimal("0.00"),
            appreciation_rate_percentage=Decimal("0.00"),
            vacancy_rate_percentage=Decimal("0.00"),
            size=100
        )
        UsufructDetails.objects.create(
            property=u_prop,
            inflow_monthly_rent=Decimal("5000.00"),
            prep_cost=Decimal("100000.00")
        )
        
        data = PortfolioDashboardSelector.get_dashboard_data(self.portfolio, reference_date=reference_date)
        
        # Total Market Value should be 1M (only Normal Prop)
        self.assertEqual(data['metrics']['portfolio_market_value'], Decimal("1000000.00"))
        # Total Invested Capital should be 1.1M (1M normal + 100k prep cost)
        self.assertEqual(data['metrics']['total_invested_capital'], Decimal("1100000.00"))
        # Total Annual Rent should be 120k (both in Year 2)
        self.assertEqual(data['metrics']['total_annual_rent'], Decimal("120000.00"))

    def test_usufruct_appreciation(self):
        """Verify metrics for a usufruct property WITH appreciation in Year 3."""
        # Purchase date 2 years before reference date
        reference_date = date(2025, 1, 1) # Year 3
        purchase_date = date(2023, 1, 1)
        
        prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Appreciating Usufruct",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="USUFRUCT",
            purchase_date=purchase_date,
            acq_fee_percentage=Decimal("0.00"),
            appreciation_rate_percentage=Decimal("0.00"),
            vacancy_rate_percentage=Decimal("0.00"),
            size=Decimal("100.00")
        )

        UsufructDetails.objects.create(
            property=prop,
            insurance_cost=Decimal("1000.00"),
            prep_cost=Decimal("50000.00"),
            outflow_monthly_rent=Decimal("2000.00"),
            annual_ops_cost=Decimal("2000.00"),
            inflow_monthly_rent=Decimal("5000.00"),
            inflow_rent_appreciation_percentage=Decimal("10.00"),
            outflow_rent_appreciation_percentage=Decimal("5.00"),
        )
        
        # Year 1 check
        metrics_y1 = PropertySelector.calculate_metrics(prop, purchase_date)
        self.assertEqual(metrics_y1['metrics']['annual_rent'], Decimal("0.00"))
        
        # Year 3 check
        metrics = PropertySelector.calculate_metrics(prop, reference_date)
        
        # Years held should be approx 2.0 (731 days / 365.25 = 2.00137)
        # 10% appreciation over 2.00137 years for inflow: 5000 * (1.1)^2.00137 * 12 = 72609.47
        self.assertAlmostEqual(metrics['metrics']['annual_rent'], Decimal("72609.47"), places=2)
        
        # 5% appreciation over 2.00137 years for outflow: 2000 * (1.05)^2.00137 * 12 = 26461.77
        # NOI in Year 3 = 72609.47 - 26461.77 - 2000 = 44147.70
        # (Insurance is excluded in Year 3)
        self.assertAlmostEqual(metrics['metrics']['noi'], Decimal("44147.70"), places=2)
