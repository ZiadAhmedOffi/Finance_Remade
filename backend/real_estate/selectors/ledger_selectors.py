from django.db.models import Sum, Q
from decimal import Decimal
from ..models import (
    LedgerYear,
    LedgerAccount,
    LedgerEntry,
    LedgerTransaction
)

class LedgerSelectors:
    @staticmethod
    def get_ledger_years(portfolio):
        """
        Returns all ledger years for a portfolio.
        """
        return LedgerYear.objects.filter(portfolio=portfolio).order_by("-year")

    @staticmethod
    def get_ledger_year_by_id(ledger_year_id):
        return LedgerYear.objects.get(id=ledger_year_id)

    @staticmethod
    def get_trial_balance(ledger_year: LedgerYear):
        """
        Calculates the trial balance for a specific fiscal year.
        Includes opening balances from carry-forward or historical sync.
        """
        portfolio = ledger_year.portfolio
        accounts = LedgerAccount.objects.filter(portfolio=portfolio)
        
        results = []
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')

        for account in accounts:
            # Aggregate all entries for this account in this ledger year
            metrics = LedgerEntry.objects.filter(
                transaction__ledger_year=ledger_year,
                account=account
            ).aggregate(
                debit=Sum('amount', filter=Q(entry_type="DEBIT")),
                credit=Sum('amount', filter=Q(entry_type="CREDIT"))
            )
            
            debit = metrics['debit'] or Decimal('0.00')
            credit = metrics['credit'] or Decimal('0.00')
            
            net_balance = Decimal('0.00')
            # Asset/Expense: Debit - Credit
            if account.type in ["ASSET", "EXPENSE"]:
                net_balance = debit - credit
            # Liability/Equity/Revenue: Credit - Debit
            else:
                net_balance = credit - debit

            results.append({
                "account_id": str(account.id),
                "account_name": account.name,
                "account_type": account.type,
                "debit": debit,
                "credit": credit,
                "net_balance": net_balance
            })
            
            total_debit += debit
            total_credit += credit

        return {
            "year": ledger_year.year,
            "is_closed": ledger_year.is_closed,
            "accounts": results,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "is_balanced": abs(total_debit - total_credit) < Decimal('0.0001')
        }

    @staticmethod
    def get_t_account_details(ledger_year: LedgerYear, account: LedgerAccount):
        """
        Returns detailed debit and credit entries for a T-account view.
        """
        entries = LedgerEntry.objects.filter(
            transaction__ledger_year=ledger_year,
            account=account
        ).select_related('transaction').order_by('transaction__date', 'transaction__created_at')
        
        debits = []
        credits = []
        
        for entry in entries:
            item = {
                "id": str(entry.id),
                "transaction_id": str(entry.transaction.id),
                "date": entry.transaction.date,
                "description": entry.transaction.description,
                "amount": entry.amount
            }
            if entry.entry_type == "DEBIT":
                debits.append(item)
            else:
                credits.append(item)
                
        return {
            "account_name": account.name,
            "account_type": account.type,
            "debits": debits,
            "credits": credits,
            "total_debit": sum(e["amount"] for e in debits),
            "total_credit": sum(e["amount"] for e in credits)
        }
