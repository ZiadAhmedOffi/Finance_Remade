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


def calculate_nav_trajectory(start_year, end_year, current_year, fund_end_year, 
                            c_injections_by_year, p_injections_by_year, 
                            safe_c_irr, safe_p_irr, is_future=False, target_appreciation=0.0):
    """
    Calculates the NAV trajectory (Current and Prognosis parts) year by year.

    Returns:
        list: A list of dicts containing NAV and appreciation for each year.
    """
    trajectory = []
    c_pv = 0.0
    p_pv = 0.0
    target_appreciation_decimal = float(target_appreciation) / 100.0

    for yr in range(start_year, end_year + 1):
        c_inj = c_injections_by_year.get(yr, 0.0)
        p_inj = p_injections_by_year.get(yr, 0.0)
        
        # Apply growth for yr >= current_year
        if is_future:
            # Future funds use target_appreciation as constant annual growth
            effective_c_irr = target_appreciation_decimal
            effective_p_irr = target_appreciation_decimal
        elif yr >= current_year:
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
            "p_inj": p_inj,
            "irr": effective_c_irr if not is_future else target_appreciation_decimal
        })
        
    return trajectory
