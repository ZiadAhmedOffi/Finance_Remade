import math
from rest_framework import serializers
from funds.models import Fund, FundLog, ModelInput, InvestmentDeal, CurrentDeal, InvestmentRound, RiskAssessment, PossibleCapitalSource, InvestorAction, InvestorRequest
from django.contrib.auth import get_user_model

User = get_user_model()

class PossibleCapitalSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PossibleCapitalSource
        fields = [
            "id",
            "fund",
            "name",
            "amount",
            "year",
            "created_at",
        ]
        read_only_fields = ["id", "fund", "created_at"]

    def validate_year(self, value):
        current_year = datetime.now().year
        if value < current_year:
            raise serializers.ValidationError(f"Year of intent declaration cannot be smaller than the current year ({current_year}).")
        return value

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
            "failure_rate",
            "break_even_rate",
            "high_growth_rate",
            "dilution_rate",
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
        from funds.selectors import deal_selectors
        return deal_selectors.calculate_investment_deal_post_money_ownership(obj)

    def get_expected_ownership_after_dilution(self, obj):
        from funds.selectors import deal_selectors
        return deal_selectors.calculate_investment_deal_expected_ownership_after_dilution(obj)

    def get_expected_pro_rata_investments(self, obj):
        from funds.selectors import deal_selectors
        return deal_selectors.calculate_investment_deal_expected_pro_rata_investments(obj)

    def get_exit_valuation(self, obj):
        from funds.selectors import deal_selectors
        return deal_selectors.calculate_investment_deal_exit_valuation(obj)

    def get_exit_value(self, obj):
        from funds.selectors import deal_selectors
        return deal_selectors.calculate_investment_deal_exit_value(obj)

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
            "expected_exit_multiple",
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
        """Calculated by subtracting entry year from current year."""
        current_year = datetime.now().year
        return current_year - obj.entry_year

    def get_post_money_ownership(self, obj):
        from funds.selectors import deal_selectors
        return deal_selectors.calculate_current_deal_post_money_ownership(obj)

    def get_ownership_after_dilution(self, obj):
        from funds.selectors import deal_selectors
        return deal_selectors.calculate_current_deal_ownership_after_dilution(obj)

    def get_moic(self, obj):
        """Formula: latest_valuation / post_money_valuation (entry_valuation + amount_invested)."""
        post_money_valuation = float(obj.entry_valuation) + float(obj.amount_invested)
        if post_money_valuation == 0:
            return 0
        return float(obj.latest_valuation) / post_money_valuation

    def get_final_exit_amount(self, obj):
        from funds.selectors import deal_selectors
        return deal_selectors.calculate_current_deal_final_exit_amount(obj)

class FundSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    steering_committee = serializers.SerializerMethodField()
    model_inputs = ModelInputSerializer(read_only=True)

    class Meta:
        model = Fund
        fields = [
            "id",
            "name",
            "description",
            "tag",
            "sharia_compliant",
            "region",
            "focus",
            "overview",
            "strategy",
            "structure",
            "strategy_and_fund_lifecycle",
            "reasons_to_invest",
            "created_by",
            "created_by_email",
            "created_at",
            "status",
            "total_units",
            "steering_committee",
            "model_inputs",
        ]
        read_only_fields = ["created_by", "created_at", "total_units"]

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
        read_only_fields = ["id", "actor", "actor_email", "target_fund", "target_fund_name", "timestamp"]

from funds.models import InvestorAction

class RiskAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskAssessment
        fields = [
            "id",
            "fund",
            "company_name",
            "execution_capacity_score",
            "market_validation_score",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "fund", "created_at", "updated_at"]

class InvestorActionSerializer(serializers.ModelSerializer):
    investor_email = serializers.EmailField(source="investor.email", read_only=True)
    fund_name = serializers.CharField(source="fund.name", read_only=True)
    investor_selling_email = serializers.EmailField(source="investor_selling.email", read_only=True)
    investor_sold_to_email = serializers.EmailField(source="investor_sold_to.email", read_only=True)

    class Meta:
        model = InvestorAction
        fields = [
            "id",
            "investor",
            "investor_email",
            "fund",
            "fund_name",
            "type",
            "year",
            "amount",
            "percentage_sold",
            "discount_percentage",
            "investor_selling",
            "investor_selling_email",
            "investor_sold_to",
            "investor_sold_to_email",
            "units",
            "original_value",
            "exit_value",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "units"]

    def validate(self, data):
        action_type = data.get("type")
        if action_type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
            if data.get("amount") is None:
                raise serializers.ValidationError({"amount": "Amount is required for investment."})
        elif action_type == "SECONDARY_EXIT":
            if data.get("percentage_sold") is None:
                raise serializers.ValidationError({"percentage_sold": "Percentage sold is required for secondary exit."})
            if data.get("investor_selling") is None:
                raise serializers.ValidationError({"investor_selling": "Investor selling is required for secondary exit."})
        
        # Percentages should be between 0 and 100
        # Note: They are calculated as (value / 100) when used for fractional math
        pct_sold = data.get("percentage_sold")
        discount = data.get("discount_percentage", 0)
        
        if pct_sold is not None and (pct_sold < 0 or pct_sold > 100):
            raise serializers.ValidationError({"percentage_sold": "Percentage sold must be between 0 and 100."})
        if discount is not None and (discount < 0 or discount > 100):
            raise serializers.ValidationError({"discount_percentage": "Discount percentage must be between 0 and 100."})
                
        return data

from funds.models import Report

class ReportSerializer(serializers.ModelSerializer):
    fund_name = serializers.CharField(source="fund.name", read_only=True)
    fund_details = FundSerializer(source="fund", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "slug",
            "name",
            "report_type",
            "fund",
            "fund_name",
            "fund_details",
            "config_json",
            "status",
            "static_url",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "static_url", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        import uuid
        # Generate a unique slug if not provided (though read_only above)
        validated_data['slug'] = str(uuid.uuid4())[:8]
        return super().create(validated_data)

class InvestorRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    fund_name = serializers.CharField(source="fund.name", read_only=True)

    class Meta:
        model = InvestorRequest
        fields = [
            "id",
            "user",
            "user_email",
            "fund",
            "fund_name",
            "type",
            "status",
            "requested_amount",
            "liquidation_percentage",
            "units_to_sell",
            "expected_value",
            "admin_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "status", "created_at", "updated_at"]

    def validate(self, data):
        # Prevent liquidation requests during lockup period
        request_type = data.get('type')
        fund = data.get('fund')

        if request_type == 'LIQUIDATION' and fund:
            from datetime import datetime
            model_inputs = getattr(fund, 'model_inputs', None)
            if model_inputs:
                inception_year = model_inputs.inception_year
                lockup_period = model_inputs.lock_up_period
                current_year = datetime.now().year
                if current_year < (inception_year + lockup_period):
                    raise serializers.ValidationError(
                        f"This fund is in a lockup period until {inception_year + lockup_period}. "
                        "Liquidation requests are not permitted at this time."
                    )
        return data
