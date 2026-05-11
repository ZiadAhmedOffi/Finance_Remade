import uuid
from django.db import models
from django.conf import settings

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

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Real Estate Portfolio"
        verbose_name_plural = "Real Estate Portfolios"

    def __str__(self):
        return self.name

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
    ]

    TYPE_CHOICES = [
        ("RESIDENTIAL", "Residential"),
        ("COMMERCIAL", "Commercial"),
        ("INDUSTRIAL", "Industrial"),
        ("RETAIL", "Retail"),
        ("MIXED_USE", "Mixed-Use"),
    ]

    FINANCING_CHOICES = [
        ("ALL_CASH", "All Cash"),
        ("MORTGAGED", "Mortgaged"),
        ("MEZZANINE", "Mezzanine"),
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

    # Financial Inputs
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=15, decimal_places=2)
    monthly_rent = models.DecimalField(max_digits=15, decimal_places=2)
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
