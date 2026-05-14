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
        
        # Pull defaults from assumptions if not provided in data
        acq_fee = data.get('acq_fee_percentage', assumptions.acquisition_fee_percentage)
        app_rate = data.get('appreciation_rate_percentage', assumptions.default_appreciation_rate)
        vacancy = data.get('vacancy_rate_percentage', assumptions.default_vacancy_rate)
        
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
            purchase_price=data['purchase_price'],
            size=data.get('size', 0.00),
            monthly_rent=data['monthly_rent'],
            other_operational_expenses=data.get('other_operational_expenses', 0.00),
            acq_fee_percentage=acq_fee,
            appreciation_rate_percentage=app_rate,
            vacancy_rate_percentage=vacancy
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
