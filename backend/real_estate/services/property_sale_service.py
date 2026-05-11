from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import PropertySale, Property

class PropertySaleService:
    @staticmethod
    @transaction.atomic
    def create_property_sale(*, property_obj: Property, data: dict) -> PropertySale:
        """
        Creates a new property sale entry.
        """
        # Check if sale already exists for this property
        if hasattr(property_obj, 'sale'):
            raise ValidationError(f"A sale entry already exists for property {property_obj.name}.")

        selling_fee_percentage = data.get('selling_fee_percentage')
        if selling_fee_percentage is None:
            # Fallback to portfolio default if not provided
            selling_fee_percentage = property_obj.portfolio.assumptions.selling_fee_percentage

        sale = PropertySale.objects.create(
            property=property_obj,
            sale_date=data.get('sale_date'),
            selling_price=Decimal(str(data.get('selling_price'))),
            selling_fee_percentage=Decimal(str(selling_fee_percentage))
        )
        
        return sale

    @staticmethod
    @transaction.atomic
    def update_property_sale(*, sale: PropertySale, data: dict) -> PropertySale:
        """
        Updates an existing property sale entry.
        """
        if 'sale_date' in data:
            sale.sale_date = data.get('sale_date')
            
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
        Deletes a property sale entry.
        """
        sale.delete()
