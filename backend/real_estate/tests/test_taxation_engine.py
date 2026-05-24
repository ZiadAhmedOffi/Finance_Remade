from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from ..models import (
    RealEstatePortfolio, Jurisdiction, TaxRule, Property, UsufructDetails
)
from ..services.taxation_service import TaxationService

User = get_user_model()

class TaxationEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.jurisdiction = Jurisdiction.objects.create(name="Dubai", currency="AED")
        self.portfolio = RealEstatePortfolio.objects.create(
            name="Test Portfolio",
            jurisdiction=self.jurisdiction,
            created_by=self.user
        )
        
        # Acquisition Tax Rule
        self.acq_rule = TaxRule.objects.create(
            jurisdiction=self.jurisdiction,
            name="DLD Fee",
            event_type="ACQUISITION",
            trigger="CONTRACT_SIGNING",
            tax_base="MARKET_VALUE",
            rate=Decimal('0.04') # 4%
        )
        
        # Ownership Tax Rule
        self.own_rule = TaxRule.objects.create(
            jurisdiction=self.jurisdiction,
            name="Property Tax",
            event_type="OWNERSHIP",
            trigger="ANNUAL",
            tax_base="ASSESSED_VALUE",
            rate=Decimal('0.01'), # 1%
            valuation_ratio=Decimal('0.80'), # 80% of Market Value
            revaluation_freq=1
        )
        
        # Income Tax Rule
        self.inc_rule = TaxRule.objects.create(
            jurisdiction=self.jurisdiction,
            name="Income Tax",
            event_type="INCOME",
            trigger="ANNUAL",
            tax_base="NET_INCOME",
            rate=Decimal('0.10') # 10%
        )

        self.property = Property.objects.create(
            portfolio=self.portfolio,
            name="Villa A",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="HELD",
            purchase_date="2024-01-01",
            purchase_price=Decimal('1000000.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00')
        )

    def test_acquisition_tax_triggered(self):
        context = {
            'market_value': Decimal('1000000.00'),
            'property_events': ['CONTRACT_SIGNING']
        }
        tax = TaxationService.calculate_property_tax_for_year(self.property, 0, context)
        # 4% of 1M = 40,000 (Acq) + 1% of 800,000 (Own) = 8,000. Total = 48,000
        # Wait, Income Tax base is NET_INCOME, which is 0 in context.
        self.assertEqual(tax, Decimal('48000.00'))

    def test_ownership_tax_recurring(self):
        context = {
            'market_value': Decimal('1100000.00'), # 10% appreciation
            'property_events': [] # ANNUAL is added automatically
        }
        tax = TaxationService.calculate_property_tax_for_year(self.property, 1, context)
        # 1% of (1.1M * 0.8) = 8,800
        self.assertEqual(tax, Decimal('8800.00'))

    def test_income_tax_and_lcf_logic(self):
        # Year 0: Negative income (Loss)
        taxable_income_y0 = Decimal('-20000.00')
        lcf_pool_y0 = Decimal('0.00')
        adjusted_inc, new_pool = TaxationService.apply_loss_carry_forward(taxable_income_y0, lcf_pool_y0)
        
        self.assertEqual(adjusted_inc, Decimal('0.00'))
        self.assertEqual(new_pool, Decimal('20000.00'))
        
        # Year 1: Positive income, utilize LCF
        taxable_income_y1 = Decimal('50000.00')
        adjusted_inc, final_pool = TaxationService.apply_loss_carry_forward(taxable_income_y1, new_pool)
        
        self.assertEqual(adjusted_inc, Decimal('30000.00')) # 50k - 20k
        self.assertEqual(final_pool, Decimal('0.00'))

    def test_usufruct_allocation(self):
        # Set property as Usufruct and Investor as Holder
        self.property.status = "USUFRUCT"
        self.property.save()
        UsufructDetails.objects.create(
            property=self.property,
            investor_role="USUFRUCT_HOLDER"
        )
        
        # Create a rule specifically for Bare Owner
        TaxRule.objects.create(
            jurisdiction=self.jurisdiction,
            name="Bare Owner Tax",
            event_type="OWNERSHIP",
            trigger="ANNUAL",
            tax_base="MARKET_VALUE",
            rate=Decimal('0.05'), # 5%
            responsible_party="BARE_OWNER"
        )
        
        context = {
            'market_value': Decimal('1000000.00'),
            'property_events': []
        }
        
        tax = TaxationService.calculate_property_tax_for_year(self.property, 1, context)
        # Should NOT include the 5% Bare Owner tax.
        # Should still include the 1% Property Tax (responsible_party="BOTH")
        # Total = 8,000
        self.assertEqual(tax, Decimal('8000.00'))

    def test_disposal_tax_triggered(self):
        # CGT Rule
        TaxRule.objects.create(
            jurisdiction=self.jurisdiction,
            name="CGT",
            event_type="DISPOSAL",
            trigger="DISPOSAL",
            tax_base="MARKET_VALUE", # Simplified CGT for test
            rate=Decimal('0.20') # 20%
        )
        
        context = {
            'market_value': Decimal('1500000.00'),
            'is_disposal_year': True
        }
        
        tax = TaxationService.calculate_property_tax_for_year(self.property, 5, context)
        # CGT: 20% of 1.5M = 300,000
        # Property Tax: 1% of (1.5M * 0.8) = 12,000
        # Total = 312,000
        self.assertEqual(tax, Decimal('312000.00'))
