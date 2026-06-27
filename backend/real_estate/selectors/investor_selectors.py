from ..models import RealEstateInvestorAction, RealEstateInvestorStats, RealEstatePortfolio
from django.db.models import Sum

class RealEstateInvestorSelector:
    @staticmethod
    def get_investor_actions(portfolio: RealEstatePortfolio):
        """
        Returns all investor actions for a portfolio.
        """
        return RealEstateInvestorAction.objects.filter(portfolio=portfolio).select_related('investor', 'investor_selling', 'investor_sold_to').order_by('year', 'created_at')

    @staticmethod
    def get_investor_stats(portfolio: RealEstatePortfolio):
        """
        Returns stats for all investors in a portfolio.
        """
        return RealEstateInvestorStats.objects.filter(portfolio=portfolio).select_related('investor').order_by('-amount_invested')

    @staticmethod
    def get_investor_action_by_id(action_id):
        try:
            return RealEstateInvestorAction.objects.get(id=action_id)
        except RealEstateInvestorAction.DoesNotExist:
            return None

    @staticmethod
    def calculate_investor_units(investor, portfolio):
        """
        Calculates current units for an investor in a portfolio.
        """
        stats = RealEstateInvestorStats.objects.filter(investor=investor, portfolio=portfolio).first()
        return float(stats.units) if stats else 0.0

    @staticmethod
    def get_primary_units_by_year(portfolio):
        """
        Returns a dict of year -> units from primary investments.
        """
        actions = RealEstateInvestorAction.objects.filter(portfolio=portfolio, type="PRIMARY_INVESTMENT")
        units_by_year = {}
        for action in actions:
            yr = action.year
            units_by_year[yr] = units_by_year.get(yr, 0.0) + float(action.units)
        return units_by_year

    @staticmethod
    def calculate_portfolio_capital_required(portfolio: RealEstatePortfolio):
        """
        [DEPRECATED] Use get_unified_capital_pipeline instead.
        Calculates total capital required per year for the portfolio.
        Returns a dict of year -> { "total": float, "breakdown": [ { "name": str, "amount": float, "type": str } ] }
        """
        # Kept for backward compatibility if any views still use it directly
        pipeline = RealEstateInvestorSelector.get_unified_capital_pipeline(portfolio)
        return {yr: {"total": float(data["net_required"]), "breakdown": data["breakdown"]} for yr, data in pipeline.items()}

    @staticmethod
    def get_unified_capital_pipeline(portfolio: RealEstatePortfolio, cf_data=None):
        """
        Unified pipeline blending Ledger actuals (for closed years) and 
        Cash Flow projections (for open/future years).
        
        Returns: { 
            year: { 
                "net_required": Decimal, 
                "uses": Decimal, 
                "sources": Decimal, 
                "breakdown": list,
                "is_actuals": bool 
            } 
        }
        """
        from .cash_flow_selectors import CashFlowSelectors
        from .ledger_selectors import LedgerSelectors
        from ..models import LedgerYear
        from decimal import Decimal

        assumptions = portfolio.assumptions
        inception_year = assumptions.inception_date.year
        end_year = inception_year + assumptions.forecast_horizon - 1
        
        # 1. Get Projected Data (Base Scenario)
        if cf_data is None:
            cf_data = CashFlowSelectors.get_portfolio_cash_flow(portfolio, force_base_scenario=True)
        
        # 2. Get Closed Ledger Years
        closed_years = LedgerYear.objects.filter(portfolio=portfolio, is_closed=True).values_list('year', flat=True)
        
        pipeline = {}
        cumulative_surplus = Decimal('0.00')

        for yr in range(inception_year, end_year + 1):
            is_actuals = yr in closed_years
            uses = Decimal('0.00')
            sources = Decimal('0.00')
            breakdown = []
            
            # ... [Logic to populate uses, sources, breakdown is the same] ...
            # Wait, I need to keep the logic for uses/sources from the previous turn
            
            if is_actuals:
                # --- PULL FROM LEDGER ---
                ledger_year = LedgerYear.objects.get(portfolio=portfolio, year=yr)
                tb = LedgerSelectors.get_trial_balance(ledger_year)
                for acc in tb["accounts"]:
                    debit, credit = Decimal(str(acc["debit"])), Decimal(str(acc["credit"]))
                    if acc["account_type"] == "EXPENSE" and debit > 0:
                        amt = debit - credit
                        uses += amt
                        breakdown.append({"name": acc["account_name"], "amount": float(amt), "type": "USE"})
                    elif acc["account_type"] == "REVENUE" and credit > 0:
                        amt = credit - debit
                        sources += amt
                        breakdown.append({"name": acc["account_name"], "amount": float(amt), "type": "SOURCE"})
                    elif acc["account_type"] == "ASSET" and acc["account_name"] != "Cash":
                        if debit > credit:
                            amt = debit - credit
                            uses += amt
                            breakdown.append({"name": f"Asset Addition: {acc['account_name']}", "amount": float(amt), "type": "USE"})
                        elif credit > debit:
                            amt = credit - debit
                            sources += amt
                            breakdown.append({"name": f"Asset Disposal: {acc['account_name']}", "amount": float(amt), "type": "SOURCE"})
                    elif acc["account_type"] == "LIABILITY":
                        if debit > credit:
                            amt = debit - credit
                            uses += amt
                            breakdown.append({"name": f"Debt Repayment: {acc['account_name']}", "amount": float(amt), "type": "USE"})
                        elif credit > debit:
                            amt = credit - debit
                            sources += amt
                            breakdown.append({"name": f"Loan Drawdown: {acc['account_name']}", "amount": float(amt), "type": "SOURCE"})
                    elif acc["account_type"] == "EQUITY" and acc["account_name"] == "Retained Earnings" and credit > debit:
                        amt = credit - debit
                        sources += amt
                        breakdown.append({"name": "Realized Gain on Sales", "amount": float(amt), "type": "SOURCE"})
            else:
                # --- PULL FROM CASH FLOW MODEL ---
                total_opex, total_rent, total_debt_service, total_taxes, total_acq = Decimal('0.00'), Decimal('0.00'), Decimal('0.00'), Decimal('0.00'), Decimal('0.00')
                total_sales = cf_data["portfolio_sales_proceeds"].get(yr, Decimal('0.00'))
                for prop_id, prop_data in cf_data["properties"].items():
                    meta = prop_data["metadata"].get(yr)
                    if meta:
                        total_rent += meta.get("effective_rent", Decimal('0.00'))
                        total_opex += meta.get("opex", Decimal('0.00'))
                        total_debt_service += (meta.get("debt_service", Decimal('0.00')) + meta.get("installments", Decimal('0.00')))
                        total_taxes += meta.get("taxes", Decimal('0.00'))
                        total_acq += (meta.get("purchase_price", Decimal('0.00')) + meta.get("down_payment", Decimal('0.00')) + meta.get("construction_costs", Decimal('0.00')))
                if total_rent > 0:
                    sources += total_rent
                    breakdown.append({"name": "Projected Rental Income", "amount": float(total_rent), "type": "SOURCE"})
                if total_sales > 0:
                    sources += total_sales
                    breakdown.append({"name": "Projected Sale Proceeds", "amount": float(total_sales), "type": "SOURCE"})
                if total_acq > 0:
                    uses += total_acq
                    breakdown.append({"name": "Projected Acquisitions/CapEx", "amount": float(total_acq), "type": "USE"})
                if total_opex > 0:
                    uses += total_opex
                    breakdown.append({"name": "Projected Opex", "amount": float(total_opex), "type": "USE"})
                if total_debt_service > 0:
                    uses += total_debt_service
                    breakdown.append({"name": "Projected Debt Service", "amount": float(total_debt_service), "type": "USE"})
                if total_taxes > 0:
                    uses += total_taxes
                    breakdown.append({"name": "Projected Taxes", "amount": float(total_taxes), "type": "USE"})

            # --- NET REQUIRED CALCULATION (CUMULATIVE AWARE) ---
            # Current year net cash flow (Sources - Uses)
            net_cash_flow = sources - uses
            
            # Cumulative position before any new capital injection this year
            position_before_call = cumulative_surplus + net_cash_flow
            
            net_required = Decimal('0.00')
            if position_before_call < 0:
                # We have a shortfall that must be met by a capital call
                net_required = abs(position_before_call)
                # After the call, the surplus is zero (we met the requirement exactly)
                cumulative_surplus = Decimal('0.00')
            else:
                # We have enough cash to cover everything, or even a surplus
                net_required = Decimal('0.00')
                cumulative_surplus = position_before_call

            pipeline[yr] = {
                "net_required": net_required,
                "uses": uses,
                "sources": sources,
                "breakdown": breakdown,
                "is_actuals": is_actuals
            }
        return pipeline

        return pipeline
