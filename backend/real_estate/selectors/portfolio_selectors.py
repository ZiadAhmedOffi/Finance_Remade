from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from ..models import RealEstatePortfolio

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
    def get_portfolio_nav_metrics(portfolio, reference_date=None):
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

        if reference_date is None:
            reference_date = timezone.now().date()

        ref_year = reference_date.year

        # 1. Total Property Market Value (Held)
        properties_metrics = PropertySelector.get_properties_for_portfolio(portfolio, reference_date=reference_date)
        total_market_value_held = sum(Decimal(str(m["metrics"]["current_market_value"])) for m in properties_metrics)
        
        assets_breakdown = [
            {
                "name": m["property"].name,
                "value": float(m["metrics"]["current_market_value"]),
                "status": m["property"].status
            } for m in properties_metrics
        ]

        # 2. Key Metrics Calculation (Always calculated as they are expected by views)
        investments_qs = RealEstateInvestorAction.objects.filter(portfolio=portfolio, type="PRIMARY_INVESTMENT")
        total_investments = investments_qs.filter(year__lte=ref_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

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
            cf_data = CashFlowSelectors.get_portfolio_cash_flow(portfolio, end_year=ref_year, force_base_scenario=True)
            cumulative_cf = cf_data["cumulative_cf"].get(ref_year, Decimal('0.00'))
            
            cash_reserves = total_investments + cumulative_cf

        # 4. Yearly Breakdown (For UI visibility)
        cash_change_breakdown = []
        assets_change_breakdown = []
        
        # Primary Investments for current year
        yearly_investments = investments_qs.filter(year=ref_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        if yearly_investments > 0:
            cash_change_breakdown.append({"name": f"Investor Injections ({ref_year})", "amount": float(yearly_investments), "type": "INFLOW"})

        # Pull yearly movements from Cash Flow model
        cf_data_yearly = CashFlowSelectors.get_portfolio_cash_flow(portfolio, start_year=ref_year, end_year=ref_year, force_base_scenario=True)
        
        # Acquisitions & Sales proceeds (Net)
        total_sales_inflow = cf_data_yearly["portfolio_sales_proceeds"].get(ref_year, Decimal('0.00'))
        
        # Sum up acquisition outflows manually to separate from operating CF for breakdown
        yearly_purchased_props = portfolio.properties.filter(purchase_date__year=ref_year).select_related('financing', 'installment', 'usufruct_details')
        for p in yearly_purchased_props:
            cost = p.purchase_price or Decimal('0.00')
            if p.status == "USUFRUCT":
                cost = getattr(p.usufruct_details, 'prep_cost', Decimal('0.00'))
                cash_change_breakdown.append({"name": f"Usufruct Prep: {p.name}", "amount": float(cost), "type": "OUTFLOW"})
            else:
                # Need to handle down payment vs full cash
                down_payment = cost
                if p.financing_type == "MORTGAGED" and hasattr(p, "financing"):
                    down_payment = cost - p.financing.loan_amount
                elif p.financing_type == "PRIMARY_INSTALLMENTS" and hasattr(p, "installment"):
                    down_payment = p.installment.down_payment
                
                cash_change_breakdown.append({"name": f"Acquisition: {p.name}", "amount": float(down_payment), "type": "OUTFLOW"})
                assets_change_breakdown.append({"name": f"Added Asset: {p.name}", "amount": float(p.purchase_price or 0), "type": "ADDITION"})

        # Add Off-plan Milestones to Cash Change Breakdown (Historical/Projected based on reference_date)
        off_plan_props = portfolio.properties.filter(status="OFF_PLAN")
        for opp in off_plan_props:
            for m in opp.milestones.filter(date__year=ref_year):
                if m.date <= reference_date:
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
        financing_entries = FinancingEntry.objects.filter(property__portfolio=portfolio, loan_start_date__lte=reference_date)
        for f in financing_entries:
            schedule = FinancingSelectors.get_amortization_schedule(f)
            # Find the balance at the end of the last period before or on reference_date
            # Or simpler: find the first period that starts AFTER reference_date and take prev balance
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
                unpaid_milestones = opp.milestones.filter(date__gt=reference_date).filter(date__gt=opp.purchase_date)
                total_liabilities += sum((m.percentage_of_price / Decimal('100.00')) * total_price for m in unpaid_milestones)

        # 5. NAV Calculation
        # True NAV = (Assets + Cash) - Liabilities
        nav = total_market_value_held + cash_reserves - total_liabilities

        # Total Units
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

