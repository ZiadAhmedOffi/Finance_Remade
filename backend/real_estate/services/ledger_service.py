from decimal import Decimal
from datetime import date
from django.db import transaction
from django.utils import timezone
from ..models import (
    RealEstatePortfolio,
    LedgerAccount,
    LedgerYear,
    LedgerTransaction,
    LedgerEntry
)

class LedgerAccountService:
    SYSTEM_ACCOUNTS = [
        ("Cash", "ASSET"),
        ("Property Assets", "ASSET"),
        ("Mortgage Payable", "LIABILITY"),
        ("Installment Payable", "LIABILITY"),
        ("Paid-in Capital", "EQUITY"),
        ("Retained Earnings", "EQUITY"),
        ("Rental Income", "REVENUE"),
        ("Operational Expenses", "EXPENSE"),
        ("Financing Expenses", "EXPENSE"),
    ]

    @staticmethod
    @transaction.atomic
    def initialize_system_accounts(portfolio: RealEstatePortfolio):
        """
        Creates the default set of system accounts for a portfolio.
        """
        for name, account_type in LedgerAccountService.SYSTEM_ACCOUNTS:
            LedgerAccount.objects.get_or_create(
                portfolio=portfolio,
                name=name,
                defaults={"type": account_type, "is_system_account": True}
            )

class LedgerTransactionService:
    @staticmethod
    @transaction.atomic
    def create_transaction(
        *,
        portfolio: RealEstatePortfolio,
        ledger_year: LedgerYear,
        description: str,
        date: timezone.datetime.date,
        entries: list,  # list of dicts: {"account": LedgerAccount, "amount": Decimal, "entry_type": "DEBIT"|"CREDIT"}
        source_type: str = None,
        source_id: str = None
    ) -> LedgerTransaction:
        """
        Creates a balanced ledger transaction.
        """
        if ledger_year.is_closed:
            raise ValueError(f"Cannot add transactions to a closed ledger year: {ledger_year.year}")

        if date.year != ledger_year.year:
             raise ValueError(f"Transaction date {date} does not match ledger year {ledger_year.year}")

        # Validate balance
        debit_sum = sum(e["amount"] for e in entries if e["entry_type"] == "DEBIT")
        credit_sum = sum(e["amount"] for e in entries if e["entry_type"] == "CREDIT")

        if abs(debit_sum - credit_sum) > Decimal('0.0001'):
            raise ValueError(f"Transaction is not balanced. Debits: {debit_sum}, Credits: {credit_sum}")

        transaction_obj = LedgerTransaction.objects.create(
            portfolio=portfolio,
            ledger_year=ledger_year,
            description=description,
            date=date,
            source_type=source_type,
            source_id=source_id
        )

        for entry in entries:
            LedgerEntry.objects.create(
                transaction=transaction_obj,
                account=entry["account"],
                amount=entry["amount"],
                entry_type=entry["entry_type"]
            )

        return transaction_obj

class LedgerYearService:
    @staticmethod
    @transaction.atomic
    def get_or_create_ledger_year(portfolio: RealEstatePortfolio, year: int) -> LedgerYear:
        """
        Ensures a LedgerYear exists and system accounts are initialized.
        """
        ledger_year, created = LedgerYear.objects.get_or_create(
            portfolio=portfolio,
            year=year
        )
        if created:
            LedgerAccountService.initialize_system_accounts(portfolio)
        return ledger_year

    @staticmethod
    @transaction.atomic
    def close_year(ledger_year: LedgerYear, user):
        """
        Finalizes a fiscal year and carries forward balances.
        """
        if ledger_year.is_closed:
            return ledger_year

        portfolio = ledger_year.portfolio
        from ..selectors.ledger_selectors import LedgerSelectors
        tb = LedgerSelectors.get_trial_balance(ledger_year)
        
        if not tb["is_balanced"]:
            raise ValueError("Cannot close an unbalanced ledger.")

        # 1. Close Revenue and Expense accounts into Retained Earnings
        # In a Trial Balance, Revenue/Expense net balances should be zeroed out.
        # But we don't actually need to create a "Closing Transaction" if we just 
        # use the net balance in the carry-forward.
        # However, for a formal T-balance, we should create a transaction on Dec 31st.
        
        re_account = LedgerAccount.objects.get(portfolio=portfolio, name="Retained Earnings")
        closing_entries = []
        
        for acc_data in tb["accounts"]:
            if acc_data["account_type"] in ["REVENUE", "EXPENSE"]:
                amount = acc_data["net_balance"]
                if amount == 0:
                    continue
                
                # If Revenue has 100 Credit balance, we Debit 100 to zero it.
                # If Expense has 100 Debit balance, we Credit 100 to zero it.
                account = LedgerAccount.objects.get(id=acc_data["account_id"])
                is_debit_balance = acc_data["account_type"] == "EXPENSE"
                
                closing_entries.append({
                    "account": account,
                    "amount": abs(amount),
                    "entry_type": "CREDIT" if is_debit_balance else "DEBIT"
                })
        
        if closing_entries:
            # The balancing entry for Retained Earnings
            debit_sum = sum(e["amount"] for e in closing_entries if e["entry_type"] == "DEBIT")
            credit_sum = sum(e["amount"] for e in closing_entries if e["entry_type"] == "CREDIT")
            
            diff = debit_sum - credit_sum
            if diff != 0:
                closing_entries.append({
                    "account": re_account,
                    "amount": abs(diff),
                    "entry_type": "CREDIT" if diff > 0 else "DEBIT"
                })

            LedgerTransactionService.create_transaction(
                portfolio=portfolio,
                ledger_year=ledger_year,
                description=f"Year-End Closing Transaction {ledger_year.year}",
                date=date(ledger_year.year, 12, 31),
                entries=closing_entries,
                source_type="YEAR_CLOSING"
            )

        # 2. Mark year as closed
        ledger_year.is_closed = True
        ledger_year.closed_at = timezone.now()
        ledger_year.closed_by = user
        ledger_year.save()

        # 3. Carry forward balances to next year
        next_year_num = ledger_year.year + 1
        next_ledger_year = LedgerYearService.get_or_create_ledger_year(portfolio, next_year_num)
        
        # Recalculate TB after closing (Revenue/Expenses will be 0)
        tb_closed = LedgerSelectors.get_trial_balance(ledger_year)
        opening_entries = []
        
        for acc_data in tb_closed["accounts"]:
            if acc_data["account_type"] in ["ASSET", "LIABILITY", "EQUITY"]:
                balance = acc_data["net_balance"]
                if balance == 0:
                    continue
                
                account = LedgerAccount.objects.get(id=acc_data["account_id"])
                
                # Asset: Positive balance means DEBIT
                # Liability/Equity: Positive balance means CREDIT
                is_normal_debit = acc_data["account_type"] == "ASSET"
                
                opening_entries.append({
                    "account": account,
                    "amount": abs(balance),
                    "entry_type": "DEBIT" if (is_normal_debit and balance > 0) or (not is_normal_debit and balance < 0) else "CREDIT"
                })

        if opening_entries:
            LedgerTransactionService.create_transaction(
                portfolio=portfolio,
                ledger_year=next_ledger_year,
                description=f"Opening Balance from {ledger_year.year}",
                date=date(next_year_num, 1, 1),
                entries=opening_entries,
                source_type="OPENING_BALANCE"
            )

        return ledger_year
