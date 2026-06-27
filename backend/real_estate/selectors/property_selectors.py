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
    def get_properties_for_portfolio(portfolio: RealEstatePortfolio, reference_date=None, properties=None) -> list:
        """
        Retrieves all properties for a portfolio that were active at the reference_date.
        """
        if reference_date is None:
            reference_date = timezone.now().date()
        
        if properties is None:
            # Include all properties purchased before or on the reference date
            properties = portfolio.properties.filter(purchase_date__lte=reference_date).select_related(
                'portfolio__assumptions', 
                'sale',
                'usufruct_details'
            )
        
        results = []
        for prop in properties:
            if prop.purchase_date > reference_date:
                continue
            # Exclude if it was sold before the reference date
            if hasattr(prop, 'sale') and prop.sale and prop.sale.sale_date < reference_date:
                continue
                
            results.append(PropertySelector.calculate_metrics(prop, reference_date))
        
        return results

    @staticmethod
    def calculate_metrics(prop: Property, reference_date) -> dict:
        """
        Performs the financial calculations for a single property.
        """
        assumptions = prop.portfolio.assumptions
        is_usufruct = prop.status == "USUFRUCT"
        
        # Years Held
        years_held = PropertyDataCalc.years_held(prop.purchase_date, reference_date)
        
        if is_usufruct:
            u_details = getattr(prop, 'usufruct_details', None)
            if u_details:
                is_first_year = reference_date.year == prop.purchase_date.year
                
                annual_rent = PropertyDataCalc.usufruct_annual_rent(
                    u_details.inflow_monthly_rent,
                    u_details.inflow_rent_appreciation_percentage,
                    years_held,
                    is_first_year=is_first_year
                )
                effective_rent = PropertyDataCalc.usufruct_effective_rent(annual_rent, prop.vacancy_rate_percentage)
                noi = PropertyDataCalc.usufruct_noi(
                    effective_rent,
                    u_details.outflow_monthly_rent,
                    u_details.outflow_rent_appreciation_percentage,
                    u_details.annual_ops_cost,
                    u_details.insurance_cost,
                    years_held,
                    is_first_year=is_first_year
                )
                gross_yield = PropertyDataCalc.usufruct_gross_yield(effective_rent, u_details.prep_cost)
                net_yield = PropertyDataCalc.usufruct_net_yield(noi, u_details.prep_cost)
                
                return {
                    "property": prop,
                    "metrics": {
                        "is_usufruct": True,
                        "annual_rent": annual_rent,
                        "effective_rent": effective_rent,
                        "noi": noi,
                        "gross_yield": gross_yield,
                        "net_yield": net_yield,
                        "insurance_cost": u_details.insurance_cost,
                        "prep_cost": u_details.prep_cost,
                        "outflow_monthly_rent": u_details.outflow_monthly_rent,
                        "annual_ops_cost": u_details.annual_ops_cost,
                        "inflow_monthly_rent": u_details.inflow_monthly_rent,
                        "outflow_rent_appreciation_percentage": u_details.outflow_rent_appreciation_percentage,
                        "inflow_rent_appreciation_percentage": u_details.inflow_rent_appreciation_percentage,
                        "ui_hint": "This property does not contribute to the total asset value of the portfolio.",
                        # Fill standard metrics with 0 or None for compatibility
                        "acq_fee_amount": Decimal('0.00'),
                        "total_cost_basis": u_details.prep_cost,
                        "years_held": round(years_held, 2),
                        "current_market_value": Decimal('0.00'),
                        "unrealized_gain": Decimal('0.00'),
                        "cost_per_sqm": PropertyDataCalc.cost_per_sqm(u_details.prep_cost, prop.size),
                        "management_fees": Decimal('0.00'),
                        "maintenance_fees": Decimal('0.00'),
                        "total_operational_expenses": (u_details.outflow_monthly_rent * 12) + u_details.annual_ops_cost + u_details.insurance_cost,
                    }
                }
            else:
                # Fallback if usufruct_details missing
                return {
                    "property": prop,
                    "metrics": {"is_usufruct": True, "error": "Missing usufruct details"}
                }

        # Derived Metrics
        acq_fee_amount = PropertyDataCalc.acq_fee(prop.purchase_price or Decimal('0'), prop.acq_fee_percentage)
        total_cost_basis = PropertyDataCalc.total_cost_basis(prop.purchase_price or Decimal('0'), prop.acq_fee_percentage)
        
        # Current Market Value
        current_market_value = PropertyDataCalc.market_value(
            prop.purchase_price or Decimal('0'), 
            prop.appreciation_rate_percentage, 
            years_held
        )
        unrealized_gain = current_market_value - total_cost_basis
        
        # Handle Off-Plan logic for rent
        is_held = prop.status == "HELD"
        
        effective_rent = PropertyDataCalc.effective_rent(
            prop.monthly_rent or Decimal('0'),
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
        
        gross_yield = PropertyDataCalc.gross_yield(effective_rent, prop.purchase_price or Decimal('0'))
        net_yield = PropertyDataCalc.net_yield(noi, current_market_value)
        cost_per_sqm = PropertyDataCalc.cost_per_sqm(prop.purchase_price or Decimal('0'), prop.size)

        return {
            "property": prop,
            "metrics": {
                "acq_fee_amount": acq_fee_amount,
                "total_cost_basis": total_cost_basis,
                "years_held": round(years_held, 2),
                "current_market_value": current_market_value,
                "unrealized_gain": unrealized_gain,
                "annual_rent": ((prop.monthly_rent or Decimal('0')) * Decimal('12')).quantize(Decimal('0.01')),
                "effective_rent": effective_rent,
                "management_fees": PropertyDataCalc.management_fees(effective_rent, assumptions.property_mgmt_fee_percentage),
                "maintenance_fees": PropertyDataCalc.maintenance_fees(current_market_value, assumptions.maintenance_percentage_of_value),
                "total_operational_expenses": total_operational_expenses,
                "noi": noi,
                "gross_yield": gross_yield,
                "net_yield": net_yield,
                "cost_per_sqm": cost_per_sqm,
                "is_usufruct": False,
                "ui_hint": None,
            }
        }
