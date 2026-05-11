from decimal import Decimal
from ..models import Property, OffPlanDetails, OffPlanMilestone, RealEstatePortfolio
from ..utils.xirr import xirr

class OffPlanSelectors:
    @staticmethod
    def get_off_plan_data_for_portfolio(portfolio: RealEstatePortfolio):
        """
        Retrieves all off-plan properties with their details and calculated metrics.
        """
        properties = portfolio.properties.filter(status="OFF_PLAN").select_related('off_plan_details', 'portfolio__assumptions')
        
        results = []
        for prop in properties:
            results.append(OffPlanSelectors.calculate_off_plan_metrics(prop))
        
        return results

    @staticmethod
    def calculate_off_plan_metrics(prop: Property):
        """
        Calculates construction-related metrics for a single off-plan property.
        """
        from ..services.off_plan_service import OffPlanService
        details = OffPlanService.ensure_off_plan_details(prop)
        
        purchase_price = prop.purchase_price
        appreciation_rate = details.appreciation_rate_at_completion / Decimal("100")
        
        value_at_completion = purchase_price * (Decimal("1") + appreciation_rate)
        
        return {
            "property_id": prop.id,
            "property_name": prop.name,
            "purchase_price": purchase_price,
            "construction_start": details.construction_start_date,
            "expected_completion": details.expected_completion_date,
            "appreciation_rate": details.appreciation_rate_at_completion,
            "value_at_completion": value_at_completion,
            "details_id": details.id
        }

    @staticmethod
    def get_payment_schedule(prop: Property):
        """
        Retrieves and calculates the payment schedule for an off-plan property.
        """
        from ..services.off_plan_service import OffPlanService
        details = OffPlanService.ensure_off_plan_details(prop)
        assumptions = prop.portfolio.assumptions
        selling_fee_pct = assumptions.selling_fee_percentage / Decimal("100")
        
        milestones = prop.milestones.all().order_by('date')
        
        purchase_price = prop.purchase_price
        appreciation_rate = details.appreciation_rate_at_completion / Decimal("100")
        value_at_completion = purchase_price * (Decimal("1") + appreciation_rate)
        
        schedule = []
        cumulative_deployed = Decimal("0.00")
        cashflows_for_xirr = []
        
        for m in milestones:
            if m.milestone_name == "Sale at Completion":
                # Final inflow
                cash_flow = value_at_completion * (Decimal("1") - selling_fee_pct)
                date = details.expected_completion_date # Use expected completion date for Sale
            else:
                # Outflow based on percentage of price
                cash_flow = -(purchase_price * (m.percentage_of_price / Decimal("100")))
                date = m.date
                cumulative_deployed += abs(cash_flow)
            
            schedule.append({
                "id": m.id,
                "milestone": m.milestone_name,
                "date": date,
                "percentage": m.percentage_of_price,
                "cash_flow": cash_flow,
                "cumulative_deployed": cumulative_deployed
            })
            
            cashflows_for_xirr.append((date, float(cash_flow)))
            
        # ROI Metrics
        property_xirr = xirr(cashflows_for_xirr)
        
        total_inflows = sum(float(cf[1]) for cf in cashflows_for_xirr if cf[1] > 0)
        total_outflows = sum(abs(float(cf[1])) for cf in cashflows_for_xirr if cf[1] < 0)
        total_expected_profit = total_inflows - total_outflows
        
        return {
            "schedule": schedule,
            "metrics": {
                "xirr": round(property_xirr * 100, 2),
                "total_expected_profit": round(total_expected_profit, 2)
            }
        }
