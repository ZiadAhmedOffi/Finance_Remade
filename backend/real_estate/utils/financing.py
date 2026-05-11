from decimal import Decimal, getcontext

# Set precision for financial calculations
getcontext().prec = 28

def calculate_pmt(rate_per_period: Decimal, periods: int, loan_amount: Decimal) -> Decimal:
    """
    Calculates the periodic payment for a loan.
    Formula: PMT = (r * PV) / (1 - (1 + r)^-n)
    """
    if rate_per_period == 0:
        return loan_amount / periods
    
    # PMT = (r * PV) / (1 - (1 + r)^-n)
    r = rate_per_period
    PV = loan_amount
    n = periods
    
    pmt = (r * PV) / (1 - (1 + r)**-n)
    return pmt.quantize(Decimal('0.01'))

def generate_amortization_schedule(
    loan_amount: Decimal,
    annual_rate: Decimal,
    tenor_years: int,
    payments_per_year: int,
    start_date
):
    """
    Generates an amortization schedule.
    Returns a list of dictionaries, each representing a payment period.
    """
    rate_per_period = annual_rate / payments_per_year
    total_periods = tenor_years * payments_per_year
    periodic_payment = calculate_pmt(rate_per_period, total_periods, loan_amount)
    
    schedule = []
    remaining_balance = loan_amount
    
    # We'll need date logic if we want to provide specific dates for each payment.
    # For now, let's just provide period numbers.
    # If start_date is provided, we can increment it based on payments_per_year.
    
    for period in range(1, total_periods + 1):
        interest_payment = (remaining_balance * rate_per_period).quantize(Decimal('0.01'))
        principal_payment = (periodic_payment - interest_payment).quantize(Decimal('0.01'))
        
        # Adjust for last payment to zero out balance
        if period == total_periods:
            principal_payment = remaining_balance
            periodic_payment = principal_payment + interest_payment
            remaining_balance = Decimal('0.00')
        else:
            remaining_balance -= principal_payment
            
        schedule.append({
            "period": period,
            "beginning_balance": (remaining_balance + principal_payment).quantize(Decimal('0.01')),
            "periodic_payment": periodic_payment,
            "principal_payment": principal_payment,
            "interest_payment": interest_payment,
            "ending_balance": remaining_balance.quantize(Decimal('0.01')),
        })
        
    return schedule
