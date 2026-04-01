from datetime import datetime
from .serializers import InvestmentDealSerializer, CurrentDealSerializer

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
    moic = gross_exit_value / total_invested_float if total_invested_float > 0 else 0
    
    # Simple weighted time for IRR estimation
    def calculate_wait_time(inc_yr, curr_yr, total_inv, inj_by_yr):
        if total_inv <= 0: return 0.0
        wait_base = float(curr_yr - 1 - inc_yr)
        numerator = sum(float(inj_by_yr.get(yr, 0.0)) * wait_base for yr in range(inc_yr, curr_yr))
        return numerator / float(total_inv)

    p_wait = calculate_wait_time(inception_year, datetime.now().year, total_invested_float, p_injections_by_year)
    irr = (float(moic) ** (1.0 / float(p_wait))) - 1.0 if moic > 0 and p_wait > 0 else 0.0

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
            
    c_moic = c_gross_exit_value / c_total_invested_float if c_total_invested_float > 0 else 0
    c_wait = calculate_wait_time(inception_year, datetime.now().year, c_total_invested_float, c_injections_by_year)
    c_irr = (float(c_moic) ** (1.0 / float(c_wait))) - 1.0 if c_moic > 0 and c_wait > 0 else 0.0

    # 3. Step through years to find value at 'year'
    current_portfolio_value = 0.0
    prognosis_portfolio_value = 0.0
    
    safe_c_irr = c_irr if c_irr and c_irr > -1 else 0.0
    safe_p_irr = irr if irr and irr > -1 else 0.0
    
    # We need to iterate from inception up to 'year'
    # To be safe, find the minimum entry year
    all_entry_years = [d["entry_year"] for d in deals_data] + [d["entry_year"] for d in c_deals_data]
    start_year = min(inception_year, min(all_entry_years)) if all_entry_years else inception_year
    
    current_deals_by_yr = {}
    for d in c_deals_data: current_deals_by_yr.setdefault(d["entry_year"], []).append(d)
    
    prognosis_deals_by_yr = {}
    for d in deals_data: prognosis_deals_by_yr.setdefault(d["entry_year"], []).append(d)

    for y in range(start_year, year + 1):
        c_injection = sum(float(d["amount_invested"]) for d in current_deals_by_yr.get(y, []))
        p_injection = sum(float(d["amount_invested"]) for d in prognosis_deals_by_yr.get(y, []))
        
        # Add pro-rata prognosis injections
        for deal_obj in deals:
            if deal_obj.pro_rata_rights and deal_obj.expected_number_of_rounds > 0:
                d_data = next((d for d in deals_data if d["id"] == str(deal_obj.id)), None)
                if d_data:
                    total_pro_rata = float(d_data.get("expected_pro_rata_investments", 0))
                    round_amt = total_pro_rata / deal_obj.expected_number_of_rounds
                    if deal_obj.entry_year < y <= deal_obj.entry_year + deal_obj.expected_number_of_rounds:
                        p_injection += round_amt
        
        c_appreciation = current_portfolio_value * safe_c_irr
        p_appreciation = prognosis_portfolio_value * safe_p_irr
        
        current_portfolio_value += c_injection + c_appreciation
        prognosis_portfolio_value += p_injection + p_appreciation
        
    return current_portfolio_value + prognosis_portfolio_value

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
