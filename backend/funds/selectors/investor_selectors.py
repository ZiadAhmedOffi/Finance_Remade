from django.db.models import Sum
from funds.models import InvestorAction, CurrentInvestorStats, Distribution
from funds.selectors import fund_selectors
from datetime import datetime, date
from real_estate.models import RealEstateInvestorAction, RealEstateInvestorStats, RealEstatePortfolio
from real_estate.selectors.portfolio_selectors import PortfolioSelectors
from real_estate.selectors.portfolio_dashboard_selectors import PortfolioDashboardSelector
from real_estate.selectors.cash_flow_selectors import CashFlowSelectors

def get_investor_actions_by_investor(investor):
    return InvestorAction.objects.filter(investor=investor).select_related('fund').order_by('year', 'created_at')

def get_investor_actions_by_fund(fund):
    return InvestorAction.objects.filter(fund=fund).select_related('investor').order_by('year', 'created_at')

def get_investor_action_by_id(action_id):
    try:
        return InvestorAction.objects.get(id=action_id)
    except InvestorAction.DoesNotExist:
        return None

def get_investor_stats_for_investor(investor):
    return CurrentInvestorStats.objects.filter(investor=investor).select_related('fund')

def get_investor_stats_for_fund(fund):
    return CurrentInvestorStats.objects.filter(fund=fund).select_related('investor')

def calculate_investor_units(investor, fund, year=None):
    actions = InvestorAction.objects.filter(investor=investor, fund=fund)
    if year:
        actions = actions.filter(year__lte=year)
    
    units = 0.0
    for a in actions:
        if a.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
            units += float(a.units)
        elif a.type == "SECONDARY_EXIT":
            units -= float(a.units)
    return units

def calculate_re_investor_units(investor, portfolio, year=None):
    actions = RealEstateInvestorAction.objects.filter(investor=investor, portfolio=portfolio)
    if year:
        actions = actions.filter(year__lte=year)
    
    units = 0.0
    for a in actions:
        if a.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
            units += float(a.units)
        elif a.type == "SECONDARY_EXIT":
            units -= float(a.units)
    return units

def get_grouped_investor_data(investor):
    actions = get_investor_actions_by_investor(investor)
    fund_data = {}
    for action in actions:
        fund_id = str(action.fund.id)
        if fund_id not in fund_data:
            fund_data[fund_id] = {
                "fund": action.fund,
                "investments": [],
                "exits": [],
                "units": 0.0,
                "net_deployed": 0.0
            }
        if action.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
            fund_data[fund_id]["investments"].append(action)
            fund_data[fund_id]["units"] += float(action.units)
            fund_data[fund_id]["net_deployed"] += float(action.amount or 0)
        elif action.type == "SECONDARY_EXIT":
            fund_data[fund_id]["exits"].append(action)
            fund_data[fund_id]["units"] -= float(action.units)
            fund_data[fund_id]["net_deployed"] -= float(action.amount or 0)
    return fund_data

def get_grouped_re_investor_data(investor):
    actions = RealEstateInvestorAction.objects.filter(investor=investor).select_related('portfolio').order_by('year', 'created_at')
    re_data = {}
    for action in actions:
        portfolio_id = str(action.portfolio.id)
        if portfolio_id not in re_data:
            re_data[portfolio_id] = {
                "portfolio": action.portfolio,
                "investments": [],
                "exits": [],
                "units": 0.0,
                "net_deployed": 0.0
            }
        if action.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
            re_data[portfolio_id]["investments"].append(action)
            re_data[portfolio_id]["units"] += float(action.units)
            re_data[portfolio_id]["net_deployed"] += float(action.amount or 0)
        elif action.type == "SECONDARY_EXIT":
            re_data[portfolio_id]["exits"].append(action)
            re_data[portfolio_id]["units"] -= float(action.units)
            re_data[portfolio_id]["net_deployed"] -= float(action.amount or 0)
    return re_data

