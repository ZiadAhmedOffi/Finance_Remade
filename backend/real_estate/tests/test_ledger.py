from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date
from ..models import RealEstatePortfolio, Property, LedgerYear, LedgerAccount, LedgerTransaction, LedgerEntry, RealEstateInvestorAction
from ..services.ledger_service import LedgerYearService, LedgerTransactionService, LedgerAccountService
from ..services.ledger_sync_service import LedgerSyncService
from ..selectors.ledger_selectors import LedgerSelectors

User = get_user_model()

class LedgerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.portfolio = RealEstatePortfolio.objects.create(
            name="Test Portfolio",
            created_by=self.user
        )
        from ..models import RealEstateAssumptions
        self.assumptions = RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date=date(2023, 1, 1),
            forecast_horizon=10
        )

    def test_ledger_initialization(self):
        """Test that ledger year and system accounts are created correctly."""
        ledger_year = LedgerYearService.get_or_create_ledger_year(self.portfolio, 2024)
        self.assertEqual(ledger_year.year, 2024)
        
        accounts = LedgerAccount.objects.filter(portfolio=self.portfolio)
        self.assertTrue(accounts.filter(name="Cash", is_system_account=True).exists())
        self.assertTrue(accounts.filter(name="Property Assets", is_system_account=True).exists())

    def test_balanced_transaction(self):
        """Test that only balanced transactions can be created."""
        ledger_year = LedgerYearService.get_or_create_ledger_year(self.portfolio, 2024)
        cash_acc = LedgerAccount.objects.get(portfolio=self.portfolio, name="Cash")
        equity_acc = LedgerAccount.objects.get(portfolio=self.portfolio, name="Paid-in Capital")
        
        # Balanced: 100 Debit Cash, 100 Credit Equity
        entries = [
            {"account": cash_acc, "amount": Decimal('100.00'), "entry_type": "DEBIT"},
            {"account": equity_acc, "amount": Decimal('100.00'), "entry_type": "CREDIT"}
        ]
        
        tx = LedgerTransactionService.create_transaction(
            portfolio=self.portfolio,
            ledger_year=ledger_year,
            description="Test Transaction",
            date=date(2024, 1, 1),
            entries=entries
        )
        self.assertIsNotNone(tx)
        self.assertEqual(tx.entries.count(), 2)

        # Unbalanced: 100 Debit Cash, 50 Credit Equity
        bad_entries = [
            {"account": cash_acc, "amount": Decimal('100.00'), "entry_type": "DEBIT"},
            {"account": equity_acc, "amount": Decimal('50.00'), "entry_type": "CREDIT"}
        ]
        
        with self.assertRaises(ValueError):
            LedgerTransactionService.create_transaction(
                portfolio=self.portfolio,
                ledger_year=ledger_year,
                description="Bad Transaction",
                date=date(2024, 1, 1),
                entries=bad_entries
            )

    def test_historical_sync(self):
        """Test the cumulative opening balance calculation."""
        # 1. Add some historical data in 2023
        # Primary Investment
        RealEstateInvestorAction.objects.create(
            investor=self.user,
            portfolio=self.portfolio,
            type="PRIMARY_INVESTMENT",
            year=2023,
            amount=Decimal('1000000.00'),
            units=1000000.00
        )
        self.portfolio.total_units = Decimal('1000000.00')
        self.portfolio.save()
        
        # Property Purchase
        prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Old Prop",
            city="City",
            country="Country",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            purchase_date=date(2023, 6, 1),
            purchase_price=Decimal('800000.00'),
            monthly_rent=Decimal('0.00'),
            other_operational_expenses=Decimal('0.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00')
        )
        
        # 2. Sync historical data for 2024
        LedgerSyncService.sync_historical_data(self.portfolio, 2024)
        
        ledger_year = LedgerYear.objects.get(portfolio=self.portfolio, year=2024)
        opening_tx = LedgerTransaction.objects.get(ledger_year=ledger_year, source_type="OPENING_BALANCE")
        
        # Expected:
        # Cash: 1,000,000 (Investment) - 800,000 (Purchase) - 8,000 (Tax @ 1%) = 192,000 (DEBIT)
        # Property Assets: 800,000 (DEBIT)
        # Paid-in Capital: 1,000,000 (CREDIT)
        # Retained Earnings: 8,000 (DEBIT) - to balance the historical tax loss
        
        tb = LedgerSelectors.get_trial_balance(ledger_year)
        self.assertTrue(tb["is_balanced"])
        
        cash_entry = next(a for a in tb["accounts"] if a["account_name"] == "Cash")
        prop_entry = next(a for a in tb["accounts"] if a["account_name"] == "Property Assets")
        equity_entry = next(a for a in tb["accounts"] if a["account_name"] == "Paid-in Capital")
        
        self.assertEqual(cash_entry["net_balance"], Decimal('192000.00'))
        self.assertEqual(prop_entry["net_balance"], Decimal('800000.00'))
        self.assertEqual(equity_entry["net_balance"], Decimal('1000000.00'))

    def test_property_sale_sync(self):
        """Test that selling a property creates correct ledger entries."""
        ledger_year = LedgerYearService.get_or_create_ledger_year(self.portfolio, 2024)
        
        # 1. Create Property
        prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Sale Prop",
            city="City",
            country="Country",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('500000.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00')
        )
        LedgerSyncService.sync_property_acquisition(prop)
        
        # 2. Sell Property
        from ..models import PropertySale
        sale = PropertySale.objects.create(
            property=prop,
            sale_date=date(2024, 6, 1),
            selling_price=Decimal('600000.00'),
            selling_fee_percentage=Decimal('5.00') # 30,000 fee
        )
        # Net proceeds: 600,000 - 30,000 = 570,000
        # Realized gain: 600,000 - 500,000 - 30,000 = 70,000
        
        LedgerSyncService.sync_property_sale(sale)
        
        tb = LedgerSelectors.get_trial_balance(ledger_year)
        
        re_entry = next(a for a in tb["accounts"] if a["account_name"] == "Retained Earnings")
        prop_entry = next(a for a in tb["accounts"] if a["account_name"] == "Property Assets")
        cash_entry = next(a for a in tb["accounts"] if a["account_name"] == "Cash")
        
        # Property Assets should be zero (500k debit from acq, 500k credit from sale)
        self.assertEqual(prop_entry["net_balance"], Decimal('0.00'))
        # Retained Earnings should be 70k credit
        self.assertEqual(re_entry["net_balance"], Decimal('70000.00'))
        # Cash should be +70k net (570k inflow - 500k outflow from acq)
        self.assertEqual(cash_entry["net_balance"], Decimal('70000.00'))

    def test_financing_sync(self):
        """Test that taking a loan creates correct ledger entries."""
        ledger_year = LedgerYearService.get_or_create_ledger_year(self.portfolio, 2024)
        prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Loan Prop",
            city="City",
            country="Country",
            property_type="RESIDENTIAL",
            financing_type="MORTGAGED",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('500000.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00')
        )
        
        from ..models import FinancingEntry
        loan = FinancingEntry.objects.create(
            property=prop,
            loan_amount=Decimal('300000.00'),
            base_interest_rate=Decimal('5.00'),
            tenor=20,
            payments_per_year=12,
            loan_start_date=date(2024, 1, 1)
        )
        
        LedgerSyncService.sync_financing_entry(loan)
        
        tb = LedgerSelectors.get_trial_balance(ledger_year)
        mortgage_entry = next(a for a in tb["accounts"] if a["account_name"] == "Mortgage Payable")
        cash_entry = next(a for a in tb["accounts"] if a["account_name"] == "Cash")
        
        self.assertEqual(mortgage_entry["net_balance"], Decimal('300000.00'))
        self.assertEqual(cash_entry["net_balance"], Decimal('300000.00'))

    def test_year_closing(self):
        """Test that closing a year rolls revenue into retained earnings and carries forward balances."""
        ledger_year = LedgerYearService.get_or_create_ledger_year(self.portfolio, 2024)
        cash_acc = LedgerAccount.objects.get(portfolio=self.portfolio, name="Cash")
        income_acc = LedgerAccount.objects.get(portfolio=self.portfolio, name="Rental Income")
        expense_acc = LedgerAccount.objects.get(portfolio=self.portfolio, name="Operational Expenses")
        re_acc = LedgerAccount.objects.get(portfolio=self.portfolio, name="Retained Earnings")
        
        # 1. Add some income and expense
        # Income: 1000 (Debit Cash, Credit Income)
        LedgerTransactionService.create_transaction(
            portfolio=self.portfolio, ledger_year=ledger_year, description="Rent", date=date(2024, 6, 1),
            entries=[
                {"account": cash_acc, "amount": Decimal('1000.00'), "entry_type": "DEBIT"},
                {"account": income_acc, "amount": Decimal('1000.00'), "entry_type": "CREDIT"}
            ]
        )
        # Expense: 400 (Debit Expense, Credit Cash)
        LedgerTransactionService.create_transaction(
            portfolio=self.portfolio, ledger_year=ledger_year, description="Repair", date=date(2024, 6, 2),
            entries=[
                {"account": expense_acc, "amount": Decimal('400.00'), "entry_type": "DEBIT"},
                {"account": cash_acc, "amount": Decimal('400.00'), "entry_type": "CREDIT"}
            ]
        )
        
        # 2. Close Year
        LedgerYearService.close_year(ledger_year, self.user)
        
        # Verify 2024 state
        self.assertTrue(ledger_year.is_closed)
        tb_2024 = LedgerSelectors.get_trial_balance(ledger_year)
        # Revenue and Expense should be 0 in the Trial Balance because of the closing transaction
        income_tb = next(a for a in tb_2024["accounts"] if a["account_name"] == "Rental Income")
        expense_tb = next(a for a in tb_2024["accounts"] if a["account_name"] == "Operational Expenses")
        re_tb = next(a for a in tb_2024["accounts"] if a["account_name"] == "Retained Earnings")
        
        self.assertEqual(income_tb["net_balance"], Decimal('0.00'))
        self.assertEqual(expense_tb["net_balance"], Decimal('0.00'))
        # Net Income = 1000 - 400 = 600. Retained Earnings should have +600 credit.
        self.assertEqual(re_tb["net_balance"], Decimal('600.00'))

        # 3. Verify 2025 Opening Balance
        ledger_year_2025 = LedgerYear.objects.get(portfolio=self.portfolio, year=2025)
        tb_2025 = LedgerSelectors.get_trial_balance(ledger_year_2025)
        
        cash_2025 = next(a for a in tb_2025["accounts"] if a["account_name"] == "Cash")
        re_2025 = next(a for a in tb_2025["accounts"] if a["account_name"] == "Retained Earnings")
        
        # Cash: 1000 - 400 = 600
        self.assertEqual(cash_2025["net_balance"], Decimal('600.00'))
        self.assertEqual(re_2025["net_balance"], Decimal('600.00'))
