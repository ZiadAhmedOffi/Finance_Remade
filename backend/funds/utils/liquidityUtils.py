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

def calculateLiquidityIndex(current_deals, inception_year, decay_constant=0.20):
    """
    Computes the complete Liquidity Index for a portfolio.
    Formula: LI = (Σ(LS_i * V_i) / Σ(V_i)) * exp(-k * t) * 100
    """
    if not current_deals:
        return {"finalLI": 0, "portfolioL": 0, "ageFactor": 1, "age": 0}

    total_weighted_ls = 0
    total_valuation = 0

    for d in current_deals:
        # Django models or dicts
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
    age_factor = math.exp(-decay_constant * age)

    final_li = portfolio_l * age_factor * 100

    return {
        "finalLI": min(100.0, max(0.0, final_li)),
        "portfolioL": portfolio_l,
        "ageFactor": age_factor,
        "age": age
    }