def calculate_investor_yield_history(investor, fund_data, re_data):
    """
    Calculates historical yield (dividends/cash flow) received by the investor across funds and RE.
    """
    current_year = datetime.now().year
    
    # Collect all relevant years
    years = {current_year}
    fund_actions = InvestorAction.objects.filter(investor=investor)
    years.update([a.year for a in fund_actions])
    
    re_actions = RealEstateInvestorAction.objects.filter(investor=investor)
    years.update([a.year for a in re_actions])
    
    dist_years = Distribution.objects.filter(type="DIVIDEND").values_list('date__year', flat=True).distinct()
    years.update(dist_years)
    
    sorted_years = sorted(list(years))
    if not sorted_years:
        return []
        
    start_year = sorted_years[0]
    end_year = current_year
    
    yield_history = []
    for yr in range(start_year, end_year + 1):
        year_entry = {"year": yr, "total": 0.0}
        total_yr_yield = 0.0
        
        # 1. Equity Funds Yield (Dividends)
        for fund_id, data in fund_data.items():
            fund = data["fund"]
            investor_units = calculate_investor_units(investor, fund, yr)
            total_fund_units = fund_selectors.get_total_units_at_year(fund, yr)
            ownership_pct = (investor_units / total_fund_units) if total_fund_units > 0 else 0.0
            
            fund_divs = Distribution.objects.filter(
                fund=fund, 
                type="DIVIDEND", 
                date__year=yr
            ).aggregate(total=Sum('amount'))['total'] or 0.0
            
            investor_share = float(fund_divs) * ownership_pct
            year_entry[fund.name] = investor_share
            total_yr_yield += investor_share
            
        # 2. Real Estate Yield (Positive Cash Flow)
        for portfolio_id, data in re_data.items():
            portfolio = data["portfolio"]
            investor_units = calculate_re_investor_units(investor, portfolio, yr)
            total_portfolio_units = PortfolioSelectors.get_total_units_at_year(portfolio, yr)
            ownership_pct = (investor_units / total_portfolio_units) if total_portfolio_units > 0 else 0.0
            
            cf_data = CashFlowSelectors.get_portfolio_cash_flow(portfolio, start_year=yr, end_year=yr)
            portfolio_cf = float(cf_data["portfolio_totals"].get(yr, 0.0))
            portfolio_sales = float(cf_data["portfolio_sales_proceeds"].get(yr, 0.0))
            
            # Yield = Ownership * (Cash Flow - Sales Proceeds) if CF > 0, else 0
            if portfolio_cf > 0:
                investor_share = ownership_pct * (portfolio_cf - portfolio_sales)
            else:
                investor_share = 0.0
            
            year_entry[portfolio.name] = investor_share
            total_yr_yield += investor_share
            
        year_entry["total"] = total_yr_yield
        yield_history.append(year_entry)
        
    return yield_history

