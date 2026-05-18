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
        Calculates total capital required per year for the portfolio.
        Returns a dict of year -> { "total": float, "breakdown": [ { "name": str, "amount": float, "type": str } ] }
        """
        from .off_plan_selectors import OffPlanSelectors
        from .financing_selectors import FinancingSelectors
        from .installment_selectors import InstallmentSelectors
        from decimal import Decimal

        yearly_data = {}
        properties = portfolio.properties.all().select_related('financing', 'off_plan_details', 'installment')

        def add_to_year(yr, amount, name, payment_type):
            if yr not in yearly_data:
                yearly_data[yr] = {"total": 0.0, "breakdown": []}
            yearly_data[yr]["total"] += amount
            yearly_data[yr]["breakdown"].append({
                "name": name,
                "amount": amount,
                "type": payment_type
            })

        for prop in properties:
            if prop.status == "OFF_PLAN":
                # Off-Plan properties use their milestones
                schedule_data = OffPlanSelectors.get_payment_schedule(prop)
                for item in schedule_data["schedule"]:
                    if item["milestone"] != "Sale at Completion":
                        yr = item["date"].year
                        amount = abs(float(item["cash_flow"]))
                        add_to_year(yr, amount, prop.name, f"Off-Plan Milestone: {item['milestone']}")
            
            elif prop.financing_type == "MORTGAGED":
                # Mortgaged properties use financing model
                try:
                    financing = prop.financing
                    # Down Payment in purchase year
                    dp = float(prop.purchase_price - financing.loan_amount)
                    yr_start = prop.purchase_date.year
                    add_to_year(yr_start, dp, prop.name, "Mortgage Down Payment")
                    
                    # Annual Debt Service
                    schedule = FinancingSelectors.get_amortization_schedule(financing)
                    months_per_period = 12 // financing.payments_per_year
                    start_date = financing.loan_start_date
                    
                    # Aggregate by year
                    annual_payments = {}
                    for item in schedule:
                        period = item['period']
                        total_months_offset = months_per_period * (period - 1)
                        year_offset = (start_date.month + total_months_offset - 1) // 12
                        yr = start_date.year + year_offset
                        
                        amount = float(item["periodic_payment"])
                        annual_payments[yr] = annual_payments.get(yr, 0.0) + amount
                    
                    for yr, amount in annual_payments.items():
                        add_to_year(yr, amount, prop.name, "Mortgage Debt Service")
                except:
                    # Fallback to ALL_CASH if no financing entry found
                    yr = prop.purchase_date.year
                    add_to_year(yr, float(prop.purchase_price), prop.name, "Purchase (Cash Fallback)")

            elif prop.financing_type == "PRIMARY_INSTALLMENTS":
                # Primary Sales with Installments
                try:
                    installment = prop.installment
                    # Down Payment in purchase year
                    dp = float(installment.down_payment)
                    yr_start = prop.purchase_date.year
                    add_to_year(yr_start, dp, prop.name, "Installment Down Payment")

                    # Annual Installments
                    schedule = InstallmentSelectors.get_installment_schedule(installment)
                    months_per_period = 12 // installment.payments_per_year
                    start_date = installment.start_date

                    annual_payments = {}
                    for item in schedule:
                        # item['date'] is "YYYY-MM"
                        yr = int(item['date'].split('-')[0])
                        amount = float(item["payment"])
                        annual_payments[yr] = annual_payments.get(yr, 0.0) + amount
                    
                    for yr, amount in annual_payments.items():
                        add_to_year(yr, amount, prop.name, "Installment Payment")
                except:
                    # Fallback to ALL_CASH if no installment entry found
                    yr = prop.purchase_date.year
                    add_to_year(yr, float(prop.purchase_price), prop.name, "Purchase (Cash Fallback)")
            
            else:
                # ALL_CASH HELD/SOLD
                yr = prop.purchase_date.year
                add_to_year(yr, float(prop.purchase_price), prop.name, "Full Cash Purchase")

        return yearly_data
