from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import FinancingEntry, Property, RealEstatePortfolio

class FinancingService:
    @staticmethod
    @transaction.atomic
    def create_financing_entry(*, property_obj: Property, data: dict) -> FinancingEntry:
        """
        Creates a new financing entry for a property.
        """
        loan_amount = Decimal(str(data.get('loan_amount')))
        purchase_price = Decimal(str(property_obj.purchase_price))
        
        # Validation: Loan Amount < Purchase Price
        if loan_amount >= purchase_price:
            raise ValidationError(f"Loan amount ({loan_amount}) must be lower than the purchase price ({purchase_price}).")
        
        # Check if one already exists (OneToOneField will enforce this anyway, but good to be explicit)
        if hasattr(property_obj, 'financing'):
            raise ValidationError(f"A financing entry already exists for property {property_obj.name}.")

        from django.utils.dateparse import parse_date
        loan_start_date = data.get('loan_start_date')
        if isinstance(loan_start_date, str):
            loan_start_date = parse_date(loan_start_date)

        entry = FinancingEntry.objects.create(
            property=property_obj,
            loan_amount=loan_amount,
            base_interest_rate=Decimal(str(data.get('base_interest_rate'))),
            tenor=int(data.get('tenor')),
            payments_per_year=int(data.get('payments_per_year', 12)),
            loan_start_date=loan_start_date
        )
        
        # Bookkeeping Integration
        from .ledger_sync_service import LedgerSyncService
        LedgerSyncService.sync_financing_entry(entry)
        
        return entry

    @staticmethod
    @transaction.atomic
    def update_financing_entry(*, entry: FinancingEntry, data: dict) -> FinancingEntry:
        """
        Updates an existing financing entry.
        """
        if 'loan_amount' in data:
            loan_amount = Decimal(str(data.get('loan_amount')))
            # We don't block the update if it's >= purchase price as per recommendation,
            # but we could log a warning or just let the selector handle the UI alert.
            # Actually, the user agreed to "Allow the update but flag it in the Financing Model table".
            # So I won't raise ValidationError here for loan_amount vs purchase_price on update,
            # unless the user explicitly wants to block it. 
            # Wait, the PLAN says "this check should be done only when the user submits the entry".
            # This usually implies creation and modification.
            # But the recommendation I gave was "allow the update but flag it... rather than blocking".
            # So I'll follow my recommendation.
            entry.loan_amount = loan_amount

        if 'base_interest_rate' in data:
            entry.base_interest_rate = Decimal(str(data.get('base_interest_rate')))
        
        if 'tenor' in data:
            entry.tenor = int(data.get('tenor'))
            
        if 'payments_per_year' in data:
            entry.payments_per_year = int(data.get('payments_per_year'))
            
        if 'loan_start_date' in data:
            from django.utils.dateparse import parse_date
            lsd = data.get('loan_start_date')
            entry.loan_start_date = parse_date(lsd) if isinstance(lsd, str) else lsd

        entry.save()
        return entry

    @staticmethod
    @transaction.atomic
    def delete_financing_entry(*, entry: FinancingEntry):
        """
        Deletes a financing entry.
        """
        entry.delete()
