from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import PropertySale, Property

class PropertySaleService:
    @staticmethod
    @transaction.atomic
    def create_property_sale(*, property_obj: Property, data: dict) -> PropertySale:
        """
        Creates a new property sale entry and marks the property as SOLD.
        """
        # 1. Ownership and Type Validations
        if property_obj.status != "HELD":
            if property_obj.status == "SOLD":
                raise ValidationError(f"Property {property_obj.name} is already sold.")
            elif property_obj.status == "OFF_PLAN":
                raise ValidationError(f"Property {property_obj.name} is Off-Plan and cannot be sold until it is completed and 'Held'.")
            elif property_obj.status == "USUFRUCT":
                raise ValidationError(f"Property {property_obj.name} is a Usufruct property and cannot be sold.")
            else:
                raise ValidationError(f"Property {property_obj.name} has status '{property_obj.status}' and cannot be sold.")

        selling_fee_percentage = data.get('selling_fee_percentage')
        if selling_fee_percentage is None:
            # Fallback to portfolio default if not provided
            selling_fee_percentage = property_obj.portfolio.assumptions.selling_fee_percentage

        from django.utils.dateparse import parse_date
        sale_date = data.get('sale_date')
        if isinstance(sale_date, str):
            sale_date = parse_date(sale_date)

        # 2. Date Validation
        if sale_date < property_obj.purchase_date:
            raise ValidationError(f"Sale date ({sale_date}) cannot be before purchase date ({property_obj.purchase_date}).")

        sale = PropertySale.objects.create(
            property=property_obj,
            sale_date=sale_date,
            selling_price=Decimal(str(data.get('selling_price'))),
            selling_fee_percentage=Decimal(str(selling_fee_percentage))
        )
        
        # Update property status
        property_obj.status = "SOLD"
        property_obj.save()
        
        # Bookkeeping Integration
        from .ledger_sync_service import LedgerSyncService
        LedgerSyncService.sync_property_sale(sale)
        
        return sale

    @staticmethod
    @transaction.atomic
    def update_property_sale(*, sale: PropertySale, data: dict) -> PropertySale:
        """
        Updates an existing property sale entry.
        """
        if 'sale_date' in data:
            from django.utils.dateparse import parse_date
            sd = data.get('sale_date')
            sale.sale_date = parse_date(sd) if isinstance(sd, str) else sd
            
        if 'selling_price' in data:
            sale.selling_price = Decimal(str(data.get('selling_price')))
            
        if 'selling_fee_percentage' in data:
            sale.selling_fee_percentage = Decimal(str(data.get('selling_fee_percentage')))

        sale.save()
        return sale

    @staticmethod
    @transaction.atomic
    def delete_property_sale(*, sale: PropertySale):
        """
        Deletes a property sale entry and reverts property status to HELD.
        """
        property_obj = sale.property
        sale_id = sale.id
        
        # 1. Cleanup Ledger
        from .ledger_service import LedgerTransactionService
        LedgerTransactionService.delete_transaction_by_source(
            source_type="PROPERTY_SALE",
            source_id=sale_id
        )

        # 2. Delete Sale Record
        sale.delete()
        
        # 3. Revert Status
        property_obj.status = "HELD"
        property_obj.save()
