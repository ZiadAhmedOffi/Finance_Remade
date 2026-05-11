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
        
        Metrics:
        - Selling Costs (Selling Price * Selling Fee %)
        - Cost Basis (The total cost basis for the property)
        - Loan Payoff (Ending balance of loan at sale date)
        - Net Proceeds (Selling Price - Selling Costs - Loan Payoff)
        - Realized Gain (Selling Price - Cost Basis - Selling Costs)
        - ROI (Selling Price / Cost Basis)
        """
        selling_price = sale.selling_price
        selling_fee_pct = sale.selling_fee_percentage / Decimal('100')
        
        selling_costs = (selling_price * selling_fee_pct).quantize(Decimal('0.01'))
        cost_basis = sale.property.purchase_price + sale.property.acq_fee_percentage / Decimal('100') * sale.property.purchase_price
        
        # Calculate Loan Payoff
        loan_payoff = Decimal('0.00')
        if hasattr(sale.property, 'financing'):
            financing = sale.property.financing
            # Get amortization schedule
            schedule = FinancingSelectors.get_amortization_schedule(financing)
            
            # Find the ending balance at the sale date
            # We need to determine how many periods have passed between loan start and sale date
            start_date = financing.loan_start_date
            sale_date = sale.sale_date
            
            if sale_date > start_date:
                # Calculate months passed
                months_passed = (sale_date.year - start_date.year) * 12 + (sale_date.month - start_date.month)
                # periods passed = months_passed / (12 / payments_per_year)
                months_per_period = 12 // financing.payments_per_year
                periods_passed = months_passed // months_per_period
                
                if periods_passed > 0:
                    # Find the last period that occurred before or on sale date
                    # If periods_passed exceeds schedule length, it's fully paid (balance 0)
                    if periods_passed >= len(schedule):
                        loan_payoff = Decimal('0.00')
                    else:
                        # Schedule is 0-indexed in our implementation (range 1 to total_periods)
                        # schedule[periods_passed - 1] corresponds to 'period' = periods_passed
                        loan_payoff = schedule[periods_passed - 1]['ending_balance']
                else:
                    loan_payoff = financing.loan_amount
            else:
                loan_payoff = financing.loan_amount

        net_proceeds = selling_price - selling_costs - loan_payoff
        realized_gain = selling_price - cost_basis - selling_costs
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
