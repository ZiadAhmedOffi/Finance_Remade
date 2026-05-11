from django.test import TestCase
from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from real_estate.models import RealEstatePortfolio, RealEstateAssumptions, Property, FinancingEntry, PropertySale
from real_estate.services.property_sale_service import PropertySaleService
from real_estate.selectors.property_sale_selectors import PropertySaleSelector

User = get_user_model()

class PropertySalesTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@example.com", 
            password="password123",
            is_active=True,
            status="ACTIVE"
        )
        self.portfolio = RealEstatePortfolio.objects.create(
            name="Test Portfolio",
            created_by=self.admin_user
        )
        self.assumptions = RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date=date(2024, 1, 1),
            selling_fee_percentage=Decimal('2.00')
        )
        self.prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Test Property",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="MORTGAGED",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('1000000.00'),
            monthly_rent=Decimal('5000.00'),
            acq_fee_percentage=Decimal('1.00'),
            appreciation_rate_percentage=Decimal('3.00'),
            vacancy_rate_percentage=Decimal('5.00')
        )
        self.financing = FinancingEntry.objects.create(
            property=self.prop,
            loan_amount=Decimal('700000.00'),
            base_interest_rate=Decimal('5.00'),
            tenor=10,
            payments_per_year=12,
            loan_start_date=date(2024, 1, 1)
        )

    def test_create_property_sale(self):
        sale_data = {
            'sale_date': date(2025, 1, 1),
            'selling_price': Decimal('1200000.00'),
            'selling_fee_percentage': Decimal('2.00')
        }
        sale = PropertySaleService.create_property_sale(property_obj=self.prop, data=sale_data)
        
        self.assertEqual(PropertySale.objects.count(), 1)
        self.assertEqual(sale.property, self.prop)
        self.assertEqual(sale.selling_price, Decimal('1200000.00'))

    def test_duplicate_sale_prevented(self):
        sale_data = {
            'sale_date': date(2025, 1, 1),
            'selling_price': Decimal('1200000.00'),
            'selling_fee_percentage': Decimal('2.00')
        }
        PropertySaleService.create_property_sale(property_obj=self.prop, data=sale_data)
        
        with self.assertRaises(ValidationError):
            PropertySaleService.create_property_sale(property_obj=self.prop, data=sale_data)

    def test_sale_metrics_calculation(self):
        # Sale exactly 1 year after purchase
        sale_data = {
            'sale_date': date(2025, 1, 1),
            'selling_price': Decimal('1200000.00'),
            'selling_fee_percentage': Decimal('2.00')
        }
        sale = PropertySaleService.create_property_sale(property_obj=self.prop, data=sale_data)
        
        metrics_data = PropertySaleSelector.calculate_sale_metrics(sale)
        metrics = metrics_data['metrics']
        
        # selling_costs = 1,200,000 * 0.02 = 24,000
        self.assertEqual(metrics['selling_costs'], Decimal('24000.00'))
        
        # realized_gain = 1,200,000 - 1,000,000 - 24,000 = 176,000
        self.assertEqual(metrics['realized_gain'], Decimal('176000.00'))
        
        # roi = 1,200,000 / 1,000,000 = 1.2
        self.assertEqual(metrics['roi'], Decimal('1.2000'))
        
        # loan_payoff should be the ending balance after 12 payments
        self.assertLess(metrics['loan_payoff'], Decimal('700000.00'))
        self.assertGreater(metrics['loan_payoff'], Decimal('600000.00'))

    def test_update_sale(self):
        sale_data = {
            'sale_date': date(2025, 1, 1),
            'selling_price': Decimal('1200000.00'),
            'selling_fee_percentage': Decimal('2.00')
        }
        sale = PropertySaleService.create_property_sale(property_obj=self.prop, data=sale_data)
        
        updated_data = {'selling_price': Decimal('1300000.00')}
        PropertySaleService.update_property_sale(sale=sale, data=updated_data)
        
        sale.refresh_from_db()
        self.assertEqual(sale.selling_price, Decimal('1300000.00'))
