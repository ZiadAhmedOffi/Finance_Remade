from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import InstallmentEntry, Property, RealEstatePortfolio

class InstallmentService:
    @staticmethod
    @transaction.atomic
    def create_installment_entry(*, property_obj: Property, data: dict) -> InstallmentEntry:
        """
        Creates a new installment entry for a property.
        """
        purchase_price = Decimal(str(property_obj.purchase_price))
        down_payment = Decimal(str(data.get('down_payment', purchase_price * Decimal('0.20'))))
        
        # Validation: Down Payment < Purchase Price
        if down_payment >= purchase_price:
            raise ValidationError(f"Down payment ({down_payment}) must be lower than the purchase price ({purchase_price}).")
        
        # Check if one already exists
        if hasattr(property_obj, 'installment'):
            raise ValidationError(f"An installment entry already exists for property {property_obj.name}.")

        entry = InstallmentEntry.objects.create(
            property=property_obj,
            down_payment=down_payment,
            tenor=int(data.get('tenor', 5)),
            payments_per_year=int(data.get('payments_per_year', 1)),
            start_date=data.get('start_date', property_obj.purchase_date)
        )
        
        return entry

    @staticmethod
    @transaction.atomic
    def update_installment_entry(*, entry: InstallmentEntry, data: dict) -> InstallmentEntry:
        """
        Updates an existing installment entry.
        """
        if 'down_payment' in data:
            entry.down_payment = Decimal(str(data.get('down_payment')))
        
        if 'tenor' in data:
            entry.tenor = int(data.get('tenor'))
            
        if 'payments_per_year' in data:
            entry.payments_per_year = int(data.get('payments_per_year'))
            
        if 'start_date' in data:
            entry.start_date = data.get('start_date')

        entry.save()
        return entry

    @staticmethod
    @transaction.atomic
    def delete_installment_entry(*, entry: InstallmentEntry):
        """
        Deletes an installment entry.
        """
        entry.delete()
