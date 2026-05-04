import uuid
from django.db import models
from django.conf import settings
from .utils.db import locked_get_or_create

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

    TAG_CHOICES = [
        ("BIC", "BIC"),
        ("VC", "VC"),
        ("VS", "VS"),
        ("AIG", "AIG"),
        ("SF", "SF"),
        ("REAL_ESTATE", "Real estate"),
    ]

    FOCUS_CHOICES = [
        ("GROWTH", "Growth Focused"),
        ("YIELD", "Yield Focused"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    
    tag = models.CharField(
        max_length=20,
        choices=TAG_CHOICES,
        default="VC",
        db_index=True
    )

    sharia_compliant = models.BooleanField(default=False)
    region = models.CharField(max_length=255, blank=True)
    focus = models.CharField(
        max_length=20, 
        choices=FOCUS_CHOICES, 
        blank=True,
        null=True
    )
    
    overview = models.TextField(blank=True)
    strategy = models.TextField(blank=True)
    structure = models.TextField(blank=True)
    strategy_and_fund_lifecycle = models.TextField(blank=True)
    reasons_to_invest = models.JSONField(default=list, blank=True)

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
    total_units = models.DecimalField(max_digits=30, decimal_places=4, default=0.0000)

    # New Target & Planning Fields
    target_appreciation = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    target_yield = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    target_capital_allocation = models.JSONField(default=list, blank=True)
    investment_composition = models.JSONField(
        default=list, 
        blank=True,
        help_text="Customizable investment composition (e.g. Ventures vs SMEs)"
    )
    risk_measures = models.JSONField(
        default=list, 
        blank=True,
        help_text="Structured list of risk measures with title and description"
    )
    report_config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["status"]),
            models.Index(fields=["tag"]),
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
        ("INVESTOR_ACTION_CREATED", "Investor Action Created"),
        ("INVESTOR_ACTION_UPDATED", "Investor Action Updated"),
        ("INVESTOR_ACTION_DELETED", "Investor Action Deleted"),
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
    
    # Portfolio Outcomes & Rates
    failure_rate = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    break_even_rate = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)
    high_growth_rate = models.DecimalField(max_digits=5, decimal_places=2, default=50.00)
    dilution_rate = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    
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

    INVESTMENT_TYPE_CHOICES = [
        ("EQUITY", "Equity Financing"),
        ("VENTURE_DEBT", "Venture Debt"),
        ("VENTURE_DEBT_ROYALTIES", "Venture Debt with Royalties (Shariah Compliant)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="deals")
    
    # Basic Company Info
    company_name = models.CharField(max_length=255)
    company_type = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    investment_type = models.CharField(
        max_length=50, 
        choices=INVESTMENT_TYPE_CHOICES, 
        default="EQUITY"
    )
    
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
    expected_exit_multiple = models.DecimalField(max_digits=10, decimal_places=2, default=5.00)
    
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

class RiskAssessment(models.Model):
    """
    Stores risk assessment metrics for a portfolio company within a fund.
    Used for the Risk Assessment Tab.
    """
    STATUS_CHOICES = [
        ('MONETIZE', 'Monetize'),
        ('ON_TRACK', 'On-Track'),
        ('RESTRUCTURE', 'Restructure'),
        ('SHUTDOWN', 'Shutdown'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="risk_assessments")
    company_name = models.CharField(max_length=255)
    
    execution_capacity_score = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)
    market_validation_score = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ON_TRACK')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('fund', 'company_name')
        verbose_name = "Risk Assessment"
        verbose_name_plural = "Risk Assessments"

    def __str__(self):
        return f"Risk Assessment: {self.company_name} ({self.fund.name})"

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

class PossibleCapitalSource(models.Model):
    """
    Represents a potential capital source for the fund.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(
        Fund,
        on_delete=models.CASCADE,
        related_name="possible_capital_sources"
    )
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=30, decimal_places=2)
    year = models.PositiveIntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["year", "created_at"]
        indexes = [
            models.Index(fields=["fund", "year"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.fund.name} ({self.year})"

class InvestorAction(models.Model):
    """
    Represents an action associated with an investor (Primary/Secondary Investment or Secondary Exit).
    """
    TYPE_CHOICES = [
        ("PRIMARY_INVESTMENT", "Primary Investment"),
        ("SECONDARY_INVESTMENT", "Secondary Investment"),
        ("SECONDARY_EXIT", "Secondary Exit"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="investor_actions"
    )
    fund = models.ForeignKey(
        Fund,
        on_delete=models.CASCADE,
        related_name="investor_actions"
    )
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    year = models.PositiveIntegerField()
    
    # Amount for Primary/Secondary Investment or Price Sold At for Secondary Exit
    amount = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)
    
    # For Secondary Exit
    percentage_sold = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    
    investor_selling = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="investor_sales"
    )
    investor_sold_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="investor_purchases"
    )
    
    # Stores units involved in the action
    units = models.DecimalField(max_digits=30, decimal_places=4, default=0.0000)
    
    # Kept for backward compatibility if needed, though replaced by 'amount' logic
    original_value = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)
    exit_value = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["year", "created_at"]
        indexes = [
            models.Index(fields=["investor", "fund"]),
            models.Index(fields=["year"]),
        ]

    def __str__(self):
        return f"{self.type} - {self.investor.email} - {self.fund.name} ({self.year})"

class CurrentInvestorStats(models.Model):
    """
    Represents the current amount an investor invested into the fund after removing the cost basis for units sold
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="current_investor_stats"
    )
    fund = models.ForeignKey(
        Fund,
        on_delete=models.CASCADE,
        related_name="current_investor_stats"
    )
    
    # Invested amount for the investor in the related fund (BALANCE)
    amount_invested = models.DecimalField(max_digits=30, decimal_places=2, default=0.00)
    # Total capital injected by the investor in the related fund (CAPITAL DEPLOYED)
    capital_deployed = models.DecimalField(max_digits=30, decimal_places=2, default=0.00)
    # Realized gain from secondary exits the investor performed in the related fund
    realized_gain = models.DecimalField(max_digits=30, decimal_places=2, default=0.00)
    # Current number of units owned by the investor in the fund
    units = models.DecimalField(max_digits=30, decimal_places=4, default=0.0000)

    class Meta:
        ordering = ["amount_invested"]
        indexes = [
            models.Index(fields=["investor", "fund"]),
        ]

    def __str__(self):
        return f"{self.investor.email} - {self.fund.name} - ({self.amount_invested})"
    
    @staticmethod
    def recalculate_investor_stats(action, investor, fund, signal):
        """A method to be used whenever investor actions are added or deleted"""
        relation, created = locked_get_or_create(CurrentInvestorStats,investor = investor, fund = fund)
        print(created)
        if signal == "save":  
            if action.type == "SECONDARY_EXIT":
                relation.amount_invested = float(relation.amount_invested) * (1 - (float(action.units) / float(relation.units)))
                relation.units = float(relation.units) - float(action.units)
                relation.realized_gain = float(relation.realized_gain) + float(action.amount) - (float(relation.amount_invested) / float(relation.units) * float(action.units))
            else: 
                relation.amount_invested = float(relation.amount_invested) + float(action.amount)
                relation.capital_deployed = float(relation.capital_deployed) + float(action.amount)
                relation.units = float(relation.units) + float(action.units)
        elif signal == "delete":
            if action.type == "SECONDARY_EXIT":
                relation.amount_invested = float(relation.amount_invested) / (1 - (float(action.units) / float(relation.units)))
                relation.units = float(relation.units) -  float(action.units)
                relation.realized_gain = float(relation.realized_gain) - float(action.amount) + (float(relation.amount_invested) / float(relation.units) * float(action.units))
            else:
                relation.amount_invested = float(relation.amount_invested) - float(action.amount)
                relation.units = float(relation.units) - float(action.units)

        relation.save()

class Report(models.Model):
    """
    Model for dynamic fund reports. Stores configuration and metadata
    about generated static reports.
    """
    REPORT_TYPE_CHOICES = [
        ("DYNAMIC", "Dynamic Fund Report"),
        ("CAPITAL_CALL", "Capital Call Report"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='reports')
    
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        default="DYNAMIC",
        db_index=True
    )

    config_json = models.JSONField(help_text="Metrics selection, chart types, etc.")
    
    status = models.CharField(
        max_length=20,
        choices=[
            ("ACTIVE", "Active"), 
            ("INACTIVE", "Inactive"), 
            ("GENERATING", "Generating"),
            ("FAILED", "Failed")
        ],
        default="INACTIVE",
        db_index=True
    )
    
    static_url = models.URLField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.fund.name}"

class InvestorRequest(models.Model):
    REQUEST_TYPE_CHOICES = [
        ('INVESTMENT', 'Investment'),
        ('LIQUIDATION', 'Liquidation'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="investor_requests"
    )
    fund = models.ForeignKey(
        Fund, 
        on_delete=models.CASCADE, 
        related_name="investor_requests"
    )
    type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Investment Fields
    requested_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    
    # Liquidation Fields
    liquidation_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    units_to_sell = models.DecimalField(max_digits=30, decimal_places=4, null=True, blank=True)
    expected_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} Req - {self.user.email} - {self.fund.name} ({self.status})"
