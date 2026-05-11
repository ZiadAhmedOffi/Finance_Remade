from django.test import TestCase
from decimal import Decimal
from datetime import date
from django.contrib.auth import get_user_model
from real_estate.models import RealEstatePortfolio, RealEstateAssumptions, Property, OffPlanDetails
from real_estate.selectors.property_selectors import PropertySelector
from real_estate.selectors.cash_flow_selectors import CashFlowSelectors

User = get_user_model()

class NewRequirementsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.portfolio = RealEstatePortfolio.objects.create(name="Test Portfolio", created_by=self.user)
        self.assumptions = RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date=date(2024, 1, 1),
            forecast_horizon=10,
            default_vacancy_rate=Decimal('10.00'),
            default_rental_growth_rate=Decimal('0.00'),
            property_mgmt_fee_percentage=Decimal('2.00'),
            maintenance_percentage_of_value=Decimal('1.00'),
            selling_fee_percentage=Decimal('2.00')
        )

    def test_property_metrics_with_vacancy_and_gross_yield(self):
        # Purchase Price: 1,000,000
        # Monthly Rent: 10,000 -> Annual Rent: 120,000
        # Vacancy: 10% -> Effective Rent: 108,000
        # Gross Yield = 108,000 / 1,000,000 = 10.8%
        prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Test Prop",
            city="Dubai",
            country="UAE",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('1000000.00'),
            monthly_rent=Decimal('10000.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('10.00'),
            status="HELD"
        )
        
        metrics = PropertySelector.calculate_metrics(prop, date(2024, 1, 1))['metrics']
        self.assertEqual(metrics['effective_rent'], Decimal('108000.00'))
        self.assertEqual(metrics['gross_yield'], Decimal('10.80'))

    def test_purchase_year_pro_rating_and_negative_cf(self):
        # Purchase Date: 2024-07-01 (6 months owned: July to Dec)
        # Purchase Price: 1,000,000
        # Monthly Rent: 10,000
        # Vacancy: 0%
        # Year 2024 CF = -1,000,000 (purchase) + 60,000 (rent) - opex
        # market_value = 1,000,000
        # maint_fee = 10,000
        # mgmt_fee = 60,000 * 0.02 = 1,200
        # expected_cf = -1,000,000 + 60,000 - 10,000 - 1,200 = -951,200
        prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Pro-rated Prop",
            city="Dubai",
            country="UAE",
            purchase_date=date(2024, 7, 1),
            purchase_price=Decimal('1000000.00'),
            monthly_rent=Decimal('10000.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00'),
            status="HELD"
        )
        
        data = CashFlowSelectors.get_portfolio_cash_flow(self.portfolio, start_year=2024, end_year=2024)
        cf_2024 = Decimal(data['properties'][str(prop.id)]['annual_cf'][2024])
        self.assertEqual(cf_2024, Decimal('-951200.00'))

    def test_off_plan_rent_appreciation(self):
        # Completion in 2026. Jump 20%. Rent growth 5%.
        # Year 2026 (t=2 from purchase 2024):
        # Base Rent: 120,000
        # Appreciated: 120,000 * (1.05)^2 * 1.20 = 158,760
        # Pro-rated for 2026-07-01 (6 months): 79,380
        # Expenses will grow too, but we want to see rent increase in 2027.
        # Year 2027 (t=3):
        # Appreciated: 120,000 * (1.05)^3 * 1.20 = 166,698
        # months = 12
        # NOI will be higher in 2027 than 2026 (pro-rated).
        prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Off Plan Appr",
            city="Dubai",
            country="UAE",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('1000000.00'),
            monthly_rent=Decimal('10000.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00'),
            status="OFF_PLAN"
        )
        OffPlanDetails.objects.create(
            property=prop,
            construction_start_date=date(2024, 1, 1),
            expected_completion_date=date(2026, 7, 1),
            appreciation_rate_at_completion=Decimal('20.00'),
            sale_at_completion=False
        )
        self.assumptions.default_rental_growth_rate = Decimal('5.00')
        self.assumptions.save()
        
        data = CashFlowSelectors.get_portfolio_cash_flow(self.portfolio, start_year=2026, end_year=2027)
        cf_2026 = Decimal(data['properties'][str(prop.id)]['annual_cf'][2026])
        cf_2027 = Decimal(data['properties'][str(prop.id)]['annual_cf'][2027])
        
        # Verify it increases
        self.assertGreater(cf_2027, cf_2026)
        # 2027 should have full year rent (approx 166k - expenses)
        # 2026 should have half year rent (approx 79k - expenses)
        self.assertGreater(cf_2027, Decimal('100000')) 

