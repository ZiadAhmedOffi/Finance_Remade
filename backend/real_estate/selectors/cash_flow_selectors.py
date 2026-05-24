from decimal import Decimal
from datetime import date
from collections import defaultdict
from ..models import RealEstatePortfolio, Property, OffPlanMilestone
from .financing_selectors import FinancingSelectors
from ..constants import SCENARIO_ADJUSTMENTS
from ..calculation import PropertyDataCalc
from ..services.taxation_service import TaxationService

class CashFlowSelectors:
    @staticmethod
    def get_portfolio_cash_flow(portfolio: RealEstatePortfolio, start_year: int = None, end_year: int = None) -> dict:
        """
        Calculates annual cash flows for all properties in a portfolio.
        Follows lifecycle and off-plan specific logic.
        Integrates Mortgages, Primary Installments, and Taxation.
        """
        assumptions = portfolio.assumptions
        inception_year = assumptions.inception_date.year
        
        if start_year is None:
            start_year = inception_year
        if end_year is None:
            end_year = inception_year + min(9, assumptions.forecast_horizon - 1)
            
        max_year = inception_year + assumptions.forecast_horizon - 1
        end_year = min(end_year, max_year)
        
        full_years_range = list(range(inception_year, end_year + 1))
        requested_years = list(range(start_year, end_year + 1))
        
        # Include properties that are SOLD but might have historical cash flow
        properties = portfolio.properties.select_related('financing', 'off_plan_details', 'installment', 'usufruct_details').prefetch_related('milestones', 'sale')
        
        property_cash_flows = {}
        portfolio_totals = defaultdict(Decimal)
        portfolio_noi = defaultdict(Decimal)
        portfolio_sales_proceeds = defaultdict(Decimal)
        portfolio_taxes = defaultdict(Decimal)
        
        active_scenario = assumptions.active_scenario
        adjustments = SCENARIO_ADJUSTMENTS.get(active_scenario, {})
        
        app_adj = adjustments.get('appreciation', Decimal('0.00'))
        rent_adj = adjustments.get('rental_growth', Decimal('0.00'))
        vacancy_adj = adjustments.get('vacancy', Decimal('0.00'))
        depreciation_rate = Decimal(str(assumptions.default_depreciation_rate)) / Decimal('100')
        
        for prop in properties:
            prop_data = {"name": prop.name, "annual_cf": {}, "metadata": {}}
            lcf_pool = Decimal('0.00') # Loss Carry Forward pool for this property
            
            # Common rates
            is_usufruct = prop.status == "USUFRUCT"
            u_details = getattr(prop, 'usufruct_details', None) if is_usufruct else None
            
            app_rate = (Decimal(str(prop.appreciation_rate_percentage)) + app_adj) if not is_usufruct else Decimal('0.00')
            rent_growth_rate = (Decimal(str(assumptions.default_rental_growth_rate)) + rent_adj) if not is_usufruct else Decimal('0.00')
            vacancy_rate = Decimal(str(prop.vacancy_rate_percentage)) + vacancy_adj
            mgmt_fee_pct = Decimal(str(assumptions.property_mgmt_fee_percentage))
            maint_fee_pct = Decimal(str(assumptions.maintenance_percentage_of_value))
            selling_fee_pct = Decimal(str(assumptions.selling_fee_percentage)) / Decimal('100')
            
            # Lifecycle bounds
            purchase_year = prop.purchase_date.year
            sale_year = None
            if hasattr(prop, 'sale'):
                sale_year = prop.sale.sale_date.year
            
            # Off-plan specifics
            is_off_plan_initial = prop.status == "OFF_PLAN"
            completion_year = None
            sale_at_completion = False
            if hasattr(prop, 'off_plan_details'):
                completion_year = prop.off_plan_details.expected_completion_date.year
                sale_at_completion = prop.off_plan_details.sale_at_completion

            # Milestones for Off-Plan
            milestones_by_year = defaultdict(Decimal)
            user_milestones = prop.milestones.all()
            user_pct_sum = sum(m.percentage_of_price for m in user_milestones)
            completion_pct = max(Decimal("0.00"), Decimal("100.00") - user_pct_sum)

            for m in user_milestones:
                milestones_by_year[m.date.year] += ((prop.purchase_price or Decimal('0')) * (m.percentage_of_price / Decimal('100')))
            
            # Add Completion milestone (at completion_year)
            if hasattr(prop, 'off_plan_details'):
                comp_yr = prop.off_plan_details.expected_completion_date.year
                milestones_by_year[comp_yr] += ((prop.purchase_price or Decimal('0')) * (completion_pct / Decimal('100')))

            # Financing & Installments
            debt_service_by_year = defaultdict(Decimal)
            interest_by_year = defaultdict(Decimal)
            if hasattr(prop, 'financing'):
                schedule = FinancingSelectors.get_amortization_schedule(prop.financing)
                loan_start_date = prop.financing.loan_start_date
                months_per_period = 12 // prop.financing.payments_per_year
                for item in schedule:
                    y = loan_start_date.year + (loan_start_date.month + (months_per_period * (item['period'] - 1)) - 1) // 12
                    debt_service_by_year[y] += item['periodic_payment']
                    interest_by_year[y] += item['interest_payment']
            
            installment_payments_by_year = defaultdict(Decimal)
            installment_down_payment = Decimal('0.00')
            if hasattr(prop, 'installment'):
                from .installment_selectors import InstallmentSelectors
                schedule = InstallmentSelectors.get_installment_schedule(prop.installment)
                installment_down_payment = prop.installment.down_payment
                for item in schedule:
                    # date format: "YYYY-MM"
                    y = int(item['date'].split('-')[0])
                    installment_payments_by_year[y] += item['payment']

            for year in full_years_range:
                # Initialize variables for metadata
                months_owned = 0
                current_market_value = Decimal('0.00')
                effective_rent = Decimal('0.00')
                mgmt_fee = Decimal('0.00')
                maint_fee = Decimal('0.00')
                total_opex = Decimal('0.00')
                noi = Decimal('0.00')
                construction_cost = Decimal('0.00')
                net_sale_inflow = Decimal('0.00')
                debt_service = Decimal('0.00')
                installments = Decimal('0.00')
                annual_tax = Decimal('0.00')
                
                property_events = []

                # 1. Check if property is within lifecycle
                if year < purchase_year or (sale_year and year > sale_year):
                    cf = None # Signal to show (-)
                else:
                    cf = Decimal('0.00')
                    
                    if year == purchase_year:
                        property_events.append('CONTRACT_SIGNING')
                    
                    if is_usufruct and u_details:
                        t = Decimal(str(year - purchase_year))
                        is_first_year = (year == purchase_year)
                        
                        # Apply appreciation to rents
                        inflow_growth = Decimal(str(float(Decimal('1') + (u_details.inflow_rent_appreciation_percentage / Decimal('100'))) ** float(t)))
                        outflow_growth = Decimal(str(float(Decimal('1') + (u_details.outflow_rent_appreciation_percentage / Decimal('100'))) ** float(t)))
                        
                        # Inflows 0 in first year
                        if is_first_year:
                            annual_inflow = Decimal('0.00')
                            months_owned = 12 - prop.purchase_date.month + 1 # Metadata
                            # Outflow rents "across the year" (12 months)
                            annual_outflow = u_details.outflow_monthly_rent * 12 * outflow_growth
                            # total_opex includes insurance only in first year
                            total_opex = annual_outflow + u_details.annual_ops_cost + u_details.insurance_cost
                            effective_rent = Decimal('0.00')
                            noi = -(total_opex)
                            # Prep cost as investment outflow
                            cf = noi - u_details.prep_cost
                        else:
                            annual_inflow = u_details.inflow_monthly_rent * 12 * inflow_growth
                            months_owned = 12
                            # Outflow rents "across the year" (12 months)
                            annual_outflow = u_details.outflow_monthly_rent * 12 * outflow_growth
                            # total_opex excludes insurance in following years
                            total_opex = annual_outflow + u_details.annual_ops_cost
                            effective_rent = (annual_inflow * (Decimal('1') - (vacancy_rate / Decimal('100')))).quantize(Decimal('0.01'))
                            noi = (effective_rent - total_opex).quantize(Decimal('0.01'))
                            cf = noi
                        
                        current_market_value = Decimal('0.00')
                    
                    # 2. Handle Sale Year inflow
                    elif sale_year and year == sale_year:
                        # If explicitly sold in the sales tab
                        from .property_sale_selectors import PropertySaleSelector
                        sale_metrics = PropertySaleSelector.calculate_sale_metrics(prop.sale)
                        net_sale_inflow = sale_metrics['metrics']['net_proceeds']
                        cf += net_sale_inflow
                        property_events.append('DISPOSAL')
                    
                    # 3. Handle Operating CF
                    elif is_off_plan_initial and completion_year and year < completion_year:
                        # Off-Plan construction phase
                        construction_cost = milestones_by_year.get(year, Decimal('0.00'))
                        debt_service = debt_service_by_year.get(year, Decimal('0.00'))
                        installments = installment_payments_by_year.get(year, Decimal('0.00'))
                        cf = -(construction_cost + debt_service + installments)
                        months_owned = 12
                        if construction_cost > 0 or installments > 0:
                            property_events.append('ON_PAYMENT')
                    
                    elif is_off_plan_initial and completion_year and year == completion_year:
                        # Completion Year
                        property_events.append('HANDOVER')
                        if sale_at_completion:
                            # Sale at completion logic
                            appreciation_rate = prop.off_plan_details.appreciation_rate_at_completion / Decimal("100")
                            value_at_completion = (prop.purchase_price or Decimal('0')) * (Decimal("1") + appreciation_rate)
                            net_sale_inflow = value_at_completion * (Decimal("1") - selling_fee_pct)
                            # Subtract construction costs in that year if any
                            construction_cost = milestones_by_year.get(year, Decimal('0.00'))
                            debt_service = debt_service_by_year.get(year, Decimal('0.00'))
                            installments = installment_payments_by_year.get(year, Decimal('0.00'))
                            cf = net_sale_inflow - construction_cost - debt_service - installments
                            # Signal that it's "sold" effectively
                            sale_year = year 
                            property_events.append('DISPOSAL')
                        else:
                            # Transition to rental property
                            # Pro-rate based on completion date
                            months_owned = 12 - prop.off_plan_details.expected_completion_date.month + 1
                            t = Decimal(str(year - purchase_year))
                            completion_jump_rate = prop.off_plan_details.appreciation_rate_at_completion / Decimal('100')
                            
                            # Appreciate rent and value
                            current_market_value = PropertyDataCalc.market_value(prop.purchase_price or Decimal('0'), app_rate, t)
                            current_market_value = (current_market_value * (Decimal('1') + completion_jump_rate)).quantize(Decimal('0.01'))
                            
                            effective_rent = PropertyDataCalc.effective_rent(
                                prop.monthly_rent or Decimal('0'),
                                vacancy_rate,
                                t,
                                rent_growth_rate,
                                months_in_period=months_owned
                            )
                            effective_rent = (effective_rent * (Decimal('1') + completion_jump_rate)).quantize(Decimal('0.01'))

                            maint_fee = PropertyDataCalc.maintenance_fees(current_market_value, maint_fee_pct)
                            mgmt_fee = PropertyDataCalc.management_fees(effective_rent, mgmt_fee_pct)
                            
                            total_opex = (mgmt_fee + maint_fee + Decimal(str(prop.other_operational_expenses))).quantize(Decimal('0.01'))
                            noi = PropertyDataCalc.noi(effective_rent, total_opex)
                            
                            # Subtract remaining construction costs and debt service
                            construction_cost = milestones_by_year.get(year, Decimal('0.00'))
                            debt_service = debt_service_by_year.get(year, Decimal('0.00'))
                            installments = installment_payments_by_year.get(year, Decimal('0.00'))
                            cf = noi - construction_cost - debt_service - installments
                    
                    else:
                        # Normal Held Property or post-completion off-plan
                        t = Decimal(str(year - purchase_year))
                        
                        # Market Value
                        current_market_value = PropertyDataCalc.market_value(prop.purchase_price or Decimal('0'), app_rate, t)
                        
                        # Purchase Price & Down Payment
                        if year == purchase_year and not is_off_plan_initial:
                            if prop.financing_type == "PRIMARY_INSTALLMENTS":
                                cf -= installment_down_payment
                            elif prop.financing_type == "MORTGAGED" and hasattr(prop, 'financing'):
                                down_payment = (prop.purchase_price or Decimal('0')) - prop.financing.loan_amount
                                cf -= down_payment
                            else:
                                cf -= (prop.purchase_price or Decimal('0'))
                            
                            months_owned = 12 - prop.purchase_date.month + 1
                        else:
                            months_owned = 12
                        
                        effective_rent = PropertyDataCalc.effective_rent(
                            prop.monthly_rent or Decimal('0'),
                            vacancy_rate,
                            t,
                            rent_growth_rate,
                            months_in_period=months_owned
                        )
                        
                        if is_off_plan_initial and completion_year and year >= completion_year:
                            completion_jump_rate = prop.off_plan_details.appreciation_rate_at_completion / Decimal('100')
                            # Completion jump is a one-time step up in value
                            current_market_value = (current_market_value * (Decimal('1') + completion_jump_rate)).quantize(Decimal('0.01'))
                            effective_rent = (effective_rent * (Decimal('1') + completion_jump_rate)).quantize(Decimal('0.01'))

                        maint_fee = PropertyDataCalc.maintenance_fees(current_market_value, maint_fee_pct)
                        mgmt_fee = PropertyDataCalc.management_fees(effective_rent, mgmt_fee_pct)
                        
                        total_opex = (mgmt_fee + maint_fee + Decimal(str(prop.other_operational_expenses))).quantize(Decimal('0.01'))
                        noi = PropertyDataCalc.noi(effective_rent, total_opex)
                        debt_service = debt_service_by_year.get(year, Decimal('0.00'))
                        installments = installment_payments_by_year.get(year, Decimal('0.00'))
                        cf += noi - debt_service - installments

                    # --- TAXATION INTEGRATION ---
                    interest_expense = interest_by_year.get(year, Decimal('0.00'))
                    depreciation = ((prop.purchase_price or Decimal('0')) * depreciation_rate).quantize(Decimal('0.01'))
                    taxable_income = noi - depreciation - interest_expense
                    
                    # Apply LCF
                    adjusted_taxable, lcf_pool = TaxationService.apply_loss_carry_forward(taxable_income, lcf_pool)
                    
                    tax_context = {
                        'market_value': current_market_value,
                        'net_income': adjusted_taxable,
                        'property_events': property_events,
                        'is_disposal_year': year == sale_year,
                        'loan_interest': interest_expense
                    }
                    annual_tax = TaxationService.calculate_property_tax_for_year(prop, year - inception_year, tax_context)
                    cf -= annual_tax
                    # --- END TAXATION ---

                # Aggregation
                if cf is not None:
                    portfolio_totals[year] += cf
                    portfolio_noi[year] += noi
                    portfolio_sales_proceeds[year] += net_sale_inflow
                    portfolio_taxes[year] += annual_tax
                
                if year in requested_years:
                    prop_data["annual_cf"][year] = cf.quantize(Decimal('0.01')) if cf is not None else None
                    if cf is not None:
                        # Store metadata for drill-down
                        prop_data["metadata"][year] = {
                            "months_held": months_owned,
                            "market_value": current_market_value.quantize(Decimal('0.01')),
                            "effective_rent": effective_rent.quantize(Decimal('0.01')),
                            "mgmt_fees": mgmt_fee.quantize(Decimal('0.01')),
                            "maintenance_fees": maint_fee.quantize(Decimal('0.01')),
                            "opex": total_opex.quantize(Decimal('0.01')),
                            "noi": noi.quantize(Decimal('0.01')),
                            "debt_service": debt_service.quantize(Decimal('0.01')),
                            "interest_expense": interest_expense.quantize(Decimal('0.01')),
                            "installments": installments.quantize(Decimal('0.01')),
                            "purchase_price": (prop.purchase_price or Decimal('0')) if year == purchase_year and not is_off_plan_initial and prop.financing_type not in ["MORTGAGED", "PRIMARY_INSTALLMENTS"] else Decimal("0.00"),
                            "down_payment": (installment_down_payment if prop.financing_type == "PRIMARY_INSTALLMENTS" else ((prop.purchase_price or Decimal('0')) - prop.financing.loan_amount if prop.financing_type == "MORTGAGED" and hasattr(prop, "financing") else Decimal("0.00"))) if year == purchase_year else Decimal("0.00"),
                            "construction_costs": construction_cost.quantize(Decimal('0.01')),
                            "sale_proceeds": net_sale_inflow.quantize(Decimal('0.01')),
                            "taxes": annual_tax.quantize(Decimal('0.01')),
                            "lcf_pool": lcf_pool.quantize(Decimal('0.01'))
                        }
            
            property_cash_flows[str(prop.id)] = prop_data

        # Cumulative CF from inception
        current_cumulative = Decimal('0.00')
        cumulative_by_year = {}
        for year in full_years_range:
            current_cumulative += portfolio_totals[year]
            cumulative_by_year[year] = current_cumulative.quantize(Decimal('0.01'))

        return {
            "inception_year": inception_year,
            "years": requested_years,
            "properties": property_cash_flows,
            "portfolio_totals": {y: portfolio_totals[y].quantize(Decimal('0.01')) for y in requested_years},
            "portfolio_noi": {y: portfolio_noi[y].quantize(Decimal('0.01')) for y in requested_years},
            "portfolio_sales_proceeds": {y: portfolio_sales_proceeds[y].quantize(Decimal('0.01')) for y in requested_years},
            "portfolio_taxes": {y: portfolio_taxes[y].quantize(Decimal('0.01')) for y in requested_years},
            "cumulative_cf": {y: cumulative_by_year[y] for y in requested_years}
        }
