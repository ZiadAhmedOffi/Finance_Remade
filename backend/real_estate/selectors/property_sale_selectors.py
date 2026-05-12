from decimal import Decimal
from ..models import PropertySale, RealEstatePortfolio
from .financing_selectors import FinancingSelectors

class PropertySaleSelector:
    @staticmethod
    def get_sales_for_portfolio(portfolio: RealEstatePortfolio) -> list:
        """
        Retrieves all property sales for a portfolio with calculated financial metrics.
        """
        sales = PropertySale.objects.filter(
            property__portfolio=portfolio
        ).select_related('property', 'property__financing')
        
        results = []
        for sale in sales:
            results.append(PropertySaleSelector.calculate_sale_metrics(sale))
        
        return results

    @staticmethod
    def calculate_sale_metrics(sale: PropertySale) -> dict:
        """
        Calculates derived metrics for a single property sale.
        """
        from ..calculation import PropertyDataCalc
        
        selling_price = sale.selling_price
        selling_fee_pct = sale.selling_fee_percentage
        
        selling_costs = PropertyDataCalc.selling_costs(selling_price, selling_fee_pct)
        cost_basis = PropertyDataCalc.total_cost_basis(sale.property.purchase_price, sale.property.acq_fee_percentage)
        
        # Calculate Loan Payoff
        loan_payoff = Decimal('0.00')
        if hasattr(sale.property, 'financing'):
            financing = sale.property.financing
            schedule = FinancingSelectors.get_amortization_schedule(financing)
            
            start_date = financing.loan_start_date
            sale_date = sale.sale_date
            
            if sale_date > start_date:
                months_passed = (sale_date.year - start_date.year) * 12 + (sale_date.month - start_date.month)
                months_per_period = 12 // financing.payments_per_year
                periods_passed = months_passed // months_per_period
                
                if periods_passed > 0:
                    if periods_passed >= len(schedule):
                        loan_payoff = Decimal('0.00')
                    else:
                        loan_payoff = schedule[periods_passed - 1]['ending_balance']
                else:
                    loan_payoff = financing.loan_amount
            else:
                loan_payoff = financing.loan_amount

        net_proceeds = PropertyDataCalc.net_proceeds(selling_price, selling_costs, loan_payoff)
        realized_gain = PropertyDataCalc.realized_gain(selling_price, cost_basis, selling_costs)
        roi = (selling_price / cost_basis) if cost_basis > 0 else Decimal('0.00')
        
        return {
            "sale": sale,
            "metrics": {
                "selling_costs": selling_costs,
                "cost_basis": cost_basis,
                "loan_payoff": loan_payoff,
                "net_proceeds": net_proceeds,
                "realized_gain": realized_gain,
                "roi": round(roi, 4),
            }
        }
