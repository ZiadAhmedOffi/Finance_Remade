from django.db.models import Sum
from funds.models import InvestorAction, CurrentInvestorStats
from funds.selectors import fund_selectors
from datetime import datetime

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

def calculate_dashboard_metrics(investor):
    fund_data = get_grouped_investor_data(investor)
    total_current_portfolio_value = 0.0
    portfolio_table = []
    pie_chart_data = []
    current_year = datetime.now().year

    for fund_id, data in fund_data.items():
        fund = data["fund"]
        total_fund_units = float(fund.total_units)
        ownership_pct = (data["units"] / total_fund_units * 100.0) if total_fund_units > 0 else 0.0
        current_fund_val = fund_selectors.get_total_fund_portfolio(fund, current_year)
        current_val_in_fund = (ownership_pct / 100.0) * current_fund_val
        total_current_portfolio_value += current_val_in_fund

        portfolio_table.append({
            "fund_name": fund.name,
            "ownership_pct": ownership_pct,
            "current_value": current_val_in_fund,
            "net_deployed": data["net_deployed"]
        })
        pie_chart_data.append({
            "name": fund.name,
            "value": current_val_in_fund
        })

    stats = get_investor_stats_for_investor(investor)
    realized_gains = sum(float(s.realized_gain or 0) for s in stats)
    total_capital_deployed = sum(float(s.amount_invested or 0) for s in stats)
    total_capital_injected = sum(float(s.capital_deployed or 0) for s in stats)

    unrealized_gains = total_current_portfolio_value - total_capital_deployed
    unrealized_multiple = (total_current_portfolio_value / total_capital_deployed) if total_capital_deployed > 0 else 0.0

    # Realized multiple calculation
    investor_investments = InvestorAction.objects.filter(investor=investor, type__in=["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"])
    investor_exits = InvestorAction.objects.filter(investor=investor, type="SECONDARY_EXIT")
    total_exits_amount = sum(float(action.amount or 0) for action in investor_exits)
    total_invested_amount = sum(float(action.amount or 0) for action in investor_investments)
    realized_multiple = 0.0
    if total_capital_deployed > 0 and total_capital_deployed != total_invested_amount:
        realized_multiple = total_exits_amount / (total_invested_amount - total_capital_deployed)

    # Line Graph logic
    all_actions = get_investor_actions_by_investor(investor)
    years = sorted(list(set(a.year for a in all_actions)))
    line_graph_data = []
    if years:
        start_year = min(years)
        end_year = max(current_year, max(years))
        for yr in range(start_year, end_year + 1):
            yr_total_value = 0.0
            yr_total_injection = 0.0
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
            "current_portfolio_value": total_current_portfolio_value
        },
        "portfolio_table": portfolio_table,
        "pie_chart_data": pie_chart_data,
        "line_graph_data": line_graph_data
    }
