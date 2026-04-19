from datetime import datetime
from .serializers import InvestmentDealSerializer, CurrentDealSerializer

def solve_implied_return_rate(injections_by_year, final_year, final_value):
    """
    Solves for the implied annual return rate (r) using a forward-compounding model.
    Formula: V_T = sum_{t=0 to T-1} I_t * (1 + r)^(T - t)
    Using binary search (bisection) for stability.

    Args:
        injections_by_year (dict): Mapping of year to injection amount.
        final_year (int): The target year for the valuation.
        final_value (float): The final valuation at the target year.

    Returns:
        float: The implied annual return rate.
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

def get_prognosis_injections(deals_data, deals_objs):
    """
    Calculates the scheduled injections for prognosis deals, including distributed pro-rata investments.

    Args:
        deals_data (list): Serialized data for investment deals.
        deals_objs (QuerySet): InvestmentDeal model instances.

    Returns:
        dict: Mapping of year to total injection amount for prognosis deals.
    """
    p_injections_by_year = {}
    deals_data_lookup = {d["id"]: d for d in deals_data}

    # Initial investments
    for d_data in deals_data:
        yr = d_data["entry_year"]
        p_injections_by_year[yr] = p_injections_by_year.get(yr, 0.0) + float(d_data.get("amount_invested", 0))
            
    # Distributed pro-rata across years
    for deal_obj in deals_objs:
        if deal_obj.pro_rata_rights and deal_obj.expected_number_of_rounds > 0:
            d_data = deals_data_lookup.get(str(deal_obj.id))
            if d_data:
                total_pro_rata_deal = float(d_data.get("expected_pro_rata_investments", 0))
                round_amt = total_pro_rata_deal / deal_obj.expected_number_of_rounds
                for i in range(1, deal_obj.expected_number_of_rounds + 1):
                    yr = deal_obj.entry_year + i
                    p_injections_by_year[yr] = p_injections_by_year.get(yr, 0.0) + round_amt
    
    return p_injections_by_year

def get_current_injections(c_deals_data):
    """
    Calculates the injections for current deals based on their entry years.

    Args:
        c_deals_data (list): Serialized data for current deals.

    Returns:
        dict: Mapping of year to total injection amount for current deals.
    """
    c_injections_by_year = {}
    for d in c_deals_data:
        yr = d["entry_year"]
        c_injections_by_year[yr] = c_injections_by_year.get(yr, 0.0) + float(d["amount_invested"])
    return c_injections_by_year

def calculate_nav_trajectory(start_year, end_year, current_year, fund_end_year, 
                            c_injections_by_year, p_injections_by_year, 
                            safe_c_irr, safe_p_irr):
    """
    Calculates the NAV trajectory (Current and Prognosis parts) year by year.

    Returns:
        list: A list of dicts containing NAV and appreciation for each year.
    """
    trajectory = []
    c_pv = 0.0
    p_pv = 0.0

    for yr in range(start_year, end_year + 1):
        c_inj = c_injections_by_year.get(yr, 0.0)
        p_inj = p_injections_by_year.get(yr, 0.0)
        
        # Apply IRR growth for yr >= current_year
        if yr >= current_year:
            growth_factor = 0.75 ** (yr - current_year + 1)
            effective_c_irr = safe_c_irr * growth_factor
            effective_p_irr = safe_p_irr * growth_factor
        else:
            effective_c_irr = safe_c_irr
            effective_p_irr = safe_p_irr

        c_appr = c_pv * effective_c_irr if yr <= fund_end_year else 0.0
        p_appr = p_pv * effective_p_irr if yr <= fund_end_year else 0.0
        
        c_pv += c_inj + c_appr
        p_pv += p_inj + p_appr

        trajectory.append({
            "year": yr,
            "c_pv": c_pv,
            "p_pv": p_pv,
            "c_appr": c_appr,
            "p_appr": p_appr,
            "c_inj": c_inj,
            "p_inj": p_inj
        })
        
    return trajectory

def get_total_fund_portfolio(fund, year):
    """
    Calculates the total fund portfolio value at the end of a given year.
    Matches the logic in FundPerformanceView.get_performance_table.

    Args:
        fund (Fund): The fund instance.
        year (int): The target year for the valuation.

    Returns:
        float: The combined portfolio value (Current + Prognosis).
    """
    model_inputs = getattr(fund, "model_inputs", None)
    if not model_inputs:
        return 0.0

    inception_year = int(model_inputs.inception_year)
    current_year = datetime.now().year
    fund_life = int(model_inputs.fund_life)
    fund_end_year = inception_year + fund_life

    # 1. Deal Prognosis Metrics
    deals = fund.deals.all()
    deal_serializer = InvestmentDealSerializer(deals, many=True)
    deals_data = deal_serializer.data
    p_injections_by_year = get_prognosis_injections(deals_data, deals)
    
    gross_exit_value_future = sum(float(d["exit_value"]) for d in deals_data if d["entry_year"] >= current_year)
    p_injections_future = {yr: amt for yr, amt in p_injections_by_year.items() if yr >= current_year}
    p_solver_injections = p_injections_future if p_injections_future else p_injections_by_year
    irr = solve_implied_return_rate(p_solver_injections, fund_end_year, gross_exit_value_future)

    # 2. Current Deals Metrics
    current_deals = fund.current_deals.all()
    c_deal_serializer = CurrentDealSerializer(current_deals, many=True)
    c_deals_data = c_deal_serializer.data
    c_injections_by_year = get_current_injections(c_deals_data)
    
    c_gross_exit_value = sum(float(d["final_exit_amount"]) for d in c_deals_data)
    historical_target_year = current_year - 1
    c_irr = solve_implied_return_rate(c_injections_by_year, historical_target_year, c_gross_exit_value)


    # 3. Calculate NAV parts
    safe_c_irr = c_irr if c_irr and c_irr > -1 else 0.0
    safe_p_irr = irr if irr and irr > -1 else 0.0

    all_entry_years = [d["entry_year"] for d in deals_data] + [d["entry_year"] for d in c_deals_data]
    start_year = min(inception_year, min(all_entry_years)) if all_entry_years else inception_year
    
    trajectory = calculate_nav_trajectory(
        start_year, year, current_year, fund_end_year,
        c_injections_by_year, p_injections_by_year,
        safe_c_irr, safe_p_irr
    )
    
    if not trajectory:
        return 0.0
        
    final_point = trajectory[-1]
    return final_point["c_pv"] + final_point["p_pv"]

def get_total_units_at_year(fund, year):
    """
    Calculates total units at the end of a given year.
    Sum of units from all PRIMARY_INVESTMENT actions up to and including that year.

    Args:
        fund (Fund): The fund instance.
        year (int): The target year.

    Returns:
        float: Total primary investment units.
    """
    from .models import InvestorAction
    actions = InvestorAction.objects.filter(
        fund=fund, 
        type="PRIMARY_INVESTMENT",
        year__lte=year
    )
    total_units = sum(action.units for action in actions)
    return float(total_units)
