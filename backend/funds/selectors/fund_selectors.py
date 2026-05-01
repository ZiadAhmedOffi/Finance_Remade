from funds.models import Fund, FundLog, ModelInput
from users.services.permission_service import PermissionService
from funds.utils import calculators
from funds.selectors import deal_selectors
from datetime import datetime
from django.db.models import Sum

def get_all_funds():
    return Fund.objects.all().order_by("-created_at")

def get_funds_for_user(user):
    """
    Returns funds accessible to the user based on their roles and status.
    """
    if PermissionService.is_super_admin(user):
        return Fund.objects.all().order_by("-created_at")
    
    # For non-superadmins, show active funds where they have ANY role
    from users.models import UserRoleAssignment
    fund_ids = UserRoleAssignment.objects.filter(user=user).values_list("fund_id", flat=True)
    return Fund.objects.filter(id__in=fund_ids).exclude(status="DEACTIVATED").order_by("-created_at")

def get_fund_by_id(fund_id):
    try:
        return Fund.objects.get(id=fund_id)
    except Fund.DoesNotExist:
        return None

def get_fund_logs(fund):
    return FundLog.objects.filter(target_fund=fund).select_related("actor").order_by("-timestamp")

def get_fund_model_input(fund):
    try:
        return ModelInput.objects.get(fund=fund)
    except ModelInput.DoesNotExist:
        return None

def get_total_fund_portfolio(fund, year):
    """
    Calculates the total fund portfolio value at the end of a given year.
    """
    model_inputs = get_fund_model_input(fund)
    if not model_inputs:
        return 0.0

    inception_year = int(model_inputs.inception_year)
    current_year = datetime.now().year
    fund_life = int(model_inputs.fund_life)
    fund_end_year = inception_year + fund_life

    # 1. Deal Prognosis Metrics
    deals = deal_selectors.get_deals_for_fund(fund)
    p_injections_by_year = deal_selectors.get_prognosis_injections(fund)
    
    gross_exit_value_future = sum(float(d.exit_value) for d in deals if d.entry_year >= current_year)
    p_injections_future = {yr: amt for yr, amt in p_injections_by_year.items() if yr >= current_year}
    p_solver_injections = p_injections_future if p_injections_future else p_injections_by_year
    irr = calculators.solve_implied_return_rate(p_solver_injections, fund_end_year, gross_exit_value_future)

    # 2. Current Deals Metrics
    current_deals = deal_selectors.get_current_deals_for_fund(fund)
    c_injections_by_year = deal_selectors.get_current_injections(fund)
    
    c_gross_exit_value = sum(deal_selectors.calculate_current_deal_final_exit_amount(d) for d in current_deals)
    historical_target_year = current_year - 1
    c_irr = calculators.solve_implied_return_rate(c_injections_by_year, historical_target_year, c_gross_exit_value)

    # 3. Calculate NAV parts
    safe_c_irr = c_irr if c_irr and c_irr > -1 else 0.0
    safe_p_irr = irr if irr and irr > -1 else 0.0

    all_entry_years = [d.entry_year for d in deals] + [d.entry_year for d in current_deals]
    start_year = min(inception_year, min(all_entry_years)) if all_entry_years else inception_year
    
    trajectory = calculators.calculate_nav_trajectory(
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
    """
    from funds.models import InvestorAction
    return float(InvestorAction.objects.filter(
        fund=fund, 
        type="PRIMARY_INVESTMENT",
        year__lte=year
    ).aggregate(total_units=Sum('units'))['total_units'] or 0.0)

def get_fund_logs(fund):
    return FundLog.objects.filter(target_fund=fund).select_related("actor").order_by("-timestamp")

def get_fund_model_input(fund):
    try:
        return ModelInput.objects.get(fund=fund)
    except ModelInput.DoesNotExist:
        return None
