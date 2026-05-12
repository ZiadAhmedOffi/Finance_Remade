from decimal import Decimal
from django.utils import timezone
from collections import defaultdict
from ..models import RealEstatePortfolio, Property, PropertySale
from .property_selectors import PropertySelector
from .cash_flow_selectors import CashFlowSelectors
from .financing_selectors import FinancingSelectors
from ..calculation import PropertyDataCalc

class PortfolioDashboardSelector:
    """
    Aggregates data for the Real Estate Portfolio Dashboard.
    """

    @staticmethod
    def get_dashboard_data(portfolio: RealEstatePortfolio, reference_date=None) -> dict:
        if reference_date is None:
            reference_date = timezone.now().date()
        
        # Prefetch related data for efficiency
        properties = portfolio.properties.all().select_related(
            'portfolio__assumptions', 
            'financing', 
            'off_plan_details',
            'sale'
        ).prefetch_related('milestones')
        
        assumptions = portfolio.assumptions
        
        # 1. Basic property metrics
        active_properties_metrics = []
        sold_properties_metrics = []
        
        for prop in properties:
            metrics = PropertySelector.calculate_metrics(prop, reference_date)
            # Add status and type for distribution analysis
            metrics['status'] = prop.status
            metrics['property_type'] = prop.property_type
            metrics['country'] = prop.country
            metrics['name'] = prop.name
            metrics['id'] = str(prop.id)
            
            # Source of truth for "Realized" is a sale record with date <= reference_date
            sale = getattr(prop, 'sale', None)
            is_realized = False
            if sale and sale.sale_date <= reference_date:
                is_realized = True
            elif prop.status == "SOLD" and not sale:
                # If marked SOLD but no record, assume it's already realized
                is_realized = True
            
            if is_realized:
                # For sold properties, we only have realized gain
                if sale:
                    realized_gain = PropertyDataCalc.realized_gain(
                        sale.selling_price,
                        metrics['metrics']['total_cost_basis'],
                        PropertyDataCalc.selling_costs(sale.selling_price, sale.selling_fee_percentage)
                    )
                    metrics['metrics']['realized_gain'] = realized_gain
                    metrics['metrics']['selling_price'] = sale.selling_price
                else:
                    # Fallback if no sale record but status is SOLD
                    metrics['metrics']['realized_gain'] = metrics['metrics']['unrealized_gain']
                
                # Sold properties have NO unrealized gain and NO current market value
                metrics['metrics']['unrealized_gain'] = None
                metrics['metrics']['current_market_value'] = Decimal('0.00')
                metrics['status'] = "SOLD" # Force status to SOLD for UI if date passed
                
                sold_properties_metrics.append(metrics)
            else:
                # Active properties (Held, Off-Plan, or Sold in the future)
                # Ensure realized_gain is 0 for active assets
                metrics['metrics']['realized_gain'] = Decimal('0.00')
                
                # Debt Service for Yield Analysis
                debt_service = Decimal('0.00')
                if hasattr(prop, 'financing'):
                    schedule = FinancingSelectors.get_amortization_schedule(prop.financing)
                    # Use current year debt service
                    current_year = reference_date.year
                    loan_start_date = prop.financing.loan_start_date
                    months_per_period = 12 // prop.financing.payments_per_year
                    for item in schedule:
                        y = loan_start_date.year + (loan_start_date.month + (months_per_period * (item['period'] - 1)) - 1) // 12
                        if y == current_year:
                            debt_service += item['periodic_payment']
                
                metrics['metrics']['annual_debt_service'] = debt_service
                active_properties_metrics.append(metrics)

        # 2. Aggregated Metrics (Section 1)
        total_market_value = sum(m['metrics']['current_market_value'] for m in active_properties_metrics)
        total_invested_capital = sum(m['metrics']['total_cost_basis'] for m in active_properties_metrics) + \
                                sum(m['metrics']['total_cost_basis'] for m in sold_properties_metrics)
        total_unrealized_gains = sum(m['metrics']['unrealized_gain'] for m in active_properties_metrics)
        total_realized_gains = sum(m['metrics'].get('realized_gain', Decimal('0.00')) for m in sold_properties_metrics)
        total_annual_rent = sum(m['metrics']['annual_rent'] for m in active_properties_metrics)
        total_noi = sum(m['metrics']['noi'] for m in active_properties_metrics)
        total_debt_service = sum(m['metrics']['annual_debt_service'] for m in active_properties_metrics)
        
        # Cash Flow for Y1 Net Cash Flow
        cf_data = CashFlowSelectors.get_portfolio_cash_flow(portfolio)
        y1_net_cf = cf_data['portfolio_totals'].get(reference_date.year, Decimal('0.00'))
        
        # Yields
        portfolio_gross_yield = PropertyDataCalc.gross_yield(total_annual_rent, total_invested_capital)
        portfolio_net_yield = PropertyDataCalc.net_yield(total_noi, total_market_value)
        
        # ROI: ([Unrealized Gains + Realized Gains] / Total Invested Capital)
        portfolio_roi = Decimal('0.00')
        if total_invested_capital > 0:
            portfolio_roi = (((total_unrealized_gains + total_realized_gains) / total_invested_capital) * Decimal('100')).quantize(Decimal('0.01'))

        aggregated_metrics = {
            "property_count_active": len(active_properties_metrics),
            "portfolio_market_value": total_market_value,
            "total_invested_capital": total_invested_capital,
            "unrealized_gains": total_unrealized_gains,
            "realized_gains": total_realized_gains,
            "total_annual_rent": total_annual_rent,
            "total_noi": total_noi,
            "total_annual_debt_service": total_debt_service,
            "net_cash_flow_y1": y1_net_cf,
            "portfolio_gross_yield": portfolio_gross_yield,
            "portfolio_net_yield": portfolio_net_yield,
            "portfolio_roi": portfolio_roi
        }

        # 3. Capital Distribution (Section 1)
        type_distribution = defaultdict(Decimal)
        country_distribution = defaultdict(Decimal)
        
        for m in active_properties_metrics:
            type_distribution[m['property_type']] += m['metrics']['total_cost_basis']
            country_distribution[m['country']] += m['metrics']['total_cost_basis']
            
        type_dist_list = []
        for p_type, value in type_distribution.items():
            percentage = ((value / total_invested_capital) * Decimal('100')).quantize(Decimal('0.01')) if total_invested_capital > 0 else Decimal('0.00')
            type_dist_list.append({"type": p_type, "value": value, "percentage": percentage})
            
        country_dist_list = []
        for country, value in country_distribution.items():
            percentage = ((value / total_invested_capital) * Decimal('100')).quantize(Decimal('0.01')) if total_invested_capital > 0 else Decimal('0.00')
            country_dist_list.append({"country": country, "value": value, "percentage": percentage})

        # 4. Value & Gain by Property (Section 2)
        property_value_gain_table = []
        for m in active_properties_metrics + sold_properties_metrics:
            property_value_gain_table.append({
                "id": m['id'],
                "name": m['name'],
                "cost_basis": m['metrics']['total_cost_basis'],
                "current_market_value": m['metrics']['current_market_value'] if m['status'] != "SOLD" else None,
                "unrealized_gain": m['metrics']['unrealized_gain'] if m['status'] != "SOLD" else None,
                "realized_gain": m['metrics'].get('realized_gain', Decimal('0.00')) if m['status'] == "SOLD" else Decimal('0.00'),
                "status": m['status']
            })

        # 5. 10-Year Value Appreciation Projection (Section 3)
        # We'll use a simplified version of CF logic but focused on Value
        projection_years = cf_data['years']
        appreciation_projection = {
            "years": projection_years,
            "properties": {},
            "portfolio_total": defaultdict(Decimal)
        }
        
        for prop_id, prop_cf in cf_data['properties'].items():
            values = []
            for year in projection_years:
                # Check if property is owned in this year by looking at annual_cf in cf_data
                cf_value = prop_cf['annual_cf'].get(year)
                
                if cf_value is None:
                    values.append(None)
                else:
                    val = prop_cf['metadata'].get(year, {}).get('market_value', Decimal('0.00'))
                    values.append(val)
                    appreciation_projection['portfolio_total'][year] += val
                    
            appreciation_projection['properties'][prop_id] = {
                "name": prop_cf['name'],
                "values": values
            }
        
        appreciation_projection['portfolio_total'] = [appreciation_projection['portfolio_total'][y] for y in projection_years]

        # 6. Liquidation Readiness Index (Section 4)
        liquidation_table = []
        portfolio_liquidation_indices = []
        
        for m in active_properties_metrics:
            status_val = 40 if m['status'] == "HELD" else 10 # Plan says "Held" 40, "Off-Plan" 10
            years_held = m['metrics']['years_held']
            net_yield = m['metrics']['net_yield']
            gain_pct = (m['metrics']['unrealized_gain'] / m['metrics']['total_cost_basis'] * Decimal('100')) if m['metrics']['total_cost_basis'] > 0 else Decimal('0.00')
            
            # Excel formula: ROUND(status_points + MIN(20, years/3*20) + MIN(20, MAX(0, net_yield)/0.06*20) + MIN(20, MAX(0, gain)/0.3*20), 0)
            # Note: The plan says gain is unrealized_gain / cost_basis. In Excel 0.3 means 30%.
            
            years_points = min(Decimal('20.00'), Decimal(str(years_held)) / Decimal('3') * Decimal('20.00'))
            yield_points = min(Decimal('20.00'), max(Decimal('0.00'), net_yield) / Decimal('6.00') * Decimal('20.00')) # 0.06 is 6%
            gain_points = min(Decimal('20.00'), max(Decimal('0.00'), gain_pct) / Decimal('30.00') * Decimal('20.00')) # 0.3 is 30%
            
            liquidation_index = round(Decimal(str(status_val)) + years_points + yield_points + gain_points)
            
            liquidation_table.append({
                "id": m['id'],
                "name": m['name'],
                "status": m['status'],
                "years_held": years_held,
                "net_yield": net_yield,
                "gain_percentage": gain_pct,
                "liquidation_index": liquidation_index
            })
            portfolio_liquidation_indices.append(liquidation_index)
            
        avg_liquidation_index = round(sum(portfolio_liquidation_indices) / len(portfolio_liquidation_indices)) if portfolio_liquidation_indices else 0

        # 7. Off-Plan Development Stage (Section 5)
        off_plan_table = []
        for prop in properties:
            if prop.status == "OFF_PLAN" and hasattr(prop, 'off_plan_details'):
                details = prop.off_plan_details
                start_date = details.construction_start_date
                comp_date = details.expected_completion_date
                
                total_days = (comp_date - start_date).days
                elapsed_days = (reference_date - start_date).days
                time_elapsed_pct = min(Decimal('100.00'), max(Decimal('0.00'), (Decimal(str(elapsed_days)) / Decimal(str(total_days)) * Decimal('100')))) if total_days > 0 else Decimal('0.00')
                
                # Capital Deployed %: Sum of milestones reached / Total Purchase Price
                total_milestones_pct = sum(m.percentage_of_price for m in prop.milestones.all() if m.date <= reference_date)
                capital_deployed_pct = min(Decimal('100.00'), total_milestones_pct)
                
                # Stage Logic
                te = time_elapsed_pct / Decimal('100')
                if te >= 1: stage = "Completed"
                elif te >= 0.66: stage = "Late Construction"
                elif te >= 0.33: stage = "Mid Construction"
                elif te > 0: stage = "Early Construction"
                else: stage = "Pre-Construction"
                
                off_plan_table.append({
                    "id": str(prop.id),
                    "name": prop.name,
                    "start_date": start_date,
                    "completion_date": comp_date,
                    "time_elapsed_percentage": time_elapsed_pct,
                    "capital_deployed_percentage": capital_deployed_pct,
                    "stage": stage
                })

        # 8. Yield Analysis By Property (Section 6)
        yield_analysis_table = []
        for m in active_properties_metrics:
            # Plan: Filter out off-plan properties from yield analysis
            if m['status'] == "OFF_PLAN":
                continue
                
            yield_analysis_table.append({
                "id": m['id'],
                "name": m['name'],
                "annual_rent": m['metrics']['annual_rent'],
                "noi": m['metrics']['noi'],
                "annual_debt_service": m['metrics']['annual_debt_service'],
                "gross_yield": m['metrics']['gross_yield'],
                "net_yield": m['metrics']['net_yield']
            })
            
        # Portfolio total for yield analysis
        yield_analysis_table.append({
            "id": "total",
            "name": "Portfolio Total",
            "annual_rent": total_annual_rent,
            "noi": total_noi,
            "annual_debt_service": total_debt_service,
            "gross_yield": portfolio_gross_yield,
            "net_yield": portfolio_net_yield
        })

        return {
            "metrics": aggregated_metrics,
            "distribution": {
                "by_type": type_dist_list,
                "by_country": country_dist_list
            },
            "value_gain_table": property_value_gain_table,
            "appreciation_projection": appreciation_projection,
            "liquidation_index": {
                "table": liquidation_table,
                "portfolio_average": avg_liquidation_index
            },
            "off_plan_stages": off_plan_table,
            "yield_analysis": yield_analysis_table
        }
