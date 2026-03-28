import math
from rest_framework import serializers
from .models import Fund, FundLog, ModelInput, InvestmentDeal, CurrentDeal, InvestmentRound
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


from datetime import datetime

class InvestmentRoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentRound
        fields = [
            "id",
            "fund",
            "company_name",
            "year",
            "pre_money_valuation",
            "new_money_raised",
            "target_valuation",
            "exercise_pro_rata",
            "amount_invested",
            "associated_deal",
            "new_ownership_percentage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "fund", "created_at", "updated_at"]

class InvestmentDealSerializer(serializers.ModelSerializer):
    """
    Serializer for InvestmentDeal including calculated financial metrics.
    Calculates holding period, ownership %, exit valuation, and exit value.
    """
    holding_period = serializers.SerializerMethodField()
    post_money_ownership = serializers.SerializerMethodField()
    exit_valuation = serializers.SerializerMethodField()
    exit_value = serializers.SerializerMethodField()
    expected_ownership_after_dilution = serializers.SerializerMethodField()
    expected_pro_rata_investments = serializers.SerializerMethodField()

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
            "expected_number_of_rounds",
            "expected_ownership_after_dilution",
            "expected_pro_rata_investments",
            "is_pro_rata",
            "pro_rata_rights",
            "parent_deal",
            "holding_period",
            "post_money_ownership",
            "exit_valuation",
            "exit_value",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "fund", "created_at", "updated_at"]

    def validate(self, data):
        """
        Check that entry_year and exit_year are at least the current year.
        Also validate pro rata logic.
        """
        current_year = datetime.now().year
        entry_year = data.get("entry_year")
        exit_year = data.get("exit_year")
        is_pro_rata = data.get("is_pro_rata", False)
        parent_deal = data.get("parent_deal")
        company_name = data.get("company_name")

        if entry_year and entry_year < current_year:
            raise serializers.ValidationError({"entry_year": f"Entry year must be at least {current_year}."})
        if exit_year and exit_year < current_year:
            raise serializers.ValidationError({"exit_year": f"Exit year must be at least {current_year}."})
        if entry_year and exit_year and exit_year < entry_year:
            raise serializers.ValidationError({"exit_year": "Exit year cannot be before entry year."})
        
        if is_pro_rata:
            if not parent_deal:
                raise serializers.ValidationError({"parent_deal": "A parent deal must be selected for pro rata deals."})
            if parent_deal.company_name != company_name:
                raise serializers.ValidationError({"parent_deal": "Parent deal must belong to the same company."})
            if parent_deal.is_pro_rata:
                raise serializers.ValidationError({"parent_deal": "Parent deal cannot be a pro rata deal itself."})
        
        return data

    def get_holding_period(self, obj):
        """Calculated by subtracting entry year from exit year."""
        return obj.exit_year - obj.entry_year

    def get_post_money_ownership(self, obj):
        """Formula: amount_invested / (amount_invested + entry_valuation)."""
        denominator = float(obj.amount_invested) + float(obj.entry_valuation)
        if denominator == 0:
            return 0
        return (float(obj.amount_invested) / denominator) * 100

    def get_expected_ownership_after_dilution(self, obj):
        """
        Calculates expected ownership after dilution based on pro-rata rights.
        With pro-rata: original ownership * (0.9)^(number of rounds)
        Without pro-rata: original ownership * (0.8)^(number of rounds)
        """
        original_ownership = float(self.get_post_money_ownership(obj))
        rounds = int(obj.expected_number_of_rounds)
        
        factor = 0.9 if obj.pro_rata_rights else 0.8
        return original_ownership * (factor ** rounds)

    def get_expected_pro_rata_investments(self, obj):
        """
        Calculates expected pro rata investments (USD).
        Summation from i=1 to rounds [0.1 * original ownership * entry valuation * scenario factor * (0.9 * scenario factor)^(i-1)]
        Only if pro_rata_rights is True.
        """
        if not obj.pro_rata_rights:
            return 0
        
        original_ownership_decimal = float(self.get_post_money_ownership(obj)) / 100
        scenario_factor = float(getattr(obj, f"{obj.selected_scenario.lower()}_factor", 1.00))
        entry_valuation = float(obj.entry_valuation)
        rounds = int(obj.expected_number_of_rounds)
        
        total = 0
        base_val = 0.1 * original_ownership_decimal * entry_valuation * scenario_factor
        growth_factor = 0.9 * scenario_factor
        
        for i in range(1, rounds + 1):
            total += base_val * (growth_factor ** (i - 1))
            
        return total

    def get_exit_valuation(self, obj):
        """Calculated by multiplying the factor of the selected scenario by the post-money valuation (entry valuation + amount invested)."""
        factor = getattr(obj, f"{obj.selected_scenario.lower()}_factor", 1.00)
        post_money_valuation = obj.entry_valuation + obj.amount_invested
        return post_money_valuation * factor

    def get_exit_value(self, obj):
        """Calculated by multiplying the expected ownership percentage after dilution by the exit valuation."""
        ownership_decimal = self.get_expected_ownership_after_dilution(obj) / 100
        exit_val = self.get_exit_valuation(obj)
        return float(ownership_decimal) * float(exit_val)

