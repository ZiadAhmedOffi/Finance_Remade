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
        Cash Reserves = Total Primary Investments - Sum(All Property Purchase Prices) + Sum(All Property Sale Net Proceeds)
        """
        from .property_selectors import PropertySelector
        from .property_sale_selectors import PropertySaleSelector
        from ..models import RealEstateInvestorAction
        from datetime import date

        if reference_date is None:
            reference_date = timezone.now().date()

        ref_year = reference_date.year

        # 1. Total Property Market Value (Held) - Use historical calculation if reference_date provided
        properties_metrics = PropertySelector.get_properties_for_portfolio(portfolio, reference_date=reference_date)
        total_market_value_held = sum(Decimal(str(m["metrics"]["current_market_value"])) for m in properties_metrics)

        
        assets_breakdown = [
            {
                "name": m["property"].name,
                "value": float(m["metrics"]["current_market_value"]),
                "status": m["property"].status
            } for m in properties_metrics
        ]

        # 2. Total Primary Investments
        investments_qs = RealEstateInvestorAction.objects.filter(portfolio=portfolio, type="PRIMARY_INVESTMENT")
        total_investments = investments_qs.filter(year__lte=ref_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        yearly_investments = investments_qs.filter(year=ref_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # 3. Sum of all Property Purchase Prices (to calculate cash spent)
        all_properties = portfolio.properties.all()
        total_purchase_price = all_properties.filter(purchase_date__lte=reference_date).aggregate(total=Sum('purchase_price'))['total'] or Decimal('0.00')
        yearly_purchase_price = all_properties.filter(purchase_date__year=ref_year).aggregate(total=Sum('purchase_price'))['total'] or Decimal('0.00')
        yearly_purchased_props = all_properties.filter(purchase_date__year=ref_year)

        # 4. Total Net Proceeds from Sales
        sales_metrics = PropertySaleSelector.get_sales_for_portfolio(portfolio)
        total_net_proceeds = sum(Decimal(str(s["metrics"]["net_proceeds"])) for s in sales_metrics if s["sale"].sale_date <= reference_date)
        yearly_net_proceeds = sum(Decimal(str(s["metrics"]["net_proceeds"])) for s in sales_metrics if s["sale"].sale_date.year == ref_year)
        yearly_sales = [s for s in sales_metrics if s["sale"].sale_date.year == ref_year]

        # 5. Cash Reserves
        cash_reserves = Decimal(str(total_investments)) - Decimal(str(total_purchase_price)) + Decimal(str(total_net_proceeds))
        
        # Build yearly change breakdown
        cash_change_breakdown = []
        assets_change_breakdown = []

        if yearly_investments > 0:
            cash_change_breakdown.append({"name": f"Investor Injections ({ref_year})", "amount": float(yearly_investments), "type": "INFLOW"})
        
        for p in yearly_purchased_props:
            cash_change_breakdown.append({"name": f"Purchase Outflow: {p.name}", "amount": float(p.purchase_price), "type": "OUTFLOW"})
            assets_change_breakdown.append({"name": f"Added Asset: {p.name}", "amount": float(p.purchase_price), "type": "ADDITION"})
            
        for s in yearly_sales:
            sale_obj = s["sale"]
            cash_change_breakdown.append({"name": f"Sale Inflow: {sale_obj.property.name}", "amount": float(s["metrics"]["net_proceeds"]), "type": "INFLOW"})
            assets_change_breakdown.append({"name": f"Removed Asset: {sale_obj.property.name}", "amount": float(sale_obj.selling_price), "type": "REMOVAL"})

        # 6. NAV
        nav = 0.0
        if cash_reserves > 0:
            nav = total_market_value_held + cash_reserves
        else:
            nav = total_market_value_held

        # Total Units at reference date
        total_units_at_ref = PortfolioSelectors.get_total_units_at_year(portfolio, ref_year)
        if total_units_at_ref == 0:
            total_units_at_ref = float(portfolio.total_units)

        return {
            "total_market_value_held": total_market_value_held,
            "total_investments": total_investments,
            "total_net_proceeds": total_net_proceeds,
            "cash_reserves": cash_reserves,
            "nav": nav,
            "total_units": total_units_at_ref,
            "price_per_unit": (nav / Decimal(str(total_units_at_ref))) if total_units_at_ref > 0 else Decimal('1.00'),
            "assets_breakdown": assets_breakdown,
            "cash_change_breakdown": cash_change_breakdown,
            "assets_change_breakdown": assets_change_breakdown
        }
