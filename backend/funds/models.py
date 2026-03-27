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
    
    # Pro Rata Logic
    is_pro_rata = models.BooleanField(default=False)
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