class CurrentDealSerializer(serializers.ModelSerializer):
    """
    Serializer for CurrentDeal including calculated financial metrics.
    Calculates holding period, ownership %, MOIC, and final exit amount.
    """
    holding_period = serializers.SerializerMethodField()
    post_money_ownership = serializers.SerializerMethodField()
    moic = serializers.SerializerMethodField()
    final_exit_amount = serializers.SerializerMethodField()
    ownership_after_dilution = serializers.SerializerMethodField()

    class Meta:
        model = CurrentDeal
        fields = [
            "id",
            "fund",
            "company_name",
            "company_type",
            "industry",
            "entry_year",
            "latest_valuation_year",
            "amount_invested",
            "entry_valuation",
            "latest_valuation",
            "is_pro_rata",
            "pro_rata_rights",
            "parent_deal",
            "holding_period",
            "post_money_ownership",
            "ownership_after_dilution",
            "moic",
            "final_exit_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "fund", "created_at", "updated_at"]

    def validate(self, data):
        """
        Check that entry_year and latest_valuation_year are not in the future.
        Also validate pro rata logic.
        """
        current_year = datetime.now().year
        entry_year = data.get("entry_year")
        val_year = data.get("latest_valuation_year")
        is_pro_rata = data.get("is_pro_rata", False)
        parent_deal = data.get("parent_deal")
        company_name = data.get("company_name")

        if entry_year and entry_year > current_year:
            raise serializers.ValidationError({"entry_year": f"Entry year cannot be in the future (max {current_year})."})
        if val_year and val_year > current_year:
            raise serializers.ValidationError({"latest_valuation_year": f"Latest valuation year cannot be in the future (max {current_year})."})
        if entry_year and val_year and val_year < entry_year:
            raise serializers.ValidationError({"latest_valuation_year": "Latest valuation year cannot be before entry year."})
        
        if is_pro_rata:
            if not parent_deal:
                raise serializers.ValidationError({"parent_deal": "A parent deal must be selected for pro rata deals."})
            if parent_deal.company_name != company_name:
                raise serializers.ValidationError({"parent_deal": "Parent deal must belong to the same company."})
            if parent_deal.is_pro_rata:
                raise serializers.ValidationError({"parent_deal": "Parent deal cannot be a pro rata deal itself."})
        
        return data

    def get_holding_period(self, obj):
        """Calculated by subtracting entry year from latest valuation year."""
        return obj.latest_valuation_year - obj.entry_year

    def get_post_money_ownership(self, obj):
        """
        Formula: amount_invested / (amount_invested + entry_valuation).
        For pro-rata deals, returns the ownership percentage from the associated investment round.
        """
        if obj.is_pro_rata:
            try:
                # InvestmentRound has a OneToOneField to CurrentDeal with related_name 'investment_round'
                return float(obj.investment_round.new_ownership_percentage)
            except:
                pass

        denominator = float(obj.amount_invested) + float(obj.entry_valuation)
        if denominator == 0:
            return 0
        return (float(obj.amount_invested) / denominator) * 100

    def get_ownership_after_dilution(self, obj):
        """Returns the ownership percentage from the latest investment round, or original ownership if no rounds."""
        latest_round = InvestmentRound.objects.filter(
            fund=obj.fund, 
            company_name=obj.company_name
        ).order_by('-year', '-created_at').first()
        
        if latest_round:
            return float(latest_round.new_ownership_percentage)
        return self.get_post_money_ownership(obj)

    def get_moic(self, obj):
        """Formula: latest_valuation / post_money_valuation (entry_valuation + amount_invested)."""
        post_money_valuation = float(obj.entry_valuation) + float(obj.amount_invested)
        if post_money_valuation == 0:
            return 0
        return float(obj.latest_valuation) / post_money_valuation

    def get_final_exit_amount(self, obj):
        """Formula: ownership_after_dilution % * latest_valuation."""
        ownership_decimal = float(self.get_ownership_after_dilution(obj)) / 100
        return ownership_decimal * float(obj.latest_valuation)

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
            "status",
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
