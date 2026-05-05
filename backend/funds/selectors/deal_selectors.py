from funds.models import InvestmentDeal, CurrentDeal, InvestmentRound

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
    if deal.is_pro_rata:
        if float(deal.entry_valuation) == 0:
            return 0.0
        return (float(deal.amount_invested) / float(deal.entry_valuation)) * 100.0

    denominator = float(deal.amount_invested) + float(deal.entry_valuation)
    if denominator == 0:
        return 0.0
    return (float(deal.amount_invested) / denominator) * 100.0

def calculate_current_deal_ownership_after_dilution(deal):
    """
    Calculates diluted ownership based on subsequent rounds.
    """
    initial_ownership = calculate_current_deal_post_money_ownership(deal)
    
    if deal.is_pro_rata:
        try:
            creation_round = deal.investment_round
            subsequent_rounds = InvestmentRound.objects.filter(
                fund=deal.fund, 
                company_name=deal.company_name,
                created_at__gt=creation_round.created_at
            ).order_by('year', 'created_at')
        except:
            subsequent_rounds = InvestmentRound.objects.filter(
                fund=deal.fund,
                company_name=deal.company_name,
                year__gt=deal.entry_year
            ).order_by('year', 'created_at')
    else:
        subsequent_rounds = InvestmentRound.objects.filter(
            fund=deal.fund, 
            company_name=deal.company_name
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
    ownership_decimal = calculate_current_deal_ownership_after_dilution(deal) / 100.0
    return ownership_decimal * float(deal.latest_valuation)

def calculate_investment_deal_post_money_ownership(deal):
    """
    Formula: amount_invested / (amount_invested + entry_valuation).
    """
    denominator = float(deal.amount_invested) + float(deal.entry_valuation)
    if denominator == 0:
        return 0.0
    return (float(deal.amount_invested) / denominator) * 100.0

def calculate_investment_deal_expected_ownership_after_dilution(deal):
    """
    Calculates expected ownership after dilution based on pro-rata rights.
    """
    original_ownership = calculate_investment_deal_post_money_ownership(deal)
    rounds = int(deal.expected_number_of_rounds)
    
    factor = 0.9 if deal.pro_rata_rights else 0.8
    return original_ownership * (factor ** rounds)

def calculate_investment_deal_expected_pro_rata_investments(deal):
    """
    Calculates expected pro rata investments (USD).
    """
    if not deal.pro_rata_rights:
        return 0.0
    
    original_ownership_decimal = calculate_investment_deal_post_money_ownership(deal) / 100.0
    
    holding_period = deal.exit_year - deal.entry_year
    if holding_period <= 0:
        holding_period = 1

    scenario_base_factor = float(getattr(deal, f"{deal.selected_scenario.lower()}_factor", 1.00))
    dilution_adjusted_factor = scenario_base_factor ** (1 / holding_period)
    
    entry_valuation = float(deal.entry_valuation)
    rounds = int(deal.expected_number_of_rounds)
    
    total = 0.0
    base_val = 0.1 * original_ownership_decimal * entry_valuation * dilution_adjusted_factor
    growth_factor = 0.9 * dilution_adjusted_factor
    
    for i in range(1, rounds + 1):
        total += base_val * (growth_factor ** (i - 1))
        
    return total

def calculate_investment_deal_exit_valuation(deal):
    """
    Calculated by multiplying the factor of the selected scenario by the post-money entry valuation.
    """
    factor = float(getattr(deal, f"{deal.selected_scenario.lower()}_factor", 1.00))
    post_money_valuation = float(deal.entry_valuation) + float(deal.amount_invested)
    return post_money_valuation * factor

def calculate_investment_deal_exit_value(deal):
    """
    Calculated by multiplying the expected ownership percentage after dilution by the exit valuation.
    """
    ownership_decimal = calculate_investment_deal_expected_ownership_after_dilution(deal) / 100.0
    exit_val = calculate_investment_deal_exit_valuation(deal)
    return float(ownership_decimal) * float(exit_val)
