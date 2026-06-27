from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from ..models import RealEstatePortfolio
from collections import defaultdict
from datetime import date

class PortfolioSelectors:
    @staticmethod
    def get_portfolios():
        """
        Returns all active real estate portfolios.
        """
        return RealEstatePortfolio.objects.filter(status="ACTIVE").select_related('assumptions', 'created_by')

    @staticmethod
    def get_portfolio_by_id(portfolio_id):
        """
        Returns a single portfolio by ID.
        """
        return RealEstatePortfolio.objects.select_related('assumptions', 'created_by').get(id=portfolio_id)

    @staticmethod
    def get_total_units_at_year(portfolio, year):
        """
        Calculates total units at the end of a given year for a RE portfolio.
        """
        from ..models import RealEstateInvestorAction
        return float(RealEstateInvestorAction.objects.filter(
            portfolio=portfolio, 
            type="PRIMARY_INVESTMENT",
            year__lte=year
        ).aggregate(total_units=Sum('units'))['total_units'] or 0.0)

    @staticmethod
    def get_portfolio_nav_context(portfolio, start_year, end_year, properties=None, cf_data=None, sales_metrics=None, investments_list=None):
        """
        Precomputes yearly NAV inputs so callers can build multi-year series without
        recalculating debt schedules, trial balances, and property lookups every year.
        """
        from .property_selectors import PropertySelector
        from .property_sale_selectors import PropertySaleSelector
        from .cash_flow_selectors import CashFlowSelectors
        from ..models import LedgerYear
        from .ledger_selectors import LedgerSelectors
        from .financing_selectors import FinancingSelectors
        from .installment_selectors import InstallmentSelectors

        if properties is None:
            properties = list(portfolio.properties.all().select_related(
                'portfolio__assumptions',
                'financing',
                'off_plan_details',
                'sale',
                'usufruct_details',
                'installment',
            ).prefetch_related('milestones'))
        else:
            properties = list(properties)

        if cf_data is None:
            cf_data = CashFlowSelectors.get_portfolio_cash_flow(portfolio, end_year=end_year, force_base_scenario=True)

        if investments_list is None:
            investments_list = list(portfolio.investor_actions.all())
        else:
            investments_list = list(investments_list)

        if sales_metrics is None:
            sales_metrics = PropertySaleSelector.get_sales_for_portfolio(portfolio)

        sales_proceeds_by_year = defaultdict(Decimal)
        for sale_metric in sales_metrics:
            sales_proceeds_by_year[sale_metric["sale"].sale_date.year] += Decimal(str(sale_metric["metrics"]["net_proceeds"]))

        yearly_investments = defaultdict(Decimal)
        cumulative_investments = {}
        cumulative_units = {}
        running_investments = Decimal('0.00')
        running_units = Decimal('0.00')
        for yr in range(start_year, end_year + 1):
            for action in investments_list:
                if action.type == "PRIMARY_INVESTMENT" and action.year == yr:
                    yearly_investments[yr] += Decimal(str(action.amount))
                    running_units += Decimal(str(action.units))
            running_investments += yearly_investments[yr]
            cumulative_investments[yr] = running_investments
            cumulative_units[yr] = running_units

        closed_ledger_years = {
            ledger_year.year: ledger_year
            for ledger_year in LedgerYear.objects.filter(portfolio=portfolio, year__gte=start_year, year__lte=end_year)
        }
        ledger_cash_by_year = {}
        ledger_trial_balances = {}
        for yr, ledger_year in closed_ledger_years.items():
            tb = LedgerSelectors.get_trial_balance(ledger_year)
            ledger_trial_balances[yr] = tb
            cash_acc_data = next((a for a in tb["accounts"] if a["account_name"] == "Cash"), None)
            if cash_acc_data is not None:
                ledger_cash_by_year[yr] = Decimal(str(cash_acc_data["net_balance"]))

        debt_service_by_year = defaultdict(Decimal)
        installment_service_by_year = defaultdict(Decimal)
        mortgage_liabilities_by_year = defaultdict(Decimal)
        installment_liabilities_by_year = defaultdict(Decimal)
        offplan_liabilities_by_year = defaultdict(Decimal)

        for prop in properties:
            financing = getattr(prop, 'financing', None)
            if financing is not None:
                schedule = FinancingSelectors.get_amortization_schedule(financing)
                months_per_period = 12 // financing.payments_per_year
                year_end_balances = {}
                for item in schedule:
                    total_months_offset = months_per_period * (item['period'] - 1)
                    payment_year = financing.loan_start_date.year + (financing.loan_start_date.month + total_months_offset - 1) // 12
                    debt_service_by_year[payment_year] += Decimal(str(item['periodic_payment']))
                    year_end_balances[payment_year] = Decimal(str(item['ending_balance']))

                outstanding = Decimal(str(financing.loan_amount))
                for yr in range(start_year, end_year + 1):
                    if financing.loan_start_date.year > yr:
                        continue
                    if yr in year_end_balances:
                        outstanding = year_end_balances[yr]
                    mortgage_liabilities_by_year[yr] += outstanding

            installment = getattr(prop, 'installment', None)
            if installment is not None:
                schedule = InstallmentSelectors.get_installment_schedule(installment)
                total_principal = Decimal(str((installment.property.purchase_price or Decimal('0.00')) - installment.down_payment))
                year_end_paid = defaultdict(Decimal)
                for item in schedule:
                    payment_year = int(item['date'].split('-')[0])
                    payment_amount = Decimal(str(item['payment']))
                    installment_service_by_year[payment_year] += payment_amount
                    year_end_paid[payment_year] += payment_amount

                paid_to_date = Decimal('0.00')
                for yr in range(start_year, end_year + 1):
                    if installment.start_date.year > yr:
                        continue
                    paid_to_date += year_end_paid.get(yr, Decimal('0.00'))
                    installment_liabilities_by_year[yr] += max(Decimal('0.00'), total_principal - paid_to_date)

            if prop.status == "OFF_PLAN":
                milestones = list(prop.milestones.all())
                for yr in range(start_year, end_year + 1):
                    ref_date = date(yr, 12, 31)
                    if prop.purchase_date > ref_date:
                        continue
                    outstanding = Decimal('0.00')
                    total_price = prop.purchase_price or Decimal('0.00')
                    for milestone in milestones:
                        if milestone.date > ref_date and milestone.date > prop.purchase_date:
                            outstanding += (Decimal(str(milestone.percentage_of_price)) / Decimal('100.00')) * total_price
                    offplan_liabilities_by_year[yr] += outstanding

        cash_change_breakdown_by_year = defaultdict(list)
        assets_change_breakdown_by_year = defaultdict(list)
        for yr in range(start_year, end_year + 1):
            yearly_investment = yearly_investments.get(yr, Decimal('0.00'))
            if yearly_investment > 0:
                cash_change_breakdown_by_year[yr].append({
                    "name": f"Investor Injections ({yr})",
                    "amount": float(yearly_investment),
                    "type": "INFLOW",
                })

            for prop in properties:
                if prop.purchase_date.year == yr:
                    cost = prop.purchase_price or Decimal('0.00')
                    if prop.status == "USUFRUCT":
                        cost = getattr(prop.usufruct_details, 'prep_cost', Decimal('0.00'))
                        cash_change_breakdown_by_year[yr].append({
                            "name": f"Usufruct Prep: {prop.name}",
                            "amount": float(cost),
                            "type": "OUTFLOW",
                        })
                    else:
                        down_payment = cost
                        if prop.financing_type == "MORTGAGED" and getattr(prop, "financing", None) is not None:
                            down_payment = cost - prop.financing.loan_amount
                        elif prop.financing_type == "PRIMARY_INSTALLMENTS" and getattr(prop, "installment", None) is not None:
                            down_payment = prop.installment.down_payment

                        cash_change_breakdown_by_year[yr].append({
                            "name": f"Acquisition: {prop.name}",
                            "amount": float(down_payment),
                            "type": "OUTFLOW",
                        })
                        assets_change_breakdown_by_year[yr].append({
                            "name": f"Added Asset: {prop.name}",
                            "amount": float(prop.purchase_price or 0),
                            "type": "ADDITION",
                        })

                if prop.status == "OFF_PLAN":
                    for milestone in prop.milestones.all():
                        if milestone.date.year == yr:
                            amount = (Decimal(str(milestone.percentage_of_price)) / Decimal('100.00')) * (prop.purchase_price or Decimal('0.00'))
                            if amount > 0:
                                cash_change_breakdown_by_year[yr].append({
                                    "name": f"Milestone: {milestone.milestone_name} ({prop.name})",
                                    "amount": float(amount),
                                    "type": "OUTFLOW",
                                })

            total_sales_inflow = Decimal(str(cf_data["portfolio_sales_proceeds"].get(yr, Decimal('0.00'))))
            if total_sales_inflow > 0:
                cash_change_breakdown_by_year[yr].append({
                    "name": f"Sales Proceeds ({yr})",
                    "amount": float(total_sales_inflow),
                    "type": "INFLOW",
                })

            yearly_noi = Decimal(str(cf_data["portfolio_noi"].get(yr, Decimal('0.00'))))
            yearly_taxes = Decimal(str(cf_data["portfolio_taxes"].get(yr, Decimal('0.00'))))
            total_debt_service = debt_service_by_year.get(yr, Decimal('0.00')) + installment_service_by_year.get(yr, Decimal('0.00'))

            if yearly_noi != 0:
                cash_change_breakdown_by_year[yr].append({
                    "name": f"Net Operating Income ({yr})",
                    "amount": float(abs(yearly_noi)),
                    "type": "INFLOW" if yearly_noi > 0 else "OUTFLOW",
                })
            if total_debt_service > 0:
                cash_change_breakdown_by_year[yr].append({
                    "name": f"Debt Service ({yr})",
                    "amount": float(total_debt_service),
                    "type": "OUTFLOW",
                })
            if yearly_taxes > 0:
                cash_change_breakdown_by_year[yr].append({
                    "name": f"Taxes ({yr})",
                    "amount": float(yearly_taxes),
                    "type": "OUTFLOW",
                })

        yearly_metrics = {}
        for yr in range(start_year, end_year + 1):
            ref_date = date(yr, 12, 31)
            property_metrics = PropertySelector.get_properties_for_portfolio(
                portfolio,
                reference_date=ref_date,
                properties=properties,
            )
            assets_breakdown = [
                {
                    "name": metric["property"].name,
                    "value": float(metric["metrics"]["current_market_value"]),
                    "status": metric["property"].status,
                }
                for metric in property_metrics
            ]
            total_market_value_held = sum(
                Decimal(str(metric["metrics"]["current_market_value"]))
                for metric in property_metrics
            )
            total_investments = cumulative_investments.get(yr, Decimal('0.00'))
            total_net_proceeds = sum(
                amount for sale_year, amount in sales_proceeds_by_year.items() if sale_year <= yr
            )
            cash_reserves = ledger_cash_by_year.get(yr)
            is_ledger_sourced = cash_reserves is not None
            if cash_reserves is None:
                cash_reserves = total_investments + Decimal(str(cf_data["cumulative_cf"].get(yr, Decimal('0.00'))))

            total_liabilities = (
                mortgage_liabilities_by_year.get(yr, Decimal('0.00')) +
                installment_liabilities_by_year.get(yr, Decimal('0.00')) +
                offplan_liabilities_by_year.get(yr, Decimal('0.00'))
            )
            total_units = float(cumulative_units.get(yr, Decimal('0.00')))
            nav = total_market_value_held + cash_reserves - total_liabilities
            if total_units == 0:
                total_units = float(portfolio.total_units)

            yearly_metrics[yr] = {
                "total_market_value_held": float(total_market_value_held),
                "total_investments": float(total_investments),
                "total_net_proceeds": float(total_net_proceeds),
                "cash_reserves": float(cash_reserves),
                "total_liabilities": float(total_liabilities),
                "nav": float(nav),
                "total_units": total_units,
                "price_per_unit": float(nav / Decimal(str(total_units))) if total_units > 0 else 1.0,
                "assets_breakdown": assets_breakdown,
                "cash_change_breakdown": cash_change_breakdown_by_year[yr],
                "assets_change_breakdown": assets_change_breakdown_by_year[yr],
                "is_ledger_sourced": is_ledger_sourced,
            }

        return {
            "years": yearly_metrics,
            "ledger_trial_balances": ledger_trial_balances,
        }

    @staticmethod
    def get_portfolio_nav_metrics(portfolio, reference_date=None, properties=None, cf_data=None, sales_metrics=None, investments_list=None, nav_context=None):
        """
        Calculates NAV and Cash Reserves for a portfolio.
        NAV = Market Value of Held Assets + Cash Reserves
        
        Cash Reserves Primary Logic: 
        - Use "Cash" account balance from the LedgerYear if it exists.
        
        Cash Reserves Fallback Logic:
        - Total Primary Investments + Cumulative Cash Flow (from Cash Flow Model - BASE scenario).
        """
        from .property_selectors import PropertySelector
        from .property_sale_selectors import PropertySaleSelector
        from .cash_flow_selectors import CashFlowSelectors
        from ..models import RealEstateInvestorAction, LedgerYear, LedgerAccount, FinancingEntry, InstallmentEntry
        from .ledger_selectors import LedgerSelectors
        from datetime import date
        from django.db.models import Sum

        if reference_date is None:
            reference_date = timezone.now().date()

        ref_year = reference_date.year

        if nav_context is not None:
            year_metrics = nav_context.get("years", {}).get(ref_year)
            if year_metrics is not None:
                return year_metrics

        # 1. Total Property Market Value (Held)
        properties_metrics = PropertySelector.get_properties_for_portfolio(portfolio, reference_date=reference_date, properties=properties)
        total_market_value_held = sum(Decimal(str(m["metrics"]["current_market_value"])) for m in properties_metrics)
        
        assets_breakdown = [
            {
                "name": m["property"].name,
                "value": float(m["metrics"]["current_market_value"]),
                "status": m["property"].status
            } for m in properties_metrics
        ]

        # 2. Key Metrics Calculation (Always calculated as they are expected by views)
        if investments_list is not None:
            total_investments = sum(Decimal(str(action.amount)) for action in investments_list if action.year <= ref_year)
        else:
            investments_qs = RealEstateInvestorAction.objects.filter(portfolio=portfolio, type="PRIMARY_INVESTMENT")
            total_investments = investments_qs.filter(year__lte=ref_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        if sales_metrics is None:
            sales_metrics = PropertySaleSelector.get_sales_for_portfolio(portfolio)
        total_net_proceeds = sum(Decimal(str(s["metrics"]["net_proceeds"])) for s in sales_metrics if s["sale"].sale_date <= reference_date)

        # 3. Cash Reserves Calculation
        cash_reserves = Decimal('0.00')
        is_ledger_sourced = False
        
        # Try Ledger first
        ledger_year = LedgerYear.objects.filter(portfolio=portfolio, year=ref_year).first()
        if ledger_year:
            tb = LedgerSelectors.get_trial_balance(ledger_year)
            cash_acc_data = next((a for a in tb["accounts"] if a["account_name"] == "Cash"), None)
            if cash_acc_data:
                cash_reserves = cash_acc_data["net_balance"]
                is_ledger_sourced = True

        # Fallback to Cash Flow Model + Investments
        if not is_ledger_sourced:
            # Get cumulative CF from model (forcing BASE scenario)
            if cf_data is None:
                cf_data = CashFlowSelectors.get_portfolio_cash_flow(portfolio, end_year=ref_year, force_base_scenario=True)
            cumulative_cf = cf_data["cumulative_cf"].get(ref_year, Decimal('0.00'))
            
            cash_reserves = total_investments + cumulative_cf

        # 4. Yearly Breakdown (For UI visibility)
        cash_change_breakdown = []
        assets_change_breakdown = []
        
        # Primary Investments for current year
        if investments_list is not None:
            yearly_investments = sum(Decimal(str(action.amount)) for action in investments_list if action.year == ref_year)
        else:
            yearly_investments = investments_qs.filter(year=ref_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        if yearly_investments > 0:
            cash_change_breakdown.append({"name": f"Investor Injections ({ref_year})", "amount": float(yearly_investments), "type": "INFLOW"})

        # Pull yearly movements from Cash Flow model
        cf_data_yearly = cf_data if cf_data is not None else CashFlowSelectors.get_portfolio_cash_flow(portfolio, start_year=ref_year, end_year=ref_year, force_base_scenario=True)
        
        # Acquisitions & Sales proceeds (Net)
        total_sales_inflow = cf_data_yearly["portfolio_sales_proceeds"].get(ref_year, Decimal('0.00'))
        
        # Sum up acquisition outflows manually to separate from operating CF for breakdown
        if properties is not None:
            yearly_purchased_props = [p for p in properties if p.purchase_date.year == ref_year]
        else:
            yearly_purchased_props = portfolio.properties.filter(purchase_date__year=ref_year).select_related('financing', 'installment', 'usufruct_details')
            
        for p in yearly_purchased_props:
            cost = p.purchase_price or Decimal('0.00')
            if p.status == "USUFRUCT":
                cost = getattr(p.usufruct_details, 'prep_cost', Decimal('0.00'))
                cash_change_breakdown.append({"name": f"Usufruct Prep: {p.name}", "amount": float(cost), "type": "OUTFLOW"})
            else:
                # Need to handle down payment vs full cash
                down_payment = cost
                if p.financing_type == "MORTGAGED" and hasattr(p, "financing") and p.financing is not None:
                    down_payment = cost - p.financing.loan_amount
                elif p.financing_type == "PRIMARY_INSTALLMENTS" and hasattr(p, "installment") and p.installment is not None:
                    down_payment = p.installment.down_payment
                
                cash_change_breakdown.append({"name": f"Acquisition: {p.name}", "amount": float(down_payment), "type": "OUTFLOW"})
                assets_change_breakdown.append({"name": f"Added Asset: {p.name}", "amount": float(p.purchase_price or 0), "type": "ADDITION"})

        # Add Off-plan Milestones to Cash Change Breakdown (Historical/Projected based on reference_date)
        if properties is not None:
            off_plan_props = [p for p in properties if p.status == "OFF_PLAN"]
        else:
            off_plan_props = portfolio.properties.filter(status="OFF_PLAN")
            
        for opp in off_plan_props:
            if properties is not None:
                milestones_list = opp.milestones.all()
            else:
                milestones_list = opp.milestones.filter(date__year=ref_year)
                
            for m in milestones_list:
                if m.date.year == ref_year and m.date <= reference_date:
                    amount = (m.percentage_of_price / Decimal('100.00')) * (opp.purchase_price or Decimal('0.00'))
                    if amount > 0:
                        cash_change_breakdown.append({"name": f"Milestone: {m.milestone_name} ({opp.name})", "amount": float(amount), "type": "OUTFLOW"})

        if total_sales_inflow > 0:
            cash_change_breakdown.append({"name": f"Sales Proceeds ({ref_year})", "amount": float(total_sales_inflow), "type": "INFLOW"})

        # Operating movements
        yearly_noi = cf_data_yearly["portfolio_noi"].get(ref_year, Decimal('0.00'))
        yearly_taxes = cf_data_yearly["portfolio_taxes"].get(ref_year, Decimal('0.00'))
        
        # Debt service (we need to sum from metadata)
        total_debt_service = Decimal('0.00')
        for p_id, p_data in cf_data_yearly["properties"].items():
            meta = p_data["metadata"].get(ref_year)
            if meta:
                total_debt_service += (meta.get("debt_service", Decimal('0.00')) + meta.get("installments", Decimal('0.00')))

        if yearly_noi != 0:
            cash_change_breakdown.append({"name": f"Net Operating Income ({ref_year})", "amount": float(abs(yearly_noi)), "type": "INFLOW" if yearly_noi > 0 else "OUTFLOW"})
        if total_debt_service > 0:
            cash_change_breakdown.append({"name": f"Debt Service ({ref_year})", "amount": float(total_debt_service), "type": "OUTFLOW"})
        if yearly_taxes > 0:
            cash_change_breakdown.append({"name": f"Taxes ({ref_year})", "amount": float(yearly_taxes), "type": "OUTFLOW"})

        # 4. Liabilities Calculation (Mortgages, Installments & Off-plan)
        total_liabilities = Decimal('0.00')
        from .financing_selectors import FinancingSelectors
        from .installment_selectors import InstallmentSelectors

        # Mortgages
        if properties is not None:
            financing_entries = [p.financing for p in properties if getattr(p, 'financing', None) is not None and p.financing.loan_start_date <= reference_date]
        else:
            financing_entries = FinancingEntry.objects.filter(property__portfolio=portfolio, loan_start_date__lte=reference_date)
            
        for f in financing_entries:
            schedule = FinancingSelectors.get_amortization_schedule(f)
            # Find the balance at the end of the last period before or on reference_date
            months_per_period = 12 // f.payments_per_year

            # Find last payment before reference_date
            last_balance = f.loan_amount
            for item in schedule:
                period = item['period']
                total_months_offset = months_per_period * (period - 1)
                payment_date = date(f.loan_start_date.year + (f.loan_start_date.month + total_months_offset - 1) // 12, 
                                    (f.loan_start_date.month + total_months_offset - 1) % 12 + 1, 1)

                if payment_date <= reference_date:
                    last_balance = Decimal(str(item['ending_balance']))
                else:
                    break
            total_liabilities += last_balance

        # Installments
        if properties is not None:
            installment_entries = [p.installment for p in properties if getattr(p, 'installment', None) is not None and p.installment.start_date <= reference_date]
        else:
            installment_entries = InstallmentEntry.objects.filter(property__portfolio=portfolio, start_date__lte=reference_date)
            
        for i in installment_entries:
            schedule = InstallmentSelectors.get_installment_schedule(i)
            # Find the balance after the last payment before reference_date
            total_paid = Decimal('0.00')
            total_principal = i.property.purchase_price - i.down_payment
            for item in schedule:
                # item['date'] is "YYYY-MM"
                y, m = map(int, item['date'].split('-'))
                payment_date = date(y, m, 1)
                if payment_date <= reference_date:
                    total_paid += Decimal(str(item['payment']))
                else:
                    break
            total_liabilities += max(Decimal('0.00'), total_principal - total_paid)

        # Off-plan Payables
        for opp in off_plan_props:
            if opp.purchase_date <= reference_date:
                total_price = opp.purchase_price or Decimal('0.00')
                if properties is not None:
                    unpaid_milestones = [m for m in opp.milestones.all() if m.date > reference_date and m.date > opp.purchase_date]
                else:
                    unpaid_milestones = opp.milestones.filter(date__gt=reference_date).filter(date__gt=opp.purchase_date)
                total_liabilities += sum((m.percentage_of_price / Decimal('100.00')) * total_price for m in unpaid_milestones)

        # 5. NAV Calculation
        # True NAV = (Assets + Cash) - Liabilities
        nav = total_market_value_held + cash_reserves - total_liabilities

        # Total Units
        if investments_list is not None:
            total_units_at_ref = sum(float(inv.units) for inv in investments_list if inv.year <= ref_year)
        else:
            total_units_at_ref = PortfolioSelectors.get_total_units_at_year(portfolio, ref_year)
            
        if total_units_at_ref == 0:
            total_units_at_ref = float(portfolio.total_units)

        return {
            "total_market_value_held": float(total_market_value_held),
            "total_investments": float(total_investments),
            "total_net_proceeds": float(total_net_proceeds),
            "cash_reserves": float(cash_reserves),
            "total_liabilities": float(total_liabilities),
            "nav": float(nav),
            "total_units": total_units_at_ref,
            "price_per_unit": float(nav / Decimal(str(total_units_at_ref))) if total_units_at_ref > 0 else 1.0,
            "assets_breakdown": assets_breakdown,
            "cash_change_breakdown": cash_change_breakdown,
            "assets_change_breakdown": assets_change_breakdown,
            "is_ledger_sourced": is_ledger_sourced
        }
