import math
from datetime import datetime

def get_venture_ls(company_type: str) -> float:
    """
    Maps company stage strings to Liquidity Scores (LS).
    Lower % -> more liquid (better)
    """
    if not company_type:
        return 0.50
        
    t = company_type.upper().strip()
    if "PMF -" in t or t == "PMF-":
        return 0.90
    if "PMF +" in t or t == "PMF+":
        return 0.75
    if "BMF -" in t or t == "BMF-":
        return 0.60
    if "BMF +" in t or t == "BMF+":
        return 0.45
    if "SCALING -" in t or t == "SCALING-":
        return 0.30
    if "SCALING +" in t or t == "SCALING+":
        return 0.15
    return 0.50  # Default fallback

def calculateLiquidityIndex(current_deals, inception_year, fund_life=10):
    """
    Computes the complete Liquidity Index for a portfolio.
    Formula: LI = (1 - portfolio_l) * (1 + time_factor) * 100
    
    portfolio_l uses the old logic (weighted average of risk-based LS).
    time_factor is a distributed percentage over the fund's lifetime.
    """
    if not current_deals:
        return {"finalLI": 0, "portfolioL": 0, "ageFactor": 0, "age": 0}

    total_valuation = 0
    total_weighted_ls = 0

    for d in current_deals:
        if hasattr(d, 'latest_valuation'):
            val = float(d.latest_valuation) if d.latest_valuation else 0
        else:
            val = float(d.get('latest_valuation', 0))
            
        if hasattr(d, 'company_type'):
            company_type = d.company_type
        else:
            company_type = d.get('company_type', '')
            
        ls = get_venture_ls(company_type)
        total_weighted_ls += ls * val
        total_valuation += val

    portfolio_l = total_weighted_ls / total_valuation if total_valuation > 0 else 0.5

    current_year = datetime.now().year
    age = max(0, current_year - inception_year)
    
    unit = fund_life / 5
    if age <= 3 * unit:
        # First 3/5 gets 50%
        time_factor = (age / (3 * unit)) * 0.5
    else:
        # Final 2/5 gets 50% (Total 100%)
        remaining_age = min(age - 3 * unit, 2 * unit)
        time_factor = 0.5 + (remaining_age / (2 * unit)) * 0.5
        
    time_factor = min(1.0, time_factor)

    # Use (1 - portfolio_l) as the weighted base
    final_li = (1 - portfolio_l) * (1 + time_factor) * 100

    return {
        "finalLI": min(100.0, max(0.0, final_li)),
        "portfolioL": portfolio_l,
        "ageFactor": time_factor,
        "age": age
    }
