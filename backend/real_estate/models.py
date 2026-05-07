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
