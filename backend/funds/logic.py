from datetime import datetime
from .serializers import InvestmentDealSerializer, CurrentDealSerializer

def solve_implied_return_rate(injections_by_year, final_year, final_value):
    """
    Solves for the implied annual return rate (r) using a forward-compounding model.
    Formula: V_T = sum_{t=0 to T-1} I_t * (1 + r)^(T - t)
    Using binary search (bisection) for stability.
    """
    if not injections_by_year:
        return 0.0
    if final_value <= 0:
        return -1.0
        
    def f(r):
        total = 0.0
        factor = 1.0 + r
        for yr, amt in injections_by_year.items():
            if yr <= final_year:
                total += float(amt) * (factor ** (final_year - yr))
        return total - float(final_value)

    low = -0.99
    high = 10.0
    tolerance = 1e-7
    
    if f(low) > 0: return low
    if f(high) < 0: return high
    
    for _ in range(100):
        mid = (low + high) / 2.0
        val = f(mid)
        if abs(val) < tolerance:
            return mid
        if val > 0:
            high = mid
        else:
            low = mid
    return (low + high) / 2.0

def compute_nav_by_year(injections_by_year, r, final_year, start_year, end_year):
    """
    Calculates Net Asset Value (NAV) per year using forward-compounding.
    Formula: NAV_t = sum_{i=0 to t} I_i * (1 + r)^(min(t, final_year) - i)
    """
    nav_by_year = {}
    factor = 1.0 + r
    for t in range(start_year, end_year + 1):
        total = 0.0
        effective_year = min(t, final_year)
        for yr, amt in injections_by_year.items():
            if yr <= t:
                exponent = max(0, effective_year - yr)
                total += float(amt) * (factor ** exponent)
        nav_by_year[t] = total
    return nav_by_year

def get_total_fund_portfolio(fund, year):
    """
    Calculates the total fund portfolio value at the end of a given year.
    Matches the logic in FundPerformanceView.get_performance_table.
    """
    deals = fund.deals.all()
    current_deals = fund.current_deals.all()
    model_inputs = getattr(fund, "model_inputs", None)
    
    if not model_inputs:
        return 0.0

    management_fee_pct = float(model_inputs.management_fee)
    inception_year = int(model_inputs.inception_year)
    current_year = datetime.now().year
    fund_life = int(model_inputs.fund_life)
    fund_end_year = inception_year + fund_life

    # 1. Deal Prognosis Metrics
    total_invested = sum(deal.amount_invested for deal in deals)
    deal_serializer = InvestmentDealSerializer(deals, many=True)
    deals_data = deal_serializer.data
    
    total_expected_pro_rata = 0.0
    p_injections_by_year = {}
    for d_data in deals_data:
        yr = d_data["entry_year"]
        p_injections_by_year[yr] = p_injections_by_year.get(yr, 0.0) + float(d_data.get("amount_invested", 0))
        total_expected_pro_rata += float(d_data.get("expected_pro_rata_investments", 0))
            
    # Distribute pro-rata across years
    for deal_obj in deals:
        if deal_obj.pro_rata_rights and deal_obj.expected_number_of_rounds > 0:
            d_data = next((d for d in deals_data if d["id"] == str(deal_obj.id)), None)
            if d_data:
                total_pro_rata_deal = float(d_data.get("expected_pro_rata_investments", 0))
                round_amt = total_pro_rata_deal / deal_obj.expected_number_of_rounds
                for i in range(1, deal_obj.expected_number_of_rounds + 1):
                    yr = deal_obj.entry_year + i
                    p_injections_by_year[yr] = p_injections_by_year.get(yr, 0.0) + round_amt
    
    total_invested_float = float(total_invested) + total_expected_pro_rata
    gross_exit_value = sum(float(d["exit_value"]) for d in deals_data)
    # Target for future deals: only sum exit values of deals starting from current_year
    gross_exit_value_future = sum(float(d["exit_value"]) for d in deals_data if d["entry_year"] >= current_year)
    
    # Expected IRR (irr) targeting fund_end_year using future injections
    p_injections_future = {yr: amt for yr, amt in p_injections_by_year.items() if yr >= current_year}
    p_solver_injections = p_injections_future if p_injections_future else p_injections_by_year
    irr = solve_implied_return_rate(p_solver_injections, fund_end_year, gross_exit_value_future)

    # 2. Current Deals Metrics
    c_total_invested = sum(d.amount_invested for d in current_deals)
    c_deal_serializer = CurrentDealSerializer(current_deals, many=True)
    c_deals_data = c_deal_serializer.data
    c_gross_exit_value = sum(float(d["final_exit_amount"]) for d in c_deals_data)
    c_total_invested_float = float(c_total_invested)
    
    c_injections_by_year = {}
    for d in c_deals_data:
        yr = d["entry_year"]
        c_injections_by_year[yr] = c_injections_by_year.get(yr, 0.0) + float(d["amount_invested"])
            
    # Current IRR (c_irr) targeting current_year - 1
    historical_target_year = current_year - 1
    c_irr = solve_implied_return_rate(c_injections_by_year, historical_target_year, c_gross_exit_value)

    # 3. Calculate NAV parts
    safe_c_irr = c_irr if c_irr and c_irr > -1 else 0.0
    safe_p_irr = irr if irr and irr > -1 else 0.0

    # Iterative calculation to match FundPerformanceView
    # Find start_year
    all_entry_years = [d["entry_year"] for d in deals_data] + [d["entry_year"] for d in c_deals_data]
    start_year = min(inception_year, min(all_entry_years)) if all_entry_years else inception_year
    
    c_pv = 0.0
    p_pv = 0.0
    for yr in range(start_year, year + 1):
        c_inj = c_injections_by_year.get(yr, 0.0)
        p_inj = p_injections_by_year.get(yr, 0.0)
        
        c_appr = c_pv * safe_c_irr if yr <= fund_end_year else 0.0
        p_appr = p_pv * safe_p_irr if yr <= fund_end_year else 0.0
        
        c_pv += c_inj + c_appr
        p_pv += p_inj + p_appr
        
    return c_pv + p_pv

def get_total_units_at_year(fund, year):
    """
    Calculates total units at the end of a given year.
    Sum of units from all PRIMARY_INVESTMENT actions up to and including that year.
    """
    from .models import InvestorAction
    actions = InvestorAction.objects.filter(
        fund=fund, 
        type="PRIMARY_INVESTMENT",
        year__lte=year
    )
    total_units = sum(action.units for action in actions)
    return float(total_units)
