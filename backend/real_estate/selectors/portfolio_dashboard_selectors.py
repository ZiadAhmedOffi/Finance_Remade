from decimal import Decimal
from django.utils import timezone
from collections import defaultdict
from ..models import RealEstatePortfolio, Property, PropertySale, RealEstateInvestorAction
from .property_selectors import PropertySelector
from .cash_flow_selectors import CashFlowSelectors
from .financing_selectors import FinancingSelectors
from ..calculation import PropertyDataCalc
from ..utils.xirr import xirr

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
                    # Fallback if no record but status is SOLD
                    metrics['metrics']['realized_gain'] = metrics['metrics']['unrealized_gain']
                
                # Sold properties have NO unrealized gain and NO current market value
                metrics['metrics']['unrealized_gain'] = None
                metrics['metrics']['current_market_value'] = Decimal('0.00')
                metrics['status'] = "SOLD" # Force status to SOLD for UI if date passed
                
                sold_properties_metrics.append(metrics)
            else:
                # Active properties (Held, Off-Plan, or Sold in the future)
                # Ensure realized_gain is 0 for active assets initially
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
        # Cash Flow for Y1 Net Cash Flow and Realized Gains from operations
        cf_data = CashFlowSelectors.get_portfolio_cash_flow(portfolio)
        y1_net_cf = cf_data['portfolio_totals'].get(reference_date.year, Decimal('0.00'))

        # Calculate total realized gains from sales alone first
        total_sales_gain = sum(m['metrics'].get('realized_gain', Decimal('0.00')) for m in sold_properties_metrics)

        # Add operational realized gains to each property (NOI - Debt Service)
        for m in active_properties_metrics + sold_properties_metrics:
            prop_id = m['id']
            prop_cf = cf_data['properties'].get(prop_id)
            if prop_cf:
                extra_realized_gain = Decimal('0.00')
                for year, cf in prop_cf['annual_cf'].items():
                    # Only count years up to reference_date where annual_cf was positive
                    if year <= reference_date.year and cf is not None and cf > 0:
                        metadata = prop_cf['metadata'].get(year, {})
                        noi = metadata.get('noi', Decimal('0.00'))
                        debt_service = metadata.get('debt_service', Decimal('0.00'))
                        extra_realized_gain += (noi - debt_service)
                
                m['metrics']['realized_gain'] = m['metrics'].get('realized_gain', Decimal('0.00')) + extra_realized_gain

        total_market_value = sum(m['metrics']['current_market_value'] for m in active_properties_metrics if m['status'] != "USUFRUCT")
        total_invested_capital = sum(m['metrics'].get('total_cost_basis', Decimal('0.00')) for m in active_properties_metrics) + \
                                sum(m['metrics'].get('total_cost_basis', Decimal('0.00')) for m in sold_properties_metrics)
        
        # Handle cases where unrealized_gain might be None (Sold properties)
        total_unrealized_gains = sum(m['metrics'].get('unrealized_gain') or Decimal('0.00') for m in active_properties_metrics)
        
        total_annual_rent = sum(m['metrics'].get('annual_rent') or Decimal('0.00') for m in active_properties_metrics)
        total_noi = sum(m['metrics'].get('noi') or Decimal('0.00') for m in active_properties_metrics)
        total_debt_service = sum(m['metrics'].get('annual_debt_service') or Decimal('0.00') for m in active_properties_metrics)
        
        # New: Portfolio vacancy rate as average across all active properties
        active_props_for_vacancy = [m for m in active_properties_metrics if m['status'] != "OFF_PLAN"]
        portfolio_vacancy_rate = Decimal('0.00')
        if active_props_for_vacancy:
            portfolio_vacancy_rate = sum(Decimal(str(m['property'].vacancy_rate_percentage)) for m in active_props_for_vacancy) / len(active_props_for_vacancy)

        # Portfolio realized gains = Gains from sales + Positive annual portfolio cash flows (excluding sale proceeds)
        portfolio_operational_gain = sum(
            (cf - cf_data['portfolio_sales_proceeds'][year]) for year, cf in cf_data['portfolio_totals'].items()
            if year <= reference_date.year and (cf - cf_data['portfolio_sales_proceeds'][year]) > 0
        )
        total_realized_gains = total_sales_gain + portfolio_operational_gain
        
        # Yields
        portfolio_gross_yield = PropertyDataCalc.gross_yield(total_annual_rent, total_invested_capital)
        portfolio_net_yield = PropertyDataCalc.net_yield(total_noi, total_market_value)
        
        # ROI: ([Unrealized Gains + Realized Gains] / Total Invested Capital)
        portfolio_roi = Decimal('0.00')
        if total_invested_capital > 0:
            portfolio_roi = (((total_unrealized_gains + total_realized_gains) / total_invested_capital) * Decimal('100')).quantize(Decimal('0.01'))

        # IRR Calculation (Equity IRR)
        # 1. Total Return IRR: Flows = [-Injections, +Current Equity NAV]
        # 2. Yield IRR: Flows = [-Injections, +(Total Investments + Cumulative Operational Cash Flow)]
        
        injections = RealEstateInvestorAction.objects.filter(portfolio=portfolio, type="PRIMARY_INVESTMENT").order_by('created_at')
        from .portfolio_selectors import PortfolioSelectors
        nav_metrics = PortfolioSelectors.get_portfolio_nav_metrics(portfolio, reference_date=reference_date)
        
        # Correct Equity NAV: (Assets + Cash) - Liabilities
        equity_nav = float(nav_metrics["nav"])
        total_investments = float(nav_metrics["total_investments"])
        
        # Cumulative Operational CF to date
        # We subtract total_investments from cash_reserves because cash_reserves = total_investments + cumulative_cf
        # and cumulative_cf is exactly the sum of NOI - Debt Service - Taxes - Installments - Acquisitions + Sales Proceeds.
        # However, we want the "Yield" component to ignore asset appreciation and ONLY look at net income.
        cumulative_cf = float(nav_metrics["cash_reserves"]) - total_investments
        
        flows_total = []
        flows_yield = []
        
        for inv in injections:
            amt = float(inv.amount)
            if amt > 0:
                # Flow date should be the date of injection
                f_date = inv.created_at.date()
                flows_total.append((f_date, -amt))
                flows_yield.append((f_date, -amt))
        
        if not flows_total:
            # Handle case with no injections
            portfolio_irr = 0.0
            irr_yield = 0.0
            irr_capital_growth = 0.0
        else:
            # Add terminal values
            # Total Return includes the current equity value (Appreciation + Cash)
            flows_total.append((reference_date, equity_nav))
            
            # Yield Return assumes NO appreciation, so terminal value is just the net cash generated + principal value
            # Actually, Equity (No Growth) = (Initial Purchase Price - Remaining Debt) + Cash
            # But a simpler proxy for "Yield Return" is: Injections + Cumulative Net Operational Cash Flow
            # This represents how much cash the investor got (or has in the pot) relative to what they put in.
            flows_yield.append((reference_date, total_investments + cumulative_cf))
            
            portfolio_irr = xirr(flows_total)
            irr_yield = xirr(flows_yield)
            irr_capital_growth = portfolio_irr - irr_yield

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
            "portfolio_roi": portfolio_roi,
            "portfolio_vacancy_rate": portfolio_vacancy_rate,
            "portfolio_avg_appreciation": sum(Decimal(str(m['property'].appreciation_rate_percentage)) for m in active_properties_metrics) / len(active_properties_metrics) if active_properties_metrics else Decimal('0.00'),
            "portfolio_simple_irr": portfolio_net_yield + (sum(Decimal(str(m['property'].appreciation_rate_percentage)) for m in active_properties_metrics) / len(active_properties_metrics) if active_properties_metrics else Decimal('0.00')),
            "portfolio_irr": Decimal(str(portfolio_irr * 100)).quantize(Decimal('0.01')),
            "irr_yield": Decimal(str(irr_yield * 100)).quantize(Decimal('0.01')),
            "irr_capital_growth": Decimal(str(irr_capital_growth * 100)).quantize(Decimal('0.01'))
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
                "realized_gain": m['metrics'].get('realized_gain', Decimal('0.00')),
                "status": m['status']
            })

        # 5. Annual Portfolio Value Expansion (Section 3) - New Method
        projection_years = sorted(cf_data['years'])
        current_year = reference_date.year
        value_expansion_ladder = []
        
        # Temporary storage for annual aggregation (historical and future)
        annual_metrics = {y: {
            "injection": Decimal('0.00'),
            "total_value": Decimal('0.00')
        } for y in projection_years}

        for prop_id, prop_cf in cf_data['properties'].items():
            # Find the actual property object for accurate purchase data
            prop_obj = next((p for p in properties if str(p.id) == prop_id), None)
            if not prop_obj: continue
            
            p_year = prop_obj.purchase_date.year
            p_price = prop_obj.purchase_price
            is_usufruct = prop_obj.status == "USUFRUCT"
            u_details = getattr(prop_obj, 'usufruct_details', None) if is_usufruct else None

            for i, year in enumerate(projection_years):
                # Use reference_date market value for current year to be consistent with top metrics
                if year == current_year:
                    # Find metrics for this property to get current_market_value as of reference_date
                    m = next((item for item in active_properties_metrics if item['id'] == prop_id), None)
                    if m:
                        market_value = m['metrics']['current_market_value']
                    else:
                        # Fallback to cash flow metadata if not found in active metrics (e.g. if sold later in current year)
                        metadata = prop_cf['metadata'].get(year, {})
                        market_value = metadata.get('market_value', Decimal('0.00'))
                else:
                    metadata = prop_cf['metadata'].get(year, {})
                    market_value = metadata.get('market_value', Decimal('0.00'))
                
                # Check if property was sold in or before this year
                is_sold = hasattr(prop_obj, 'sale') and prop_obj.sale.sale_date.year <= year
                if is_sold:
                    # If sold, it no longer contributes to portfolio value in this or subsequent years
                    market_value = Decimal('0.00')
                elif year >= p_year:
                    # Floor market value at purchase_price if it's within lifecycle and not yet sold.
                    # This ensures off-plan properties during construction show up at cost basis.
                    # Also handles cases where market_value might be reported as less than cost basis.
                    if p_price is not None:
                        market_value = max(market_value, p_price)
                
                if year == p_year:
                    # Asset Injection happens in the purchase year
                    injection_val = p_price if p_price is not None else (u_details.prep_cost if u_details else Decimal('0.00'))
                    annual_metrics[year]["injection"] += injection_val
                
                annual_metrics[year]["total_value"] += market_value

        # Finalize value_expansion_ladder (historical and future)
        prev_total_value = Decimal('0.00')
        for year in projection_years:
            injection = annual_metrics[year]["injection"]
            total_value = annual_metrics[year]["total_value"]
            
            # Appreciation is the residual that bridges the gap between years
            # This ensures Closing Value (N) = Opening Value (N-1) + Injection (N) + Appreciation (N)
            appreciation = total_value - prev_total_value - injection
            
            value_expansion_ladder.append({
                "year": year,
                "injection": injection,
                "appreciation": appreciation,
                "total_portfolio_value": total_value,
                "is_future": year > current_year
            })
            prev_total_value = total_value

        # 5.5 Intrinsic Value Spider Graph
        intrinsic_value_data = []
        intrinsic_value_table = []
        # We still use the full projection for exit valuation
        final_year = projection_years[-1]

        for prop_id, prop_cf in cf_data['properties'].items():
            # Entry Val = Purchase Price + Acq Fees
            # Find the actual property object for accurate entry data
            prop_obj = next((p for p in properties if str(p.id) == prop_id), None)
            if not prop_obj: continue

            is_usufruct = prop_obj.status == "USUFRUCT"
            u_details = getattr(prop_obj, 'usufruct_details', None) if is_usufruct else None

            if is_usufruct and u_details:
                entry_val = u_details.prep_cost
            else:
                entry_val = PropertyDataCalc.total_cost_basis(prop_obj.purchase_price, Decimal(str(assumptions.acquisition_fee_percentage)))
            
            current_val = prop_cf['metadata'].get(current_year, {}).get('market_value', Decimal('0.00'))
            
            # Floor current_val at purchase_price if not sold and current_val is 0
            is_sold_now = hasattr(prop_obj, 'sale') and prop_obj.sale.sale_date.year <= current_year
            if current_val == 0 and not is_sold_now:
                if is_usufruct and u_details:
                    current_val = u_details.prep_cost
                else:
                    current_val = prop_obj.purchase_price
                
            exit_val = prop_cf['metadata'].get(final_year, {}).get('market_value', Decimal('0.00'))

            if exit_val > 0 or (is_usufruct and entry_val > 0):
                # For Usufruct, exit_val might be 0 in terms of asset value, 
                # but maybe we should still show it?
                # Actually, the spider graph expects exit_val to be the 100% baseline.
                # If Usufruct has no market value, it might not fit the spider graph well.
                # But let's at least not crash.
                
                # If exit_val is 0 but it's Usufruct, maybe use entry_val as baseline for current?
                baseline = exit_val if exit_val > 0 else entry_val
                
                if baseline > 0:
                    intrinsic_value_data.append({
                        "subject": prop_obj.name,
                        "entry": (entry_val / baseline * Decimal('100')).quantize(Decimal('0.1')),
                        "current": (current_val / baseline * Decimal('100')).quantize(Decimal('0.1')),
                        "expected": (exit_val / baseline * Decimal('100')).quantize(Decimal('0.1')) if baseline > 0 else Decimal('100.0'),
                        "raw_entry": entry_val,
                        "raw_current": current_val,
                        "raw_expected": exit_val
                    })
                    
                    intrinsic_value_table.append({
                        "name": prop_obj.name,
                        "entry_valuation": entry_val,
                        "current_valuation": current_val,
                        "exit_valuation": exit_val,
                        "growth_multiple": (exit_val / entry_val).quantize(Decimal('0.01')) if entry_val > 0 else Decimal('0.00')
                    })

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
            "value_expansion_ladder": value_expansion_ladder,
            "intrinsic_value": {
                "data": intrinsic_value_data,
                "table": intrinsic_value_table
            },
            "liquidation_index": {
                "table": liquidation_table,
                "portfolio_average": avg_liquidation_index
            },
            "off_plan_stages": off_plan_table,
            "yield_analysis": yield_analysis_table
        }
