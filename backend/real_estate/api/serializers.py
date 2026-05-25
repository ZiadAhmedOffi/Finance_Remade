from rest_framework import serializers
from ..models import (
    RealEstatePortfolio, 
    RealEstateAssumptions, 
    Property, 
    FinancingEntry, 
    OffPlanDetails, 
    OffPlanMilestone,
    PropertySale,
    RealEstatePossibleCapitalSource,
    RealEstateInvestorAction,
    RealEstateInvestorStats,
    InstallmentEntry,
    UsufructDetails,
    Jurisdiction,
    TaxRule
)

class JurisdictionSerializer(serializers.ModelSerializer):
    rules_count = serializers.IntegerField(source='rules.count', read_only=True)

    class Meta:
        model = Jurisdiction
        fields = ['id', 'name', 'currency', 'rules_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class TaxRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRule
        fields = [
            'id', 'jurisdiction', 'name', 'event_type', 'trigger', 'tax_base',
            'rate', 'valuation_ratio', 'revaluation_freq', 
            'deductibility_cap', 'lcf_limit', 'responsible_party', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class RealEstateAssumptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealEstateAssumptions
        fields = [
            'id', 'portfolio', 'inception_date', 'forecast_horizon',
            'default_appreciation_rate', 'default_rental_growth_rate',
            'default_vacancy_rate', 'default_discount_rate', 'default_depreciation_rate',
            'acquisition_fee_percentage', 'property_mgmt_fee_percentage',
            'maintenance_percentage_of_value', 'selling_fee_percentage',
            'active_scenario', 'updated_at'
        ]
        read_only_fields = ['id', 'portfolio', 'updated_at']

class RealEstatePortfolioSerializer(serializers.ModelSerializer):
    assumptions = RealEstateAssumptionsSerializer(read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    jurisdiction_name = serializers.CharField(source='jurisdiction.name', read_only=True)

    class Meta:
        model = RealEstatePortfolio
        fields = [
            'id', 'name', 'description', 'region', 'jurisdiction', 'jurisdiction_name',
            'status', 'created_by_email', 'created_at',
            'assumptions'
        ]
        read_only_fields = ['id', 'created_at', 'created_by_email', 'jurisdiction_name']

class UsufructDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsufructDetails
        fields = [
            'id', 'property', 'investor_role', 'insurance_cost', 'prep_cost',
            'outflow_monthly_rent', 'annual_ops_cost', 'inflow_monthly_rent',
            'outflow_rent_appreciation_percentage',
            'inflow_rent_appreciation_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class PropertySerializer(serializers.ModelSerializer):
    usufruct_details = UsufructDetailsSerializer(read_only=True, required=False)

    class Meta:
        model = Property
        fields = [
            'id', 'portfolio', 'name', 'city', 'country', 'submarket',
            'property_type', 'financing_type', 'status', 'transaction_type',
            'purchase_date', 'purchase_price', 'size', 'monthly_rent',
            'other_operational_expenses', 'acq_fee_percentage',
            'appreciation_rate_percentage', 'vacancy_rate_percentage',
            'usufruct_details', 'created_at', 'updated_at'
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

class InstallmentEntrySerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    purchase_price = serializers.DecimalField(source='property.purchase_price', max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = InstallmentEntry
        fields = [
            'id', 'property', 'property_name', 'purchase_price',
            'down_payment', 'tenor', 'payments_per_year', 'start_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class FinancingEntryWithMetricsSerializer(serializers.Serializer):
    entry = FinancingEntrySerializer()
    metrics = serializers.JSONField()

class InstallmentEntryWithMetricsSerializer(serializers.Serializer):
    entry = InstallmentEntrySerializer()
    metrics = serializers.JSONField()

class OffPlanDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffPlanDetails
        fields = [
            'id', 'property', 'construction_start_date', 
            'expected_completion_date', 'appreciation_rate_at_completion',
            'sale_at_completion', 'created_at', 'updated_at'
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

class PropertySaleSerializer(serializers.ModelSerializer):
    property_name = serializers.ReadOnlyField(source='property.name')

    class Meta:
        model = PropertySale
        fields = [
            'id', 'property', 'property_name', 'sale_date', 
            'selling_price', 'selling_fee_percentage', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class PropertySaleWithMetricsSerializer(serializers.Serializer):
    sale = PropertySaleSerializer()
    metrics = serializers.JSONField()

class RealEstatePossibleCapitalSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealEstatePossibleCapitalSource
        fields = ['id', 'portfolio', 'name', 'amount', 'year', 'created_at']
        read_only_fields = ['id', 'created_at']

class RealEstateInvestorActionSerializer(serializers.ModelSerializer):
    investor_email = serializers.EmailField(source='investor.email', read_only=True)
    investor_selling_email = serializers.EmailField(source='investor_selling.email', read_only=True, allow_null=True)
    investor_sold_to_email = serializers.EmailField(source='investor_sold_to.email', read_only=True, allow_null=True)

    class Meta:
        model = RealEstateInvestorAction
        fields = [
            'id', 'portfolio', 'investor', 'investor_email', 'type', 'year', 
            'amount', 'percentage_sold', 'discount_percentage',
            'investor_selling', 'investor_selling_email',
            'investor_sold_to', 'investor_sold_to_email',
            'units', 'created_at'
        ]
        read_only_fields = ['id', 'portfolio', 'units', 'created_at']

class RealEstateInvestorStatsSerializer(serializers.ModelSerializer):
    investor_email = serializers.EmailField(source='investor.email', read_only=True)
    first_name = serializers.CharField(source='investor.first_name', read_only=True)
    last_name = serializers.CharField(source='investor.last_name', read_only=True)

    class Meta:
        model = RealEstateInvestorStats
        fields = [
            'id', 'portfolio', 'investor', 'investor_email', 'first_name', 'last_name',
            'amount_invested', 'capital_deployed', 'realized_gain', 'units'
        ]
        read_only_fields = ['id']
