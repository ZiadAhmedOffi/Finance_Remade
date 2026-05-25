import uuid
from django.db import models
from django.conf import settings
from decimal import Decimal

class RealEstatePortfolio(models.Model):
    """
    Represents a Real Estate Portfolio within the application.
    Independent of the equity-based Fund model.
    """
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("DEACTIVATED", "Deactivated"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    region = models.CharField(max_length=255, blank=True)
    
    # New: Link to Jurisdiction
    jurisdiction = models.ForeignKey(
        'Jurisdiction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="portfolios"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="re_portfolios_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="ACTIVE", 
        db_index=True
    )
    total_units = models.DecimalField(max_digits=30, decimal_places=4, default=0.0000)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Real Estate Portfolio"
        verbose_name_plural = "Real Estate Portfolios"

    def __str__(self):
        return self.name

class Jurisdiction(models.Model):
    """
    Represents a fiscal territory with specific tax rules.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    currency = models.CharField(max_length=10, default="USD")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Jurisdiction"
        verbose_name_plural = "Jurisdictions"

    def __str__(self):
        return self.name

class TaxRule(models.Model):
    """
    Defines a specific tax logic within a Jurisdiction.
    """
    EVENT_TYPE_CHOICES = [
        ("ACQUISITION", "Acquisition"),
        ("OWNERSHIP", "Ownership"),
        ("INCOME", "Income"),
        ("DISPOSAL", "Disposal"),
        ("FINANCING", "Financing"),
    ]

    TRIGGER_CHOICES = [
        ("CONTRACT_SIGNING", "Contract Signing"),
        ("ON_PAYMENT", "On Payment"),
        ("HANDOVER", "Handover"),
        ("ANNUAL", "Annual"),
        ("DISPOSAL", "Disposal"),
    ]

    TAX_BASE_CHOICES = [
        ("MARKET_VALUE", "Market Value"),
        ("ASSESSED_VALUE", "Assessed Value"),
        ("NET_INCOME", "Net Income"),
        ("LOAN_AMOUNT", "Loan Amount"),
        ("FIXED", "Fixed Amount"),
    ]

    RESPONSIBLE_PARTY_CHOICES = [
        ("BARE_OWNER", "Bare Owner"),
        ("USUFRUCT_HOLDER", "Usufruct Holder"),
        ("BOTH", "Both / Not Applicable"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    jurisdiction = models.ForeignKey(
        Jurisdiction,
        on_delete=models.CASCADE,
        related_name="rules"
    )

    name = models.CharField(max_length=255)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES)
    tax_base = models.CharField(max_length=20, choices=TAX_BASE_CHOICES)
    
    # Financial Parameters
    rate = models.DecimalField(max_digits=10, decimal_places=4, help_text="Tax rate as a decimal (e.g. 0.05 for 5%)")
    valuation_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=1.00, help_text="Ratio of market value for assessed value")
    revaluation_freq = models.PositiveIntegerField(default=1, help_text="How often the assessment updates in years")
    deductibility_cap = models.DecimalField(max_digits=5, decimal_places=2, default=1.00, help_text="Cap on interest/expense deductions")
    lcf_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Loss Carry Forward limit in years")
    
    responsible_party = models.CharField(
        max_length=20, 
        choices=RESPONSIBLE_PARTY_CHOICES, 
        default="BOTH"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tax Rule"
        verbose_name_plural = "Tax Rules"

    def __str__(self):
        return f"{self.jurisdiction.name} - {self.name} ({self.event_type})"

class RealEstateAssumptions(models.Model):
    """
    Stores financial assumptions for a Real Estate Portfolio.
    """
    SCENARIO_CHOICES = [
        ("BASE", "Base"),
        ("BULL", "Bull"),
        ("BEAR", "Bear"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.OneToOneField(
        RealEstatePortfolio, 
        on_delete=models.CASCADE, 
        related_name="assumptions"
    )

    # General Inputs
    inception_date = models.DateField()
    forecast_horizon = models.PositiveIntegerField(help_text="In years", default=10)

    # Default Rates
    default_appreciation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3.00)
    default_rental_growth_rate = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    default_vacancy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    default_discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=8.00)
    default_depreciation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=2.00, help_text="Annual depreciation rate as percentage")

    # Fees and Costs
    acquisition_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    property_mgmt_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    maintenance_percentage_of_value = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    selling_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)

    # Scenario Selection
    active_scenario = models.CharField(
        max_length=10, 
        choices=SCENARIO_CHOICES, 
        default="BASE"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Real Estate Assumptions"
        verbose_name_plural = "Real Estate Assumptions"

    def __str__(self):
        return f"Assumptions for {self.portfolio.name}"

class Property(models.Model):
    """
    Represents an individual real estate asset within a portfolio.
    Stores both inputs and snapshotted assumptions for per-property overrides.
    """
    STATUS_CHOICES = [
        ("HELD", "Held"),
        ("OFF_PLAN", "Off-Plan"),
        ("SOLD", "Sold"),
        ("USUFRUCT", "Usufruct"),
    ]

    TYPE_CHOICES = [
        ("RESIDENTIAL", "Residential"),
        ("COMMERCIAL", "Commercial"),
        ("INDUSTRIAL", "Industrial"),
        ("RETAIL", "Retail"),
        ("MIXED_USE", "Mixed-Use"),
        ("WAREHOUSE", "Warehouses"),
    ]

    FINANCING_CHOICES = [
        ("ALL_CASH", "All Cash"),
        ("MORTGAGED", "Mortgaged"),
        ("MEZZANINE", "Mezzanine"),
        ("PRIMARY_INSTALLMENTS", "Primary Sales with Installments"),
    ]

    TRANSACTION_TYPE_CHOICES = [
        ("PRIMARY", "Primary"),
        ("SECONDARY", "Secondary"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(
        RealEstatePortfolio, 
        on_delete=models.CASCADE, 
        related_name="properties"
    )

    # Basic Info
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    submarket = models.CharField(max_length=255, blank=True)
    
    # Categories
    property_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    financing_type = models.CharField(max_length=50, choices=FINANCING_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="HELD")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default="SECONDARY")

    # Financial Inputs
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    size = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Size in square meters")
    monthly_rent = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    other_operational_expenses = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        help_text="Annual expenses",
        default=0.00
    )

    # Snapshotted assumptions (Overrides)
    acq_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    appreciation_rate_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    vacancy_rate_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-purchase_date"]
        verbose_name = "Property"
        verbose_name_plural = "Properties"

    def __str__(self):
        return f"{self.name} ({self.city})"

class UsufructDetails(models.Model):
    """
    Stores specific details for Usufruct properties.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name="usufruct_details"
    )

    # New: Role for taxation allocation
    investor_role = models.CharField(
        max_length=20, 
        choices=[
            ("BARE_OWNER", "Bare Owner"),
            ("USUFRUCT_HOLDER", "Usufruct Holder"),
        ],
        default="USUFRUCT_HOLDER"
    )

    # Inputs
    insurance_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    prep_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    outflow_monthly_rent = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    annual_ops_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    inflow_monthly_rent = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    outflow_rent_appreciation_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    inflow_rent_appreciation_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Usufruct Details"
        verbose_name_plural = "Usufruct Details"

    def __str__(self):
        return f"Usufruct Details for {self.property.name}"

