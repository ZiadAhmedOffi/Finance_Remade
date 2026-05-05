from funds.models import InvestmentDeal, CurrentDeal, InvestmentRound

def _get_val(obj, attr, default=None):
    """Helper to get attribute from object or key from dict."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)

def get_deals_for_fund(fund):
    return InvestmentDeal.objects.filter(fund=fund).order_by("-created_at")

def get_deal_by_id(deal_id):
    try:
        return InvestmentDeal.objects.get(id=deal_id)
    except InvestmentDeal.DoesNotExist:
        return None

def get_current_deals_for_fund(fund):
    return CurrentDeal.objects.filter(fund=fund).order_by("-created_at")

def get_current_deal_by_id(deal_id):
    try:
        return CurrentDeal.objects.get(id=deal_id)
    except CurrentDeal.DoesNotExist:
        return None

def get_rounds_for_fund(fund):
    return InvestmentRound.objects.filter(fund=fund).order_by("-created_at")

def get_round_by_id(round_id):
    try:
        return InvestmentRound.objects.get(id=round_id)
    except InvestmentRound.DoesNotExist:
        return None

def get_prognosis_injections(fund):
    """
    Calculates the scheduled injections for prognosis deals for a fund.
    """
    deals = InvestmentDeal.objects.filter(fund=fund)
    p_injections_by_year = {}

    for deal in deals:
        # Initial investment
        yr = deal.entry_year
        p_injections_by_year[yr] = p_injections_by_year.get(yr, 0.0) + float(deal.amount_invested)
        
        # Distributed pro-rata across years
        if deal.pro_rata_rights and deal.expected_number_of_rounds > 0:
            total_pro_rata = float(calculate_investment_deal_expected_pro_rata_investments(deal))
            round_amt = total_pro_rata / deal.expected_number_of_rounds
            for i in range(1, deal.expected_number_of_rounds + 1):
                p_yr = deal.entry_year + i
                p_injections_by_year[p_yr] = p_injections_by_year.get(p_yr, 0.0) + round_amt
    
    return p_injections_by_year

def get_current_injections(fund):
    """
    Calculates the injections for current deals for a fund.
    """
    c_deals = CurrentDeal.objects.filter(fund=fund)
    c_injections_by_year = {}
    for d in c_deals:
        yr = d.entry_year
        c_injections_by_year[yr] = c_injections_by_year.get(yr, 0.0) + float(d.amount_invested)
    return c_injections_by_year

def calculate_current_deal_post_money_ownership(deal):
    """
    Formula: amount_invested / (amount_invested + entry_valuation).
    """
    is_pro_rata = _get_val(deal, "is_pro_rata", False)
    entry_valuation = _get_val(deal, "entry_valuation", 0)
    amount_invested = _get_val(deal, "amount_invested", 0)

    if is_pro_rata:
        if float(entry_valuation) == 0:
            return 0.0
        return (float(amount_invested) / float(entry_valuation)) * 100.0

    denominator = float(amount_invested) + float(entry_valuation)
    if denominator == 0:
        return 0.0
    return (float(amount_invested) / denominator) * 100.0

def calculate_current_deal_ownership_after_dilution(deal):
    """
    Calculates diluted ownership based on subsequent rounds.
    """
    initial_ownership = calculate_current_deal_post_money_ownership(deal)
    is_pro_rata = _get_val(deal, "is_pro_rata", False)
    fund = _get_val(deal, "fund")
    company_name = _get_val(deal, "company_name")
    entry_year = _get_val(deal, "entry_year")
    
    if is_pro_rata:
        try:
            creation_round = deal.investment_round
            subsequent_rounds = InvestmentRound.objects.filter(
                fund=fund, 
                company_name=company_name,
                created_at__gt=creation_round.created_at
            ).order_by('year', 'created_at')
        except:
            subsequent_rounds = InvestmentRound.objects.filter(
                fund=fund,
                company_name=company_name,
                year__gt=entry_year
            ).order_by('year', 'created_at')
    else:
        subsequent_rounds = InvestmentRound.objects.filter(
            fund=fund, 
            company_name=company_name
        ).order_by('year', 'created_at')

    current_ownership = float(initial_ownership)
    for round_obj in subsequent_rounds:
        pre_money = float(round_obj.pre_money_valuation)
        post_money = float(round_obj.target_valuation)
        if post_money > 0:
            dilution_factor = pre_money / post_money
            current_ownership *= dilution_factor
    
    return current_ownership

def calculate_current_deal_final_exit_amount(deal):
    """
    Calculates final exit amount: ownership_after_dilution % * latest_valuation.
    """
    latest_valuation = _get_val(deal, "latest_valuation", 0)
    ownership_decimal = calculate_current_deal_ownership_after_dilution(deal) / 100.0
    return ownership_decimal * float(latest_valuation)

def calculate_investment_deal_post_money_ownership(deal):
    """
    Formula: amount_invested / (amount_invested + entry_valuation).
    """
    amount_invested = _get_val(deal, "amount_invested", 0)
    entry_valuation = _get_val(deal, "entry_valuation", 0)
    denominator = float(amount_invested) + float(entry_valuation)
    if denominator == 0:
        return 0.0
    return (float(amount_invested) / denominator) * 100.0

def calculate_investment_deal_expected_ownership_after_dilution(deal):
    """
    Calculates expected ownership after dilution based on pro-rata rights.
    """
    original_ownership = calculate_investment_deal_post_money_ownership(deal)
    expected_number_of_rounds = _get_val(deal, "expected_number_of_rounds", 0)
    pro_rata_rights = _get_val(deal, "pro_rata_rights", False)

    rounds = int(expected_number_of_rounds)
    
    factor = 0.9 if pro_rata_rights else 0.8
    return original_ownership * (factor ** rounds)

def calculate_investment_deal_expected_pro_rata_investments(deal):
    """
    Calculates expected pro rata investments (USD).
    """
    pro_rata_rights = _get_val(deal, "pro_rata_rights", False)
    if not pro_rata_rights:
        return 0.0
    
    original_ownership_decimal = calculate_investment_deal_post_money_ownership(deal) / 100.0
    
    exit_year = _get_val(deal, "exit_year", 0)
    entry_year = _get_val(deal, "entry_year", 0)
    holding_period = exit_year - entry_year
    if holding_period <= 0:
        holding_period = 1

    selected_scenario = _get_val(deal, "selected_scenario", "BASE").lower()
    scenario_base_factor = float(_get_val(deal, f"{selected_scenario}_factor", 1.00))
    dilution_adjusted_factor = scenario_base_factor ** (1 / holding_period)
    
    entry_valuation = float(_get_val(deal, "entry_valuation", 0))
    expected_number_of_rounds = int(_get_val(deal, "expected_number_of_rounds", 0))
    
    total = 0.0
    base_val = 0.1 * original_ownership_decimal * entry_valuation * dilution_adjusted_factor
    growth_factor = 0.9 * dilution_adjusted_factor
    
    for i in range(1, expected_number_of_rounds + 1):
        total += base_val * (growth_factor ** (i - 1))
        
    return total

def calculate_investment_deal_exit_valuation(deal):
    """
    Calculated by multiplying the factor of the selected scenario by the post-money entry valuation.
    """
    selected_scenario = _get_val(deal, "selected_scenario", "BASE").lower()
    factor = float(_get_val(deal, f"{selected_scenario}_factor", 1.00))
    entry_valuation = _get_val(deal, "entry_valuation", 0)
    amount_invested = _get_val(deal, "amount_invested", 0)
    post_money_valuation = float(entry_valuation) + float(amount_invested)
    return post_money_valuation * factor

def calculate_investment_deal_exit_value(deal):
    """
    Calculated by multiplying the expected ownership percentage after dilution by the exit valuation.
    """
    ownership_decimal = calculate_investment_deal_expected_ownership_after_dilution(deal) / 100.0
    exit_val = calculate_investment_deal_exit_valuation(deal)
    return float(ownership_decimal) * float(exit_val)
