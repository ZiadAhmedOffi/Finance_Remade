from django.test import TestCase
from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from real_estate.models import (
    RealEstatePortfolio, RealEstateAssumptions, Property, 
    FinancingEntry, PropertySale, InstallmentEntry, UsufructDetails,
    LedgerAccount, LedgerYear, LedgerTransaction
)
from real_estate.services.property_sale_service import PropertySaleService
from real_estate.selectors.property_sale_selectors import PropertySaleSelector

User = get_user_model()

class RobustSalesTestCase(TestCase):
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
        
        # Setup Ledger Accounts (needed for sync_property_sale)
        accounts = [
            ("Cash", "ASSET"),
            ("Property Assets", "ASSET"),
            ("Mortgage Payable", "LIABILITY"),
            ("Installment Payable", "LIABILITY"),
            ("Paid-in Capital", "EQUITY"),
            ("Retained Earnings", "EQUITY"),
        ]
        for name, atype in accounts:
            LedgerAccount.objects.create(portfolio=self.portfolio, name=name, type=atype)

        self.prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Held Property",
            status="HELD",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('1000000.00'),
            acq_fee_percentage=Decimal('1.00'),
            appreciation_rate_percentage=Decimal('3.00'),
            vacancy_rate_percentage=Decimal('5.00')
        )

    def test_block_off_plan_sale(self):
        off_plan_prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Off-Plan Property",
            status="OFF_PLAN",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('1000000.00'),
            acq_fee_percentage=Decimal('1.00'),
            appreciation_rate_percentage=Decimal('3.00'),
            vacancy_rate_percentage=Decimal('5.00')
        )
        sale_data = {
            'sale_date': date(2025, 1, 1),
            'selling_price': Decimal('1200000.00')
        }
        with self.assertRaisesMessage(ValidationError, "is Off-Plan and cannot be sold"):
            PropertySaleService.create_property_sale(property_obj=off_plan_prop, data=sale_data)

    def test_block_usufruct_sale(self):
        usufruct_prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Usufruct Property",
            status="USUFRUCT",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('0.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('5.00')
        )
        UsufructDetails.objects.create(
            property=usufruct_prop,
            prep_cost=Decimal('50000.00')
        )
        sale_data = {
            'sale_date': date(2025, 1, 1),
            'selling_price': Decimal('100000.00')
        }
        with self.assertRaisesMessage(ValidationError, "is a Usufruct property and cannot be sold"):
            PropertySaleService.create_property_sale(property_obj=usufruct_prop, data=sale_data)

    def test_block_sale_before_purchase(self):
        sale_data = {
            'sale_date': date(2023, 12, 31),
            'selling_price': Decimal('1200000.00')
        }
        with self.assertRaisesMessage(ValidationError, "cannot be before purchase date"):
            PropertySaleService.create_property_sale(property_obj=self.prop, data=sale_data)

    def test_installment_payoff_calculation(self):
        inst_prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Installment Property",
            status="HELD",
            financing_type="PRIMARY_INSTALLMENTS",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('1000000.00'),
            acq_fee_percentage=Decimal('1.00'),
            appreciation_rate_percentage=Decimal('3.00'),
            vacancy_rate_percentage=Decimal('5.00')
        )
        InstallmentEntry.objects.create(
            property=inst_prop,
            down_payment=Decimal('200000.00'),
            tenor=10,
            payments_per_year=12,
            start_date=date(2024, 1, 1)
        )
        
        # Sale after 1 year (12 payments)
        sale_data = {
            'sale_date': date(2025, 1, 1),
            'selling_price': Decimal('1200000.00')
        }
        sale = PropertySaleService.create_property_sale(property_obj=inst_prop, data=sale_data)
        
        metrics = PropertySaleSelector.calculate_sale_metrics(sale)['metrics']
        
        # Initial balance = 800,000. 120 total periods.
        # Periodic payment = 800,000 / 120 = 6666.6666...
        # After 12 months, paid = 12 * 6666.6666... = 80,000
        # Payoff = 800,000 - 80,000 = 720,000
        self.assertAlmostEqual(metrics['installment_payoff'], Decimal('720000.00'), places=2)
        
        # Verify ledger entry for installment payoff
        tx = LedgerTransaction.objects.get(source_type="PROPERTY_SALE", source_id=sale.id)
        inst_payoff_entry = tx.entries.get(account__name="Installment Payable")
        self.assertEqual(inst_payoff_entry.entry_type, "DEBIT")
        self.assertAlmostEqual(inst_payoff_entry.amount, Decimal('720000.00'), places=2)

    def test_combined_payoff_ledger_sync(self):
        # Combined Mortgage + Installment (rare but testable)
        combined_prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Combined Prop",
            status="HELD",
            financing_type="MORTGAGED",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('1000000.00'),
            acq_fee_percentage=Decimal('1.00'),
            appreciation_rate_percentage=Decimal('3.00'),
            vacancy_rate_percentage=Decimal('5.00')
        )
        FinancingEntry.objects.create(
            property=combined_prop,
            loan_amount=Decimal('500000.00'),
            base_interest_rate=Decimal('5.00'),
            tenor=10,
            payments_per_year=12,
            loan_start_date=date(2024, 1, 1)
        )
        # Manually add an installment entry (even if financing_type is MORTGAGED)
        InstallmentEntry.objects.create(
            property=combined_prop,
            down_payment=Decimal('900000.00'), # Only 100k balance
            tenor=10,
            payments_per_year=12,
            start_date=date(2024, 1, 1)
        )
        
        sale_data = {
            'sale_date': date(2025, 1, 1),
            'selling_price': Decimal('1200000.00')
        }
        sale = PropertySaleService.create_property_sale(property_obj=combined_prop, data=sale_data)
        
        tx = LedgerTransaction.objects.get(source_type="PROPERTY_SALE", source_id=sale.id)
        
        # Verify both payoffs are present in the ledger transaction
        self.assertTrue(tx.entries.filter(account__name="Mortgage Payable", entry_type="DEBIT").exists())
        self.assertTrue(tx.entries.filter(account__name="Installment Payable", entry_type="DEBIT").exists())
        
        # Verify net proceeds debit to Cash
        cash_entry = tx.entries.get(account__name="Cash", entry_type="DEBIT")
        metrics = PropertySaleSelector.calculate_sale_metrics(sale)['metrics']
        self.assertAlmostEqual(cash_entry.amount, metrics['net_proceeds'], places=2)
