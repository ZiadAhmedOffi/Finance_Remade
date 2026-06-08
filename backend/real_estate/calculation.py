# This file contains all calculation logic for derived properties
from decimal import Decimal
from typing import Optional

class PropertyDataCalc:
    @staticmethod
    def acq_fee(purchase_price: Decimal, acq_fee_percentage: Decimal) -> Decimal:
        return (purchase_price * (acq_fee_percentage / Decimal('100'))).quantize(Decimal('0.01'))
    
    @staticmethod
    def total_cost_basis(purchase_price: Decimal, acq_fee_percentage: Decimal) -> Decimal:
        return (purchase_price + PropertyDataCalc.acq_fee(purchase_price, acq_fee_percentage)).quantize(Decimal('0.01'))
    
    @staticmethod
    def days_held(purchase_date, reference_date) -> int:
        if reference_date < purchase_date:
            return 0
        return (reference_date - purchase_date).days
    
    @staticmethod
    def years_held(purchase_date, reference_date) -> Decimal:
        days = PropertyDataCalc.days_held(purchase_date, reference_date)
        return (Decimal(str(days)) / Decimal('365.25'))
    
    @staticmethod
    def market_value(purchase_price: Decimal, appreciation_rate: Decimal, years_held: Decimal) -> Decimal:
        # Formula: P * (1 + r)^t
        growth_factor = float(Decimal('1') + (appreciation_rate / Decimal('100'))) ** float(years_held)
        return (purchase_price * Decimal(str(round(growth_factor, 10)))).quantize(Decimal('0.01'))

    @staticmethod
    def effective_rent(monthly_rent: Decimal, vacancy_rate: Decimal, years_held: Decimal, rental_growth_rate: Decimal = Decimal('0'), months_in_period: int = 12) -> Decimal:
        # Appreciate monthly rent if growth rate > 0
        if rental_growth_rate > 0:
            growth_factor = float(Decimal('1') + (rental_growth_rate / Decimal('100'))) ** float(years_held)
            appreciated_monthly_rent = monthly_rent * Decimal(str(round(growth_factor, 10)))
        else:
            appreciated_monthly_rent = monthly_rent
        
        base_rent = appreciated_monthly_rent * Decimal(str(months_in_period))
        return (base_rent * (Decimal('1') - (vacancy_rate / Decimal('100')))).quantize(Decimal('0.01'))

    @staticmethod
    def management_fees(effective_rent: Decimal, mgmt_fee_percentage: Decimal) -> Decimal:
        return (Decimal(str(effective_rent)) * (Decimal(str(mgmt_fee_percentage)) / Decimal('100'))).quantize(Decimal('0.01'))
    
    @staticmethod
    def maintenance_fees(market_value: Decimal, maint_fee_percentage: Decimal) -> Decimal:
        return (Decimal(str(market_value)) * (Decimal(str(maint_fee_percentage)) / Decimal('100'))).quantize(Decimal('0.01'))
    
    @staticmethod
    def total_operational_expenses(effective_rent: Decimal, market_value: Decimal, mgmt_fee_percentage: Decimal, maint_fee_percentage: Decimal, other_expenses: Decimal) -> Decimal:
        mgmt = PropertyDataCalc.management_fees(effective_rent, mgmt_fee_percentage)
        maint = PropertyDataCalc.maintenance_fees(market_value, maint_fee_percentage)
        return (mgmt + maint + Decimal(str(other_expenses))).quantize(Decimal('0.01'))
    
    @staticmethod
    def noi(effective_rent: Decimal, opex: Decimal) -> Decimal:
        return (effective_rent - opex).quantize(Decimal('0.01'))

    @staticmethod
    def gross_yield(effective_rent: Decimal, purchase_price: Decimal) -> Decimal:
        if purchase_price == 0:
            return Decimal('0.00')
        return ((effective_rent / purchase_price) * Decimal('100')).quantize(Decimal('0.01'))
    
    @staticmethod
    def net_yield(noi: Decimal, market_value: Decimal) -> Decimal:
        if market_value == 0:
            return Decimal('0.00')
        return ((noi / market_value) * Decimal('100')).quantize(Decimal('0.01'))

    @staticmethod
    def selling_costs(selling_price: Decimal, selling_fee_percentage: Decimal) -> Decimal:
        return (selling_price * (selling_fee_percentage / Decimal('100'))).quantize(Decimal('0.01'))
    
    @staticmethod
    def net_proceeds(selling_price: Decimal, selling_costs: Decimal, loan_payoff: Decimal) -> Decimal:
        return (selling_price - selling_costs - loan_payoff).quantize(Decimal('0.01'))
    
    @staticmethod
    def realized_gain(selling_price: Decimal, cost_basis: Decimal, selling_costs: Decimal) -> Decimal:
        return (selling_price - cost_basis - selling_costs).quantize(Decimal('0.01'))

    @staticmethod
    def ltv(loan_amount: Decimal, purchase_price: Decimal) -> Decimal:
        if purchase_price == 0:
            return Decimal('0.00')
        return ((loan_amount / purchase_price) * Decimal('100')).quantize(Decimal('0.01'))

    @staticmethod
    def value_at_completion(purchase_price: Decimal, appreciation_rate_at_completion: Decimal) -> Decimal:
        return (purchase_price * (Decimal('1') + (appreciation_rate_at_completion / Decimal('100')))).quantize(Decimal('0.01'))

    @staticmethod
    def cost_per_sqm(purchase_price: Decimal, size: Decimal) -> Decimal:
        if size == 0:
            return Decimal('0.00')
        return (purchase_price / size).quantize(Decimal('0.01'))

    @staticmethod
    def portfolio_occupancy(avg_vacancy_rate: Decimal) -> Decimal:
        return (Decimal('100') - avg_vacancy_rate).quantize(Decimal('0.01'))

    # Usufruct Calculations
    @staticmethod
    def usufruct_annual_rent(inflow_monthly_rent: Decimal, appreciation_rate: Decimal, years_held: Decimal, is_first_year: bool = False) -> Decimal:
        if is_first_year:
            return Decimal('0.00')
        growth_factor = float(Decimal('1') + (Decimal(str(appreciation_rate)) / Decimal('100'))) ** float(years_held)
        appreciated_monthly_rent = inflow_monthly_rent * Decimal(str(round(growth_factor, 10)))
        return (appreciated_monthly_rent * Decimal('12')).quantize(Decimal('0.01'))

    @staticmethod
    def usufruct_effective_rent(annual_rent: Decimal, vacancy_rate: Decimal) -> Decimal:
        return (annual_rent * (Decimal('1') - (Decimal(str(vacancy_rate)) / Decimal('100')))).quantize(Decimal('0.01'))

    @staticmethod
    def usufruct_noi(effective_rent: Decimal, outflow_monthly_rent: Decimal, outflow_appreciation_rate: Decimal, annual_ops_cost: Decimal, insurance_cost: Decimal, years_held: Decimal, is_first_year: bool = False) -> Decimal:
        growth_factor = float(Decimal('1') + (Decimal(str(outflow_appreciation_rate)) / Decimal('100'))) ** float(years_held)
        appreciated_outflow_monthly_rent = outflow_monthly_rent * Decimal(str(round(growth_factor, 10)))
        outflow_annual = appreciated_outflow_monthly_rent * Decimal('12')
        
        if is_first_year:
            # First year: outflows include insurance_cost
            return (effective_rent - outflow_annual - Decimal(str(annual_ops_cost)) - Decimal(str(insurance_cost))).quantize(Decimal('0.01'))
        else:
            # Following years: outflows exclude insurance_cost
            return (effective_rent - outflow_annual - Decimal(str(annual_ops_cost))).quantize(Decimal('0.01'))

    @staticmethod
    def usufruct_gross_yield(effective_rent: Decimal, prep_cost: Decimal) -> Decimal:
        if prep_cost == 0:
            return Decimal('0.00')
        return ((effective_rent / prep_cost) * Decimal('100')).quantize(Decimal('0.01'))

    @staticmethod
    def usufruct_net_yield(noi: Decimal, prep_cost: Decimal) -> Decimal:
        if prep_cost == 0:
            return Decimal('0.00')
        return ((noi / prep_cost) * Decimal('100')).quantize(Decimal('0.01'))
