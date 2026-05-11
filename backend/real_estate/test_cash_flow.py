from django.test import TestCase
from decimal import Decimal
from datetime import date
from django.contrib.auth import get_user_model
from real_estate.models import RealEstatePortfolio, RealEstateAssumptions, Property, FinancingEntry
from real_estate.selectors.cash_flow_selectors import CashFlowSelectors

User = get_user_model()

class CashFlowModelTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@example.com", 
            password="password123",
            is_active=True,
            status="ACTIVE"
        )
        self.portfolio = RealEstatePortfolio.objects.create(
            name="CF Test Portfolio",
            created_by=self.admin_user
        )
        self.assumptions = RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date=date(2024, 1, 1),
            forecast_horizon=5,
            default_rental_growth_rate=Decimal('5.00'), # 5% growth
            maintenance_percentage_of_value=Decimal('1.00'),
            property_mgmt_fee_percentage=Decimal('2.00'),
            selling_fee_percentage=Decimal('2.00')
        )
        # Property purchased at inception
        self.prop = Property.objects.create(
            portfolio=self.portfolio,
            name="CF Test Property",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="MORTGAGED",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('1000000.00'),
            monthly_rent=Decimal('10000.00'), # 120,000 annual
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('10.00'), # 10% appreciation
            vacancy_rate_percentage=Decimal('0.00')
        )
        # Financing: 700k loan, 5% interest, 10yr tenor (but forecast is 5yr)
        self.financing = FinancingEntry.objects.create(
            property=self.prop,
            loan_amount=Decimal('700000.00'),
            base_interest_rate=Decimal('5.00'),
            tenor=10,
            payments_per_year=1, # Annual payments for easier manual calculation in test
            loan_start_date=date(2024, 1, 1)
        )

    def test_cash_flow_calculation_year_1(self):
        # Year 1 (2024):
        # Rent: 120,000
        # Mgmt Fee: 120,000 * 0.02 = 2,400
        # Value: 1,000,000
        # Maint Fee: 1,000,000 * 0.01 = 10,000
        # OpEx: 0
        # NOI: 120,000 - 2,400 - 10,000 = 107,600
        # Debt Service: (using calculate_pmt formula)
        # PMT = (0.05 * 700000) / (1 - (1.05)^-10) = 35000 / (1 - 0.6139) = 35000 / 0.3861 ≈ 90,652.12
        
        data = CashFlowSelectors.get_portfolio_cash_flow(self.portfolio, start_year=2024, end_year=2024)
        cf_year_1 = data['properties'][str(self.prop.id)]['annual_cf'][2024]
        
        expected_noi = Decimal('107600.00')
        # We can calculate PMT exactly
        rate = Decimal('0.05')
        pv = Decimal('700000.00')
        n = 10
        pmt = (rate * pv) / (1 - (1 + rate)**-n)
        expected_debt_service = pmt.quantize(Decimal('0.01'))
        
        expected_cf = (expected_noi - expected_debt_service).quantize(Decimal('0.01'))
        self.assertEqual(cf_year_1, expected_cf)

    def test_cash_flow_growth_year_2(self):
        # Year 2 (2025):
        # Rent: 120,000 * 1.05 = 126,000
        # Mgmt Fee: 126,000 * 0.02 = 2,520
        # Value: 1,000,000 * 1.10 = 1,100,000
        # Maint Fee: 1,100,000 * 0.01 = 11,000
        # NOI: 126,000 - 2,520 - 11,000 = 112,480
        # Debt Service: Same as Year 1 (90,652.12)
        
        data = CashFlowSelectors.get_portfolio_cash_flow(self.portfolio, start_year=2025, end_year=2025)
        cf_year_2 = data['properties'][str(self.prop.id)]['annual_cf'][2025]
        
        expected_noi = Decimal('112480.00')
        rate = Decimal('0.05')
        pv = Decimal('700000.00')
        n = 10
        pmt = (rate * pv) / (1 - (1 + rate)**-n)
        expected_debt_service = pmt.quantize(Decimal('0.01'))
        
        expected_cf = (expected_noi - expected_debt_service).quantize(Decimal('0.01'))
        self.assertEqual(cf_year_2, expected_cf)

    def test_cumulative_cash_flow(self):
        data = CashFlowSelectors.get_portfolio_cash_flow(self.portfolio, start_year=2024, end_year=2025)
        
        cf_1 = data['portfolio_totals'][2024]
        cf_2 = data['portfolio_totals'][2025]
        
        expected_cum_2 = cf_1 + cf_2
        self.assertEqual(data['cumulative_cf'][2025], expected_cum_2.quantize(Decimal('0.01')))
