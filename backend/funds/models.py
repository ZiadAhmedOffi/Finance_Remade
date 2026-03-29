import uuid
from django.db import models
from django.conf import settings

class Fund(models.Model):
    """
    Represents a private equity or venture capital fund.
    Tracks core identification, creator, and status.
    """
    STATUS_CHOICES = [
        ("ESTABLISHED", "Active (Established)"),
        ("FUTURE", "Active (Future)"),
        ("DEACTIVATED", "Deactivated"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="funds_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="FUTURE", 
        db_index=True
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.name

class FundLog(models.Model):
    """
    Audit log specifically for fund-related events.
    Records actions like creation, updates, and role assignments.
    """
    ACTION_CHOICES = [
        ("FUND_CREATED", "Fund Created"),
        ("FUND_STATUS_UPDATED", "Fund Status Updated"),
        ("FUND_INFO_UPDATED", "Fund Information Updated"),
        ("FUND_INFO_UPDATE_FAILED", "Fund Information Update Failed"),
        ("MODEL_INPUTS_UPDATED", "Model Inputs Updated"),
        ("DEAL_CREATED", "Deal Created"),
        ("DEAL_UPDATED", "Deal Updated"),
        ("DEAL_DELETED", "Deal Deleted"),
        ("CURRENT_DEAL_CREATED", "Current Deal Created"),
        ("CURRENT_DEAL_UPDATED", "Current Deal Updated"),
        ("CURRENT_DEAL_DELETED", "Current Deal Deleted"),
        ("SC_MEMBER_ASSIGNED", "SC Member Assigned"),
        ("INVESTOR_ASSIGNED", "Investor Assigned"),
        ("ROLE_REMOVED", "Role Removed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fund_actions"
    )
    
    target_fund = models.ForeignKey(
        Fund,
        on_delete=models.CASCADE,
        related_name="logs"
    )
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    success = models.BooleanField(default=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.target_fund.name} by {self.actor}"


class ModelInput(models.Model):
    """
    Stores financial modeling parameters for a specific fund.
    Used for calculating metrics like average ticket and investor counts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.OneToOneField(Fund, on_delete=models.CASCADE, related_name="model_inputs")
    
    # Financial Inputs
    target_fund_size = models.DecimalField(max_digits=20, decimal_places=2, default=100000000.00)
    inception_year = models.PositiveIntegerField(default=2024)
    fund_life = models.PositiveIntegerField(default=10)
    investment_period = models.PositiveIntegerField(default=5)
    exit_horizon = models.PositiveIntegerField(default=5)
    
    # Ticket Inputs
    min_investor_ticket = models.DecimalField(max_digits=20, decimal_places=2, default=1000000.00)
    max_investor_ticket = models.DecimalField(max_digits=20, decimal_places=2, default=5000000.00)
    
    # Fees & Returns
    lock_up_period = models.PositiveIntegerField(default=7)
    preferred_return = models.DecimalField(max_digits=5, decimal_places=2, default=8.00)
    management_fee = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    admin_cost = models.DecimalField(max_digits=5, decimal_places=2, default=0.50)
    
    # Tiers & Carry
    least_expected_moic_tier_1 = models.DecimalField(max_digits=5, decimal_places=2, default=1.50)
    least_expected_moic_tier_2 = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    tier_1_carry = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    tier_2_carry = models.DecimalField(max_digits=5, decimal_places=2, default=25.00)
    tier_3_carry = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Model Inputs for {self.fund.name}"


class InvestmentDeal(models.Model):
    """
    Represents an individual investment made by a fund (Deal Prognosis).
    Tracks company details, financial entry/exit parameters, and scenarios.
    """
    SCENARIO_CHOICES = [
        ("BASE", "Base"),
        ("DOWNSIDE", "Downside"),
        ("UPSIDE", "Upside"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="deals")
    
    # Basic Company Info
    company_name = models.CharField(max_length=255)
    company_type = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    
    # Investment Timing
    entry_year = models.PositiveIntegerField(default=2024)
    exit_year = models.PositiveIntegerField(default=2029)
    
    # Financial Inputs
    amount_invested = models.DecimalField(max_digits=20, decimal_places=2)
    entry_valuation = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Scenario Factors (Multiples)
    base_factor = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    downside_factor = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    upside_factor = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    
    selected_scenario = models.CharField(
        max_length=10, 
        choices=SCENARIO_CHOICES, 
        default="BASE"
    )
    
    expected_number_of_rounds = models.PositiveIntegerField(default=0)
    
    # Pro Rata Logic
    is_pro_rata = models.BooleanField(default=False)
    pro_rata_rights = models.BooleanField(default=False)
    parent_deal = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='pro_rata_deals'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-entry_year", "company_name"]

    def __str__(self):
        return f"{self.company_name} ({self.fund.name})"

class CurrentDeal(models.Model):
    """
    Represents an investment deal already made by the fund.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="current_deals")
    
    # Basic Company Info
    company_name = models.CharField(max_length=255)
    company_type = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    
    # Investment Timing
    entry_year = models.PositiveIntegerField(default=2024)
    latest_valuation_year = models.PositiveIntegerField(default=2024)
    
    # Financial Inputs
    amount_invested = models.DecimalField(max_digits=20, decimal_places=2)
    entry_valuation = models.DecimalField(max_digits=20, decimal_places=2)
    latest_valuation = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Pro Rata Logic
    is_pro_rata = models.BooleanField(default=False)
    pro_rata_rights = models.BooleanField(default=False)
    parent_deal = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='pro_rata_deals'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-entry_year", "company_name"]

    def __str__(self):
        return f"{self.company_name} (Current) - {self.fund.name}"

class InvestmentRound(models.Model):
    """
    Represents an investment round for a company in a fund.
    Used to track dilution and pro rata exercises.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="investment_rounds")
    company_name = models.CharField(max_length=255)
    
    year = models.PositiveIntegerField()
    pre_money_valuation = models.DecimalField(max_digits=20, decimal_places=2)
    new_money_raised = models.DecimalField(max_digits=20, decimal_places=2)
    target_valuation = models.DecimalField(max_digits=20, decimal_places=2) # Post-round (pre + new_money)
    
    exercise_pro_rata = models.BooleanField(default=False)
    amount_invested = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    
    associated_deal = models.OneToOneField(
        'CurrentDeal', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='investment_round'
    )
    
    new_ownership_percentage = models.DecimalField(max_digits=10, decimal_places=4)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["year", "created_at"]

    def __str__(self):
        return f"Round {self.year} for {self.company_name} ({self.fund.name})"

    @staticmethod
    def recalculate_for_company(fund, company_name):
        """
        Recalculates new_ownership_percentage for all rounds of a company sequentially.
        Updates based on the main deal's initial ownership and subsequent rounds.
        """
        rounds = InvestmentRound.objects.filter(fund=fund, company_name=company_name).order_by('year', 'created_at')
        main_deal = CurrentDeal.objects.filter(fund=fund, company_name=company_name, is_pro_rata=False).first()
        if not main_deal:
            return
            
        # Initial ownership from main deal
        denom = float(main_deal.amount_invested) + float(main_deal.entry_valuation)
        if denom == 0:
            current_ownership = 0.0
        else:
            current_ownership = (float(main_deal.amount_invested) / denom) * 100.0
        
        for round_obj in rounds:
            pre_money = float(round_obj.pre_money_valuation)
            new_money = float(round_obj.new_money_raised)
            post_money = pre_money + new_money
            if post_money == 0:
                continue
            
            # Amount invested in this round by our fund (pro-rata exercise)
            amt_invested = float(round_obj.amount_invested)
            
            # Formula: ((currentOwnership/100 * preMoney) + amt_invested) / postMoney * 100
            current_ownership = ((current_ownership / 100.0 * pre_money) + amt_invested) / post_money * 100.0
            
            # Use update to avoid triggering signals recursively if any
            InvestmentRound.objects.filter(id=round_obj.id).update(new_ownership_percentage=current_ownership)

