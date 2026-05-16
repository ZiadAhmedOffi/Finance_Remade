from decimal import Decimal
from ..models import Property, OffPlanDetails, OffPlanMilestone, RealEstatePortfolio
from ..utils.xirr import xirr
from ..calculation import PropertyDataCalc

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
        value_at_completion = PropertyDataCalc.value_at_completion(purchase_price, details.appreciation_rate_at_completion)
        
        return {
            "property_id": prop.id,
            "property_name": prop.name,
            "purchase_price": purchase_price,
            "construction_start": details.construction_start_date,
            "expected_completion": details.expected_completion_date,
            "appreciation_rate": details.appreciation_rate_at_completion,
            "sale_at_completion": details.sale_at_completion,
            "value_at_completion": value_at_completion,
            "details_id": details.id
        }

    @staticmethod
    def get_payment_schedule(prop: Property):
        """
        Retrieves and calculates the payment schedule for an off-plan property.
        Automatically adds a 'Completion' milestone and handles 'Sale at Completion' inflow.
        """
        from ..services.off_plan_service import OffPlanService
        details = OffPlanService.ensure_off_plan_details(prop)
        assumptions = prop.portfolio.assumptions
        selling_fee_pct = assumptions.selling_fee_percentage
        
        # User defined milestones
        milestones = list(prop.milestones.all().order_by('date'))
        
        purchase_price = prop.purchase_price
        value_at_completion = PropertyDataCalc.value_at_completion(purchase_price, details.appreciation_rate_at_completion)
        
        schedule = []
        cumulative_deployed = Decimal("0.00")
        cashflows_for_xirr = []
        
        # Calculate sum of user milestones
        user_pct_sum = sum(m.percentage_of_price for m in milestones)
        completion_pct = max(Decimal("0.00"), Decimal("100.00") - user_pct_sum)
        
        # 1. Add user milestones
        for m in milestones:
            cash_flow = -(purchase_price * (m.percentage_of_price / Decimal("100")))
            cumulative_deployed += abs(cash_flow)
            
            schedule.append({
                "id": str(m.id),
                "milestone": m.milestone_name,
                "date": m.date,
                "percentage": m.percentage_of_price,
                "cash_flow": float(cash_flow),
                "cumulative_deployed": float(cumulative_deployed)
            })
            cashflows_for_xirr.append((m.date, float(cash_flow)))
        
        # 2. Add automatic Completion milestone (ALWAYS AT THE END of construction)
        comp_date = details.expected_completion_date
        comp_cf = -(purchase_price * (completion_pct / Decimal("100")))
        cumulative_deployed += abs(comp_cf)
        
        schedule.append({
            "id": "completion",
            "milestone": "Completion",
            "date": comp_date,
            "percentage": completion_pct,
            "cash_flow": float(comp_cf),
            "cumulative_deployed": float(cumulative_deployed)
        })
        cashflows_for_xirr.append((comp_date, float(comp_cf)))
        
        # 3. Add Sale at Completion if enabled
        if details.sale_at_completion:
            selling_costs = PropertyDataCalc.selling_costs(value_at_completion, selling_fee_pct)
            sale_inflow = value_at_completion - selling_costs
            
            schedule.append({
                "id": "sale",
                "milestone": "Sale at Completion",
                "date": comp_date,
                "percentage": 0,
                "cash_flow": float(sale_inflow),
                "cumulative_deployed": float(cumulative_deployed)
            })
            cashflows_for_xirr.append((comp_date, float(sale_inflow)))
        else:
            # For XIRR/Profit calculation, if NOT selling, we use the value at completion 
            # as a terminal value inflow to measure the ROI of the construction phase.
            cashflows_for_xirr.append((comp_date, float(value_at_completion)))
            
        # ROI Metrics
        # Aggregate by date before XIRR to handle multiple flows on same day
        aggregated_flows = {}
        for d, amt in cashflows_for_xirr:
            aggregated_flows[d] = aggregated_flows.get(d, 0.0) + amt
        
        final_flows = [(d, amt) for d, amt in aggregated_flows.items()]
        property_xirr = xirr(final_flows)
        
        total_inflows = sum(amt for amt in aggregated_flows.values() if amt > 0)
        total_outflows = sum(abs(amt) for amt in aggregated_flows.values() if amt < 0)
        total_expected_profit = total_inflows - total_outflows
        
        return {
            "schedule": schedule,
            "metrics": {
                "xirr": round(property_xirr * 100, 2),
                "total_expected_profit": round(total_expected_profit, 2)
            }
        }
