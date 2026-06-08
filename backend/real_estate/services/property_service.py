from decimal import Decimal
from django.db import transaction
from ..models import Property, RealEstatePortfolio, RealEstateAssumptions

class PropertyService:
    """
    Service for handling business logic related to Real Estate Properties.
    """

    @staticmethod
    @transaction.atomic
    def create_property(portfolio: RealEstatePortfolio, data: dict) -> Property:
        """
        Creates a new property, using portfolio assumptions as defaults if rates are missing.
        """
        assumptions = portfolio.assumptions
        
        # Pull defaults from assumptions if not provided in data or if empty string
        acq_fee = data.get('acq_fee_percentage')
        if acq_fee is None or acq_fee == "":
            acq_fee = assumptions.acquisition_fee_percentage
        else:
            acq_fee = Decimal(str(acq_fee))
            
        app_rate = data.get('appreciation_rate_percentage')
        if app_rate is None or app_rate == "":
            app_rate = assumptions.default_appreciation_rate
        else:
            app_rate = Decimal(str(app_rate))
            
        vacancy = data.get('vacancy_rate_percentage')
        if vacancy is None or vacancy == "":
            vacancy = assumptions.default_vacancy_rate
        else:
            vacancy = Decimal(str(vacancy))

        purchase_price_val = data.get('purchase_price')
        purchase_price = Decimal(str(purchase_price_val)) if purchase_price_val not in [None, ""] else None
        
        monthly_rent_val = data.get('monthly_rent')
        monthly_rent = Decimal(str(monthly_rent_val)) if monthly_rent_val not in [None, ""] else None
        
        status_val = data.get('status', 'HELD')
        transaction_type_val = data.get('transaction_type', 'SECONDARY')

        # Enforcement: Off-Plan must be Primary
        if status_val == "OFF_PLAN":
            transaction_type_val = "PRIMARY"
        
        # Enforcement: Primary must have 0 acquisition fees
        if transaction_type_val == "PRIMARY":
            acq_fee = Decimal('0.00')

        from django.utils.dateparse import parse_date
        purchase_date = data['purchase_date']
        if isinstance(purchase_date, str):
            purchase_date = parse_date(purchase_date)

        property_obj = Property.objects.create(
            portfolio=portfolio,
            name=data['name'],
            city=data['city'],
            country=data['country'],
            submarket=data.get('submarket', ''),
            property_type=data['property_type'],
            financing_type=data['financing_type'],
            status=status_val,
            transaction_type=transaction_type_val,
            purchase_date=purchase_date,
            purchase_price=purchase_price,
            size=Decimal(str(data.get('size', 0.00))),
            monthly_rent=monthly_rent,
            other_operational_expenses=Decimal(str(data.get('other_operational_expenses', 0.00))),
            acq_fee_percentage=acq_fee,
            appreciation_rate_percentage=app_rate,
            vacancy_rate_percentage=vacancy
        )

        # Handle Usufruct Details
        if status_val == "USUFRUCT":
            from ..models import UsufructDetails
            UsufructDetails.objects.create(
                property=property_obj,
                insurance_cost=Decimal(str(data.get('insurance_cost', 0.00))),
                prep_cost=Decimal(str(data.get('prep_cost', 0.00))),
                outflow_monthly_rent=Decimal(str(data.get('outflow_monthly_rent', 0.00))),
                annual_ops_cost=Decimal(str(data.get('annual_ops_cost', 0.00))),
                inflow_monthly_rent=Decimal(str(data.get('inflow_monthly_rent', 0.00))),
                outflow_rent_appreciation_percentage=Decimal(str(data.get('outflow_rent_appreciation_percentage', 0.00))),
                inflow_rent_appreciation_percentage=Decimal(str(data.get('inflow_rent_appreciation_percentage', 0.00))),
            )
        
        # Bookkeeping Integration
        from .ledger_sync_service import LedgerSyncService
        LedgerSyncService.sync_property_acquisition(property_obj)
        
        return property_obj

    @staticmethod
    @transaction.atomic
    def update_property(property_obj: Property, data: dict) -> Property:
        """
        Updates an existing property.
        """
        fields = [
            'name', 'city', 'country', 'submarket', 'property_type', 
            'financing_type', 'status', 'transaction_type', 'purchase_date', 
            'purchase_price', 'size', 'monthly_rent', 'other_operational_expenses', 
            'acq_fee_percentage', 'appreciation_rate_percentage', 
            'vacancy_rate_percentage'
        ]
        
        for field in fields:
            if field in data:
                val = data[field]
                if field in ['purchase_price', 'monthly_rent'] and val in [None, ""]:
                    val = None
                
                if field == 'purchase_date' and isinstance(val, str):
                    from django.utils.dateparse import parse_date
                    val = parse_date(val)
                    
                setattr(property_obj, field, val)
        
        # Enforcement logic
        if property_obj.status == "OFF_PLAN":
            property_obj.transaction_type = "PRIMARY"
        
        if property_obj.transaction_type == "PRIMARY":
            property_obj.acq_fee_percentage = Decimal('0.00')

        property_obj.save()

        # Handle Usufruct Details
        if property_obj.status == "USUFRUCT":
            from ..models import UsufructDetails
            u_details, created = UsufructDetails.objects.get_or_create(property=property_obj)
            
            u_fields = [
                'insurance_cost', 'prep_cost', 'outflow_monthly_rent', 
                'annual_ops_cost', 'inflow_monthly_rent',
                'outflow_rent_appreciation_percentage',
                'inflow_rent_appreciation_percentage'
            ]
            for f in u_fields:
                if f in data:
                    setattr(u_details, f, Decimal(str(data[f])))
            u_details.save()
        
        return property_obj
