from decimal import Decimal
from django.utils import timezone
from django.db.models import QuerySet
from ..models import Property, RealEstatePortfolio

class PropertySelector:
    """
    Selector for calculating derived financial metrics for real estate properties.
    """

    @staticmethod
    def get_properties_for_portfolio(portfolio: RealEstatePortfolio, reference_date=None) -> list:
        """
        Retrieves all properties for a portfolio with calculated derived metrics.
        """
        if reference_date is None:
            reference_date = timezone.now().date()
        
        properties = portfolio.properties.exclude(status="SOLD").select_related('portfolio__assumptions')
        
        results = []
        for prop in properties:
            results.append(PropertySelector.calculate_metrics(prop, reference_date))
        
        return results

    @staticmethod
    def calculate_metrics(prop: Property, reference_date) -> dict:
        """
        Performs the financial calculations for a single property.
        """
        assumptions = prop.portfolio.assumptions
        
        # Inputs
        purchase_price = prop.purchase_price
        acq_fee_pct = prop.acq_fee_percentage / Decimal('100')
        app_rate_pct = prop.appreciation_rate_percentage / Decimal('100')
        vacancy_rate_pct = prop.vacancy_rate_percentage / Decimal('100')
        mgmt_fee_pct = assumptions.property_mgmt_fee_percentage / Decimal('100')
        maint_fee_pct = assumptions.maintenance_percentage_of_value / Decimal('100')
        
        # Derived Metrics
        acq_fee_amount = purchase_price * acq_fee_pct
        total_cost_basis = purchase_price + acq_fee_amount
        
        # Years Held
        days_held = (reference_date - prop.purchase_date).days
        years_held = Decimal(str(days_held)) / Decimal('365.25')
        
        # Current Market Value: P * (1 + r)^t
        growth_factor = float(Decimal('1') + app_rate_pct) ** float(years_held)
        current_market_value = purchase_price * Decimal(str(round(growth_factor, 10)))
        current_market_value = Decimal(str(round(current_market_value, 2)))
        
        unrealized_gain = current_market_value - total_cost_basis
        
        annual_rent = prop.monthly_rent * Decimal('12')
        
        # Handle Off-Plan logic
        is_held = prop.status == "HELD"
        
        effective_rent = annual_rent * (Decimal('1') - vacancy_rate_pct) if is_held else Decimal('0')
        
        management_fees = mgmt_fee_pct * effective_rent
        maintenance_fees = maint_fee_pct * current_market_value
        
        total_operational_expenses = management_fees + maintenance_fees + Decimal(str(prop.other_operational_expenses))
        
        noi = effective_rent - total_operational_expenses
        
        gross_yield = (effective_rent / purchase_price) if purchase_price > 0 else Decimal('0')
        net_yield = (noi / current_market_value) if current_market_value > 0 else Decimal('0')

        return {
            "property": prop,
            "metrics": {
                "acq_fee_amount": acq_fee_amount,
                "total_cost_basis": total_cost_basis,
                "years_held": round(years_held, 2),
                "current_market_value": current_market_value,
                "unrealized_gain": unrealized_gain,
                "annual_rent": annual_rent,
                "effective_rent": effective_rent,
                "management_fees": management_fees,
                "maintenance_fees": maintenance_fees,
                "total_operational_expenses": total_operational_expenses,
                "noi": noi,
                "gross_yield": round(gross_yield * Decimal('100'), 2),
                "net_yield": round(net_yield * Decimal('100'), 2),
            }
        }