def calculate_dashboard_metrics(investor):
    current_year = datetime.now().year
    
    # 1. Fund Data
    fund_data = get_grouped_investor_data(investor)
    total_current_portfolio_value = 0.0
    portfolio_table = []
    pie_chart_data = []
    total_annual_yield_amount = 0.0

    for fund_id, data in fund_data.items():
        fund = data["fund"]
        total_fund_units = float(fund.total_units)
        ownership_pct = (data["units"] / total_fund_units * 100.0) if total_fund_units > 0 else 0.0
        current_fund_val = fund_selectors.get_total_fund_portfolio(fund, current_year)
        current_val_in_fund = (ownership_pct / 100.0) * current_fund_val
        total_current_portfolio_value += current_val_in_fund

        # Calculate Yield for Fund
        fund_yield_pct = float(fund.target_yield)
        total_annual_yield_amount += (fund_yield_pct / 100.0) * current_val_in_fund

        portfolio_table.append({
            "fund_name": fund.name,
            "ownership_pct": ownership_pct,
            "current_value": current_val_in_fund,
            "net_deployed": data["net_deployed"],
            "yield_pct": fund_yield_pct,
            "type": "FUND"
        })
        pie_chart_data.append({
            "name": fund.name,
            "value": current_val_in_fund
        })

    # 2. Real Estate Data
    re_data = get_grouped_re_investor_data(investor)
    for portfolio_id, data in re_data.items():
        portfolio = data["portfolio"]
        nav_metrics = PortfolioSelectors.get_portfolio_nav_metrics(portfolio)
        total_portfolio_units = float(portfolio.total_units)
        ownership_pct = (data["units"] / total_portfolio_units * 100.0) if total_portfolio_units > 0 else 0.0
        current_nav = float(nav_metrics["nav"])
        current_val_in_portfolio = (ownership_pct / 100.0) * current_nav
        total_current_portfolio_value += current_val_in_portfolio

        # Calculate Yield for RE
        cf_data = CashFlowSelectors.get_portfolio_cash_flow(portfolio, start_year=current_year, end_year=current_year)
        portfolio_cf = float(cf_data["portfolio_totals"].get(current_year, 0.0))
        portfolio_sales = float(cf_data["portfolio_sales_proceeds"].get(current_year, 0.0))
        
        # New Yield Base: (CF - Sales)
        yield_base = (portfolio_cf - portfolio_sales) if portfolio_cf > 0 else 0.0
        re_yield_pct = (yield_base / float(nav_metrics["nav"]) * 100.0) if float(nav_metrics["nav"]) > 0 else 0.0
        
        total_annual_yield_amount += (ownership_pct / 100.0) * yield_base

        portfolio_table.append({
            "fund_name": portfolio.name,
            "ownership_pct": ownership_pct,
            "current_value": current_val_in_portfolio,
            "net_deployed": data["net_deployed"],
            "yield_pct": re_yield_pct,
            "type": "REAL_ESTATE"
        })
        pie_chart_data.append({
            "name": portfolio.name,
            "value": current_val_in_portfolio
        })

    # 3. Aggregated Stats
    stats = get_investor_stats_for_investor(investor)
    re_stats = RealEstateInvestorStats.objects.filter(investor=investor)
    
    realized_gains = sum(float(s.realized_gain or 0) for s in stats) + sum(float(s.realized_gain or 0) for s in re_stats)
    total_capital_deployed = sum(float(s.amount_invested or 0) for s in stats) + sum(float(s.amount_invested or 0) for s in re_stats)
    total_capital_injected = sum(float(s.capital_deployed or 0) for s in stats) + sum(float(s.capital_deployed or 0) for s in re_stats)

    unrealized_gains = total_current_portfolio_value - total_capital_deployed
    unrealized_multiple = (total_current_portfolio_value / total_capital_deployed) if total_capital_deployed > 0 else 0.0

    # Weighted Aggregate Yield
    total_yield_pct = (total_annual_yield_amount / total_current_portfolio_value * 100.0) if total_current_portfolio_value > 0 else 0.0
    
    # 4. Yield History (Updated to include RE)
    yield_history = calculate_investor_yield_history(investor, fund_data, re_data)

    # Multiples calculation (Updated to include RE)
    fund_investments = InvestorAction.objects.filter(investor=investor, type__in=["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"])
    fund_exits = InvestorAction.objects.filter(investor=investor, type="SECONDARY_EXIT")
    re_investments = RealEstateInvestorAction.objects.filter(investor=investor, type__in=["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"])
    re_exits = RealEstateInvestorAction.objects.filter(investor=investor, type="SECONDARY_EXIT")
    
    total_exits_amount = sum(float(a.amount or 0) for a in fund_exits) + sum(float(a.amount or 0) for a in re_exits)
    total_invested_amount = sum(float(a.amount or 0) for a in fund_investments) + sum(float(a.amount or 0) for a in re_investments)
    
    realized_multiple = 0.0
    if total_capital_deployed > 0 and total_capital_deployed != total_invested_amount:
        realized_multiple = total_exits_amount / (total_invested_amount - total_capital_deployed)

    # 5. Line Graph logic
    fund_actions = get_investor_actions_by_investor(investor)
    re_actions = RealEstateInvestorAction.objects.filter(investor=investor)
    
    years = sorted(list(set([a.year for a in fund_actions] + [a.year for a in re_actions])))
    line_graph_data = []
    if years:
        start_year = min(years)
        end_year = max(current_year, max(years))
        for yr in range(start_year, end_year + 1):
            yr_total_value = 0.0
            yr_total_injection = 0.0
            
            # Funds
            for fid, f_data in fund_data.items():
                fund = f_data["fund"]
                f_units_at_yr = calculate_investor_units(investor, fund, yr)
                total_fund_units_at_yr = fund_selectors.get_total_units_at_year(fund, yr)
                f_ownership_pct_at_yr = (f_units_at_yr / total_fund_units_at_yr * 100.0) if total_fund_units_at_yr > 0 else 0.0
                fund_val_at_yr = fund_selectors.get_total_fund_portfolio(fund, yr)
                yr_total_value += (f_ownership_pct_at_yr / 100.0) * fund_val_at_yr
                
                actions_this_yr = InvestorAction.objects.filter(investor=investor, fund=fund, year=yr)
                for a in actions_this_yr:
                    if a.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
                        yr_total_injection += float(a.amount or 0)
                    elif a.type == "SECONDARY_EXIT":
                        yr_total_injection -= float(a.amount or 0)
            
            # Real Estate
            for rid, r_data in re_data.items():
                portfolio = r_data["portfolio"]
                r_units_at_yr = calculate_re_investor_units(investor, portfolio, yr)
                # Use date(yr, 12, 31) for point-in-time calculation
                ref_date = date(yr, 12, 31)
                nav_metrics_at_yr = PortfolioSelectors.get_portfolio_nav_metrics(portfolio, reference_date=ref_date)
                total_re_units_at_yr = float(nav_metrics_at_yr["total_units"])
                r_ownership_pct_at_yr = (r_units_at_yr / total_re_units_at_yr * 100.0) if total_re_units_at_yr > 0 else 0.0
                re_nav_at_yr = float(nav_metrics_at_yr["nav"])
                yr_total_value += (r_ownership_pct_at_yr / 100.0) * re_nav_at_yr
                
                re_actions_this_yr = RealEstateInvestorAction.objects.filter(investor=investor, portfolio=portfolio, year=yr)
                for a in re_actions_this_yr:
                    if a.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
                        yr_total_injection += float(a.amount or 0)
                    elif a.type == "SECONDARY_EXIT":
                        yr_total_injection -= float(a.amount or 0)
            
            prev_val = line_graph_data[-1]["value"] if line_graph_data else 0
            yoy_gain = ((yr_total_value / prev_val) - 1) * 100 if prev_val > 0 else 0.0
            line_graph_data.append({
                "year": yr,
                "value": yr_total_value,
                "injection": yr_total_injection,
                "yoy_gain": yoy_gain if line_graph_data else None
            })

    return {
        "metrics": {
            "total_capital_deployed": total_capital_injected,
            "realized_gains": realized_gains,
            "unrealized_gains": unrealized_gains,
            "realized_multiple": realized_multiple,
            "unrealized_multiple": unrealized_multiple,
            "current_portfolio_value": total_current_portfolio_value,
            "total_yield": total_yield_pct
        },
        "portfolio_table": portfolio_table,
        "pie_chart_data": pie_chart_data,
        "line_graph_data": line_graph_data,
        "yield_history": yield_history
    }
