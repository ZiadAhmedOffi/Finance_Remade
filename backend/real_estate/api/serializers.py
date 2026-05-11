from rest_framework import serializers
from ..models import RealEstatePortfolio, RealEstateAssumptions, Property, FinancingEntry, OffPlanDetails, OffPlanMilestone

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

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = [
            'id', 'portfolio', 'name', 'city', 'country', 'submarket',
            'property_type', 'financing_type', 'status',
            'purchase_date', 'purchase_price', 'monthly_rent',
            'other_operational_expenses', 'acq_fee_percentage',
            'appreciation_rate_percentage', 'vacancy_rate_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class FinancingEntrySerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    purchase_price = serializers.DecimalField(source='property.purchase_price', max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = FinancingEntry
        fields = [
            'id', 'property', 'property_name', 'purchase_price',
            'loan_amount', 'base_interest_rate', 'tenor',
            'payments_per_year', 'loan_start_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class FinancingEntryWithMetricsSerializer(serializers.Serializer):
    entry = FinancingEntrySerializer()
    metrics = serializers.JSONField()

class OffPlanDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffPlanDetails
        fields = [
            'id', 'property', 'construction_start_date', 
            'expected_completion_date', 'appreciation_rate_at_completion',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class OffPlanMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffPlanMilestone
        fields = [
            'id', 'property', 'milestone_name', 'date', 
            'percentage_of_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class PropertyWithMetricsSerializer(serializers.Serializer):
    property = PropertySerializer()
    metrics = serializers.JSONField()