class FinancingEntry(models.Model):
    """
    Stores financing details for a specific property.
    One-to-one relationship with Property.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name="financing"
    )

    loan_amount = models.DecimalField(max_digits=15, decimal_places=2)
    base_interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Base interest rate as a percentage"
    )
    tenor = models.PositiveIntegerField(help_text="Tenor in years")
    payments_per_year = models.PositiveIntegerField(default=12)
    loan_start_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Financing Entry"
        verbose_name_plural = "Financing Entries"

    def __str__(self):
        return f"Financing for {self.property.name}"

class InstallmentEntry(models.Model):
    """
    Stores installment details for a specific property (Primary Sales with Installments).
    One-to-one relationship with Property.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name="installment"
    )

    down_payment = models.DecimalField(max_digits=15, decimal_places=2)
    tenor = models.PositiveIntegerField(help_text="Tenor in years")
    payments_per_year = models.PositiveIntegerField(default=12)
    start_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Installment Entry"
        verbose_name_plural = "Installment Entries"

    def __str__(self):
        return f"Installments for {self.property.name}"

class OffPlanDetails(models.Model):
    """
    Stores specific construction and appreciation details for off-plan properties.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name="off_plan_details"
    )

    construction_start_date = models.DateField()
    expected_completion_date = models.DateField()
    appreciation_rate_at_completion = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=25.00,
        help_text="Expected appreciation percentage at completion"
    )
    sale_at_completion = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Off-Plan Details"
        verbose_name_plural = "Off-Plan Details"

    def __str__(self):
        return f"Off-Plan Details for {self.property.name}"

class OffPlanMilestone(models.Model):
    """
    Represents a payment milestone for an off-plan property.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="milestones"
    )

    milestone_name = models.CharField(max_length=255)
    date = models.DateField()
    percentage_of_price = models.DecimalField(max_digits=5, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date"]
        verbose_name = "Off-Plan Milestone"
        verbose_name_plural = "Off-Plan Milestones"

    def __str__(self):
        return f"{self.milestone_name} for {self.property.name}"

class PropertySale(models.Model):
    """
    Represents the sale or disposal of a property.
    One-to-one relationship with Property.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name="sale"
    )

    sale_date = models.DateField()
    selling_price = models.DecimalField(max_digits=15, decimal_places=2)
    selling_fee_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Selling fee as a percentage of selling price"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Property Sale"
        verbose_name_plural = "Property Sales"
        ordering = ["-sale_date"]

    def __str__(self):
        return f"Sale of {self.property.name} on {self.sale_date}"

class RealEstatePossibleCapitalSource(models.Model):
    """
    Represents a potential capital source for the real estate portfolio.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(
        RealEstatePortfolio,
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
            models.Index(fields=["portfolio", "year"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.portfolio.name} ({self.year})"

class RealEstateInvestorAction(models.Model):
    """
    Represents an action associated with an investor in a real estate portfolio.
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
        related_name="re_investor_actions"
    )
    portfolio = models.ForeignKey(
        RealEstatePortfolio,
        on_delete=models.CASCADE,
        related_name="investor_actions"
    )
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    year = models.PositiveIntegerField()
    
    amount = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)
    
    # For Secondary Exit
    percentage_sold = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    
    investor_selling = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="re_investor_sales"
    )
    investor_sold_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="re_investor_purchases"
    )
    
    units = models.DecimalField(max_digits=30, decimal_places=4, default=0.0000)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["year", "created_at"]
        indexes = [
            models.Index(fields=["investor", "portfolio"]),
            models.Index(fields=["year"]),
        ]

    def __str__(self):
        return f"{self.type} - {self.investor.email} - {self.portfolio.name} ({self.year})"

class RealEstateInvestorStats(models.Model):
    """
    Represents the current amount an investor invested into the real estate portfolio.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="re_investor_stats"
    )
    portfolio = models.ForeignKey(
        RealEstatePortfolio,
        on_delete=models.CASCADE,
        related_name="investor_stats"
    )
    
    amount_invested = models.DecimalField(max_digits=30, decimal_places=2, default=0.00)
    capital_deployed = models.DecimalField(max_digits=30, decimal_places=2, default=0.00)
    realized_gain = models.DecimalField(max_digits=30, decimal_places=2, default=0.00)
    units = models.DecimalField(max_digits=30, decimal_places=4, default=0.0000)

    class Meta:
        ordering = ["amount_invested"]
        unique_together = ["investor", "portfolio"]
        indexes = [
            models.Index(fields=["investor", "portfolio"]),
        ]

    def __str__(self):
        return f"{self.investor.email} - {self.portfolio.name} - ({self.amount_invested})"

    @staticmethod
    def recalculate_investor_stats(investor, portfolio):
        """
        Recalculates stats from scratch based on all actions for this investor in this portfolio.
        This is more robust than incremental updates.
        """
        from .models import RealEstateInvestorAction
        actions = RealEstateInvestorAction.objects.filter(investor=investor, portfolio=portfolio).order_by('year', 'created_at')
        
        total_amount_invested = Decimal('0.00')
        total_capital_deployed = Decimal('0.00')
        total_realized_gain = Decimal('0.00')
        total_units = Decimal('0.0000')

        for action in actions:
            amount = Decimal(str(action.amount or 0))
            units = Decimal(str(action.units or 0))

            if action.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
                total_amount_invested += amount
                total_units += units
                if action.type == "PRIMARY_INVESTMENT":
                    total_capital_deployed += amount
            
            elif action.type == "SECONDARY_EXIT":
                if total_units > 0:
                    # Weighted Average Cost Basis
                    cost_basis_per_unit = total_amount_invested / total_units
                    cost_basis_of_sale = cost_basis_per_unit * units
                    
                    total_realized_gain += (amount - cost_basis_of_sale)
                    total_amount_invested -= cost_basis_of_sale
                    total_units -= units
                else:
                    # Fallback for data inconsistency
                    total_units -= units

        stats, _ = RealEstateInvestorStats.objects.get_or_create(investor=investor, portfolio=portfolio)
        stats.amount_invested = total_amount_invested
        stats.capital_deployed = total_capital_deployed
        stats.realized_gain = total_realized_gain
        stats.units = total_units
        stats.save()
