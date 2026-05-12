from decimal import Decimal
from django.utils import timezone
from django.db.models import QuerySet
from ..models import Property, RealEstatePortfolio
from ..calculation import PropertyDataCalc

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
        
        # Years Held
        years_held = PropertyDataCalc.years_held(prop.purchase_date, reference_date)
        
        # Derived Metrics
        acq_fee_amount = PropertyDataCalc.acq_fee(prop.purchase_price, prop.acq_fee_percentage)
        total_cost_basis = PropertyDataCalc.total_cost_basis(prop.purchase_price, prop.acq_fee_percentage)
        
        # Current Market Value
        current_market_value = PropertyDataCalc.market_value(
            prop.purchase_price, 
            prop.appreciation_rate_percentage, 
            years_held
        )
        
        unrealized_gain = current_market_value - total_cost_basis
        
        # Handle Off-Plan logic for rent
        is_held = prop.status == "HELD"
        
        effective_rent = PropertyDataCalc.effective_rent(
            prop.monthly_rent,
            prop.vacancy_rate_percentage,
            years_held,
            Decimal('0') # No growth for current metrics
        ) if is_held else Decimal('0.00')
        
        if prop.status == "OFF_PLAN":
            total_operational_expenses = Decimal('0.00')
            noi = Decimal('0.00')
        else:
            total_operational_expenses = PropertyDataCalc.total_operational_expenses(
                effective_rent,
                current_market_value,
                assumptions.property_mgmt_fee_percentage,
                assumptions.maintenance_percentage_of_value,
                Decimal(str(prop.other_operational_expenses))
            )
            noi = PropertyDataCalc.noi(effective_rent, total_operational_expenses)
        
        gross_yield = PropertyDataCalc.gross_yield(effective_rent, prop.purchase_price)
        net_yield = PropertyDataCalc.net_yield(noi, current_market_value)

        return {
            "property": prop,
            "metrics": {
                "acq_fee_amount": acq_fee_amount,
                "total_cost_basis": total_cost_basis,
                "years_held": round(years_held, 2),
                "current_market_value": current_market_value,
                "unrealized_gain": unrealized_gain,
                "annual_rent": (prop.monthly_rent * Decimal('12')).quantize(Decimal('0.01')),
                "effective_rent": effective_rent,
                "management_fees": PropertyDataCalc.management_fees(effective_rent, assumptions.property_mgmt_fee_percentage),
                "maintenance_fees": PropertyDataCalc.maintenance_fees(current_market_value, assumptions.maintenance_percentage_of_value),
                "total_operational_expenses": total_operational_expenses,
                "noi": noi,
                "gross_yield": gross_yield,
                "net_yield": net_yield,
            }
        }
