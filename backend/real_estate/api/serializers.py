from rest_framework import serializers
from ..models import RealEstatePortfolio, RealEstateAssumptions

class RealEstateAssumptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealEstateAssumptions
        fields = [
            'id', 'portfolio', 'inception_date', 'forecast_horizon',
            'default_appreciation_rate', 'default_rental_growth_rate',
            'default_vacancy_rate', 'default_discount_rate',
            'acquisition_fee_percentage', 'property_mgmt_fee_percentage',
            'maintenance_percentage_of_value', 'selling_fee_percentage',
            'active_scenario', 'updated_at'
        ]
        read_only_fields = ['id', 'portfolio', 'updated_at']

class RealEstatePortfolioSerializer(serializers.ModelSerializer):
    assumptions = RealEstateAssumptionsSerializer(read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = RealEstatePortfolio
        fields = [
            'id', 'name', 'description', 'region', 
            'status', 'created_by_email', 'created_at',
            'assumptions'
        ]
        read_only_fields = ['id', 'created_at', 'created_by_email']
