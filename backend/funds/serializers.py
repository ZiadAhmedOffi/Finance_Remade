import math
from rest_framework import serializers
from .models import Fund, FundLog, ModelInput, InvestmentDeal
from django.contrib.auth import get_user_model

User = get_user_model()

class ModelInputSerializer(serializers.ModelSerializer):
    average_ticket = serializers.SerializerMethodField()
    expected_number_of_investors = serializers.SerializerMethodField()

    class Meta:
        model = ModelInput
        fields = [
            "id",
            "fund",
            "target_fund_size",
            "inception_year",
            "fund_life",
            "investment_period",
            "exit_horizon",
            "min_investor_ticket",
            "max_investor_ticket",
            "lock_up_period",
            "preferred_return",
            "management_fee",
            "admin_cost",
            "least_expected_moic_tier_1",
            "least_expected_moic_tier_2",
            "tier_1_carry",
            "tier_2_carry",
            "tier_3_carry",
            "average_ticket",
            "expected_number_of_investors",
            "updated_at",
        ]
        read_only_fields = ["id", "fund", "updated_at"]

    def get_average_ticket(self, obj):
        return (obj.min_investor_ticket + obj.max_investor_ticket) / 2

    def get_expected_number_of_investors(self, obj):
        avg = self.get_average_ticket(obj)
        if avg == 0:
            return 0
        return math.ceil(obj.target_fund_size / avg)


class InvestmentDealSerializer(serializers.ModelSerializer):
    """
    Serializer for InvestmentDeal including calculated financial metrics.
    Calculates holding period, ownership %, exit valuation, and exit value.
    """
    holding_period = serializers.SerializerMethodField()
    post_money_ownership = serializers.SerializerMethodField()
    exit_valuation = serializers.SerializerMethodField()
    exit_value = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentDeal
        fields = [
            "id",
            "fund",
            "company_name",
            "company_type",
            "industry",
            "entry_year",
            "exit_year",
            "amount_invested",
            "entry_valuation",
            "base_factor",
            "downside_factor",
            "upside_factor",
            "selected_scenario",
            "holding_period",
            "post_money_ownership",
            "exit_valuation",
            "exit_value",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "fund", "created_at", "updated_at"]

    def get_holding_period(self, obj):
        """Calculated by subtracting entry year from exit year."""
        return obj.exit_year - obj.entry_year

    def get_post_money_ownership(self, obj):
        """Formula: amount_invested / (amount_invested + entry_valuation)."""
        denominator = obj.amount_invested + obj.entry_valuation
        if denominator == 0:
            return 0
        return (obj.amount_invested / denominator) * 100

    def get_exit_valuation(self, obj):
        """Calculated by multiplying the factor of the selected scenario by entry valuation."""
        factor = getattr(obj, f"{obj.selected_scenario.lower()}_factor", 1.00)
        return obj.entry_valuation * factor

    def get_exit_value(self, obj):
        """Calculated by multiplying the ownership percentage by the exit valuation."""
        ownership_decimal = self.get_post_money_ownership(obj) / 100
        exit_val = self.get_exit_valuation(obj)
        return float(ownership_decimal) * float(exit_val)

class FundSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    steering_committee = serializers.SerializerMethodField()

    class Meta:
        model = Fund
        fields = [
            "id",
            "name",
            "description",
            "created_by",
            "created_by_email",
            "created_at",
            "is_active",
            "steering_committee",
        ]
        read_only_fields = ["created_by", "created_at"]

    def get_steering_committee(self, obj):
        from users.models import UserRoleAssignment
        assignments = UserRoleAssignment.objects.filter(
            fund=obj, 
            role__name="STEERING_COMMITTEE"
        ).select_related("user")
        return [assignment.user.email for assignment in assignments]

class FundLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)
    target_fund_name = serializers.EmailField(source="target_fund.name", read_only=True)

    class Meta:
        model = FundLog
        fields = [
            "id",
            "actor",
            "actor_email",
            "target_fund",
            "target_fund_name",
            "action",
            "success",
            "metadata",
            "timestamp",
        ]
