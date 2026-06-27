from funds.models import Fund, FundLog, ModelInput, InvestorAction, CurrentDeal, Distribution
from users.services.permission_service import PermissionService
from funds.utils import calculators
from funds.selectors import deal_selectors
from datetime import datetime, date
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone


def get_fund_portfolio_values_by_year(fund, start_year=None, end_year=None):
    """
    Calculates the total fund portfolio value for each year in the requested range.
    """
    model_inputs = get_fund_model_input(fund)
    if not model_inputs:
        return {}

    inception_year = int(model_inputs.inception_year)
    current_year = datetime.now().year
    fund_life = int(model_inputs.fund_life)
    fund_end_year = inception_year + fund_life

    deals = list(deal_selectors.get_deals_for_fund(fund))
    current_deals = list(deal_selectors.get_current_deals_for_fund(fund))

    p_injections_by_year = deal_selectors.get_prognosis_injections(fund)
    c_injections_by_year = deal_selectors.get_current_injections(fund)

    gross_exit_value_future = sum(
        float(deal_selectors.calculate_investment_deal_exit_value(deal))
        for deal in deals
        if deal.entry_year >= current_year
    )
    p_injections_future = {yr: amt for yr, amt in p_injections_by_year.items() if yr >= current_year}
    p_solver_injections = p_injections_future if p_injections_future else p_injections_by_year
    irr = calculators.solve_implied_return_rate(p_solver_injections, fund_end_year, gross_exit_value_future)

    c_gross_exit_value = sum(
        deal_selectors.calculate_current_deal_final_exit_amount(deal)
        for deal in current_deals
    )
    historical_target_year = current_year - 1
    c_irr = calculators.solve_implied_return_rate(c_injections_by_year, historical_target_year, c_gross_exit_value)

    safe_c_irr = c_irr if c_irr and c_irr > -1 else 0.0
    safe_p_irr = irr if irr and irr > -1 else 0.0

    all_entry_years = [d.entry_year for d in deals] + [d.entry_year for d in current_deals]
    actual_start_year = min(inception_year, min(all_entry_years)) if all_entry_years else inception_year
    actual_end_year = fund_end_year if end_year is None else end_year
    if start_year is not None:
        actual_start_year = min(actual_start_year, start_year)

    trajectory = calculators.calculate_nav_trajectory(
        actual_start_year,
        actual_end_year,
        current_year,
        fund_end_year,
        c_injections_by_year,
        p_injections_by_year,
        safe_c_irr,
        safe_p_irr,
    )

    return {point["year"]: point["c_pv"] + point["p_pv"] for point in trajectory}

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

def get_fund_nav_metrics(fund, reference_date=None):
    """
    Calculates NAV and Cash Reserves for a fund.
    NAV = Value of Held Assets + Cash Reserves
    Cash Reserves = Total Primary Injections - Total Cash Invested in Deals + Total Distribution Proceeds
    """
    if reference_date is None:
        reference_date = timezone.now().date()
    
    ref_year = reference_date.year

    # 1. Total Value of Held Assets (Current Deals)
    current_portfolio_value = get_total_fund_portfolio(fund, ref_year)

    # 2. Total Primary Injections (Investor Inflows)
    investments_qs = InvestorAction.objects.filter(fund=fund, type="PRIMARY_INVESTMENT")
    total_injections = investments_qs.filter(year__lte=ref_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # 3. Total Cash Invested in Deals (Outflows)
    total_deal_outflow = CurrentDeal.objects.filter(fund=fund, entry_year__lte=ref_year).aggregate(total=Sum('amount_invested'))['total'] or Decimal('0.00')
    
    # 4. Total Distribution Proceeds (Inflows)
    total_distributions = Distribution.objects.filter(fund=fund, date__lte=reference_date).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # 5. Cash Reserves
    cash_reserves = Decimal(str(total_injections)) - Decimal(str(total_deal_outflow)) + Decimal(str(total_distributions))
    
    # 6. NAV
    nav = Decimal(str(current_portfolio_value)) + cash_reserves

    # Total Units at reference date
    total_units_at_ref = get_total_units_at_year(fund, ref_year)
    if total_units_at_ref == 0:
        total_units_at_ref = float(fund.total_units)

    return {
        "current_portfolio_value": float(current_portfolio_value),
        "total_injections": float(total_injections),
        "total_distributions": float(total_distributions),
        "cash_reserves": float(cash_reserves),
        "nav": float(nav),
        "total_units": total_units_at_ref,
        "price_per_unit": float(nav / Decimal(str(total_units_at_ref))) if total_units_at_ref > 0 else 1.0,
    }

def get_total_fund_portfolio(fund, year):
    """
    Calculates the total fund portfolio value at the end of a given year.
    """
    return get_fund_portfolio_values_by_year(fund, end_year=year).get(year, 0.0)

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
