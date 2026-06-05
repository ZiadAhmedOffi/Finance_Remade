from decimal import Decimal
from django.utils import timezone
from ..models import RealEstateReport, RealEstatePortfolio
from .portfolio_dashboard_selectors import PortfolioDashboardSelector
from .cash_flow_selectors import CashFlowSelectors
from users.services.permission_service import PermissionService

class RealEstateReportSelector:
    @staticmethod
    def get_report_by_id(report_id):
        try:
            return RealEstateReport.objects.get(id=report_id)
        except RealEstateReport.DoesNotExist:
            return None

    @staticmethod
    def get_reports_by_type(user, report_type="DYNAMIC"):
        if PermissionService.is_super_admin(user):
            return RealEstateReport.objects.filter(report_type=report_type)
        else:
            # Assuming portfolios have similar access control or RBAC
            # For now, super admin or let view logic handle it via can_view_portfolio
            return RealEstateReport.objects.filter(report_type=report_type)

    @staticmethod
    def get_portfolio_performance_data(portfolio: RealEstatePortfolio, reference_date=None):
        """
        Aggregates institutional-grade performance data for a portfolio.
        Includes FFO, AFFO, LTV, IRR, and Yields.
        """
        if reference_date is None:
            reference_date = timezone.now().date()
            
        dashboard_data = PortfolioDashboardSelector.get_dashboard_data(portfolio, reference_date)
        cf_data = CashFlowSelectors.get_portfolio_cash_flow(portfolio)
        
        # 1. Calculate FFO and AFFO for current year
        current_year = reference_date.year
        
        # FFO = NOI - Interest + Depreciation (but Depreciation is non-cash, 
        # usually FFO adds it back to Net Income. Since NOI is pre-interest and pre-depreciation:
        # FFO = NOI - Interest
        # Wait, usually Net Income = NOI - Interest - Depreciation.
        # FFO = Net Income + Depreciation = (NOI - Interest - Depreciation) + Depreciation = NOI - Interest.
        
        # We need annual interest
        total_interest = Decimal('0.00')
        total_maintenance = Decimal('0.00')
        
        for prop_id, prop_cf in cf_data['properties'].items():
            metadata = prop_cf['metadata'].get(current_year, {})
            total_interest += metadata.get('interest', Decimal('0.00'))
            total_maintenance += metadata.get('maintenance_costs', Decimal('0.00'))

        ffo = dashboard_data['metrics']['total_noi'] - total_interest
        # AFFO = FFO - Maintenance Capex
        affo = ffo - total_maintenance
        
        # 2. Debt Metrics
        total_debt = Decimal('0.00')
        # We can sum up loan_amounts or remaining balances if we had them easily.
        # For now, let's look at financing entries.
        for prop in portfolio.properties.filter(financing__isnull=False):
            total_debt += prop.financing.loan_amount
            # Ideally we subtract repayments made so far.
            # Amortization schedule logic could be used here for more accuracy.
        
        ltv = Decimal('0.00')
        if dashboard_data['metrics']['portfolio_market_value'] > 0:
            ltv = (total_debt / dashboard_data['metrics']['portfolio_market_value']) * Decimal('100')

        # 3. Add to response
        performance_data = {
            **dashboard_data,
            "institutional_metrics": {
                "ffo": ffo,
                "affo": affo,
                "total_debt": total_debt,
                "ltv_percentage": ltv.quantize(Decimal('0.01')),
                "interest_coverage_ratio": (dashboard_data['metrics']['total_noi'] / total_interest) if total_interest > 0 else None,
            },
            "reference_date": reference_date.isoformat(),
        }
        
        return performance_data
