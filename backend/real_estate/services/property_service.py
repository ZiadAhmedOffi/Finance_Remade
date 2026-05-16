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

        purchase_price = Decimal(str(data['purchase_price']))
        monthly_rent = Decimal(str(data['monthly_rent']))
        
        property_obj = Property.objects.create(
            portfolio=portfolio,
            name=data['name'],
            city=data['city'],
            country=data['country'],
            submarket=data.get('submarket', ''),
            property_type=data['property_type'],
            financing_type=data['financing_type'],
            status=data.get('status', 'HELD'),
            purchase_date=data['purchase_date'],
            purchase_price=purchase_price,
            size=Decimal(str(data.get('size', 0.00))),
            monthly_rent=monthly_rent,
            other_operational_expenses=Decimal(str(data.get('other_operational_expenses', 0.00))),
            acq_fee_percentage=acq_fee,
            appreciation_rate_percentage=app_rate,
            vacancy_rate_percentage=vacancy
        )

        # Automatic Entry Creation based on Financing Type
        if property_obj.financing_type == "PRIMARY_INSTALLMENTS":
            from .installment_service import InstallmentService
            InstallmentService.create_installment_entry(
                property_obj=property_obj,
                data={
                    "down_payment": purchase_price * Decimal('0.20'),
                    "tenor": 5,
                    "payments_per_year": 1,
                    "start_date": property_obj.purchase_date
                }
            )
        elif property_obj.financing_type == "MORTGAGED":
            from .financing_service import FinancingService
            FinancingService.create_financing_entry(
                property_obj=property_obj,
                data={
                    "loan_amount": purchase_price * Decimal('0.70'), # 70% LTV default
                    "base_interest_rate": Decimal('5.00'),
                    "tenor": 20,
                    "payments_per_year": 12,
                    "loan_start_date": property_obj.purchase_date
                }
            )
        
        return property_obj

    @staticmethod
    @transaction.atomic
    def update_property(property_obj: Property, data: dict) -> Property:
        """
        Updates an existing property.
        """
        fields = [
            'name', 'city', 'country', 'submarket', 'property_type', 
            'financing_type', 'status', 'purchase_date', 'purchase_price', 
            'size', 'monthly_rent', 'other_operational_expenses', 
            'acq_fee_percentage', 'appreciation_rate_percentage', 
            'vacancy_rate_percentage'
        ]
        
        for field in fields:
            if field in data:
                setattr(property_obj, field, data[field])
        
        property_obj.save()
        return property_obj
