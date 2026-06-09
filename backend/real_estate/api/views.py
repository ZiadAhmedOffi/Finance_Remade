from decimal import Decimal
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .serializers import (
    RealEstatePortfolioSerializer, 
    RealEstateAssumptionsSerializer,
    PropertySerializer,
    PropertyWithMetricsSerializer,
    FinancingEntrySerializer,
    FinancingEntryWithMetricsSerializer,
    InstallmentEntrySerializer,
    InstallmentEntryWithMetricsSerializer,
    OffPlanDetailsSerializer,
    OffPlanMilestoneSerializer,
    PropertySaleSerializer,
    PropertySaleWithMetricsSerializer,
    RealEstatePossibleCapitalSourceSerializer,
    RealEstateInvestorActionSerializer,
    RealEstateInvestorStatsSerializer,
    JurisdictionSerializer,
    TaxRuleSerializer,
    LedgerYearSerializer,
    LedgerTransactionSerializer,
    LedgerAccountSerializer,
    RealEstateReportSerializer
)
from ..models import (
    FinancingEntry, 
    Property, 
    OffPlanMilestone, 
    PropertySale, 
    RealEstateInvestorAction, 
    RealEstatePossibleCapitalSource,
    InstallmentEntry,
    Jurisdiction,
    TaxRule,
    LedgerYear,
    LedgerAccount,
    RealEstatePortfolio,
    RealEstateReport
)
from ..selectors.portfolio_selectors import PortfolioSelectors
from ..selectors.property_selectors import PropertySelector
from ..selectors.financing_selectors import FinancingSelectors
from ..selectors.installment_selectors import InstallmentSelectors
from ..selectors.off_plan_selectors import OffPlanSelectors
from ..selectors.property_sale_selectors import PropertySaleSelector
from ..selectors.cash_flow_selectors import CashFlowSelectors
from ..selectors.portfolio_dashboard_selectors import PortfolioDashboardSelector
from ..selectors.investor_selectors import RealEstateInvestorSelector
from ..selectors.taxation_selectors import TaxationAnalysisSelector
from ..selectors.ledger_selectors import LedgerSelectors
from ..selectors.report_selectors import RealEstateReportSelector

from ..services.portfolio_service import PortfolioService
from ..services.property_service import PropertyService
from ..services.financing_service import FinancingService
from ..services.installment_service import InstallmentService
from ..services.off_plan_service import OffPlanService
from ..services.property_sale_service import PropertySaleService
from ..services.investor_service import RealEstateInvestorService
from ..services.ledger_service import LedgerYearService, LedgerTransactionService
from ..services.ledger_sync_service import LedgerSyncService
from ..services.report_service import RealEstateReportService
from users.services.permission_service import PermissionService

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from funds.interfaces.user_service_adapter import UserServiceAdapter
user_adapter = UserServiceAdapter()

class JurisdictionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = JurisdictionSerializer
    queryset = Jurisdiction.objects.all()

    def get_queryset(self):
        return Jurisdiction.objects.all().prefetch_related('rules')

class TaxRuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TaxRuleSerializer
    queryset = TaxRule.objects.all()

    def get_queryset(self):
        jurisdiction_id = self.request.query_params.get('jurisdiction')
        if jurisdiction_id:
            return TaxRule.objects.filter(jurisdiction_id=jurisdiction_id)
        return TaxRule.objects.all()

class RealEstatePortfolioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RealEstatePortfolioSerializer

    def get_queryset(self):
        user = self.request.user
        if PermissionService.is_super_admin(user):
            return PortfolioSelectors.get_portfolios()
        
        # For non-superadmins, we should filter based on role assignments
        from users.models import UserRoleAssignment
        portfolio_ids = UserRoleAssignment.objects.filter(
            user=user,
            real_estate_portfolio__isnull=False
        ).values_list('real_estate_portfolio_id', flat=True)
        
        return PortfolioSelectors.get_portfolios().filter(id__in=portfolio_ids)

    def create(self, request, *args, **kwargs):
        if not PermissionService.is_super_admin(request.user):
            raise PermissionDenied("Only superadmins can create portfolios.")
        
        portfolio = PortfolioService.create_portfolio(
            actor=request.user,
            data=request.data
        )
        serializer = self.get_serializer(portfolio)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'put', 'patch'], url_path='assumptions')
    def assumptions(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this portfolio's assumptions.")

        if request.method == 'GET':
            serializer = RealEstateAssumptionsSerializer(portfolio.assumptions)
            return Response(serializer.data)
        
        elif request.method in ['PUT', 'PATCH']:
            if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
                raise PermissionDenied("You do not have permission to edit this portfolio's assumptions.")
                
            assumptions = PortfolioService.update_assumptions(
                actor=request.user,
                portfolio=portfolio,
                data=request.data
            )
            serializer = RealEstateAssumptionsSerializer(assumptions)
            return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], url_path='properties')
    def properties(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this portfolio's properties.")

        if request.method == 'GET':
            reference_date_str = request.query_params.get('reference_date')
            reference_date = None
            if reference_date_str:
                try:
                    reference_date = datetime.strptime(reference_date_str, '%Y-%m-%d').date()
                except ValueError:
                    return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
            
            properties_with_metrics = PropertySelector.get_properties_for_portfolio(
                portfolio, 
                reference_date=reference_date
            )
            serializer = PropertyWithMetricsSerializer(properties_with_metrics, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
                raise PermissionDenied("You do not have permission to add properties to this portfolio.")
            
            property_obj = PropertyService.create_property(portfolio, request.data)
            serializer = PropertySerializer(property_obj)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['put', 'patch', 'delete'], url_path='properties/(?P<property_id>[^/.]+)')
    def manage_property(self, request, pk=None, property_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        
        if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to manage properties in this portfolio.")
            
        try:
            property_obj = portfolio.properties.get(id=property_id)
        except:
            return Response({"error": "Property not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.method in ['PUT', 'PATCH']:
            updated_property = PropertyService.update_property(property_obj, request.data)
            serializer = PropertySerializer(updated_property)
            return Response(serializer.data)
            
        elif request.method == 'DELETE':
            property_obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='financing')
    def financing(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this portfolio's financing model.")

        if request.method == 'GET':
            mortgages = FinancingSelectors.get_financing_entries_for_portfolio(portfolio)
            installments = InstallmentSelectors.get_installment_entries_for_portfolio(portfolio)
            
            return Response({
                "mortgages": FinancingEntryWithMetricsSerializer(mortgages, many=True).data,
                "installments": InstallmentEntryWithMetricsSerializer(installments, many=True).data
            })
        
        elif request.method == 'POST':
            if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
                raise PermissionDenied("You do not have permission to add financing entries to this portfolio.")
            
            try:
                property_id = request.data.get('property')
                property_obj = portfolio.properties.get(id=property_id)
            except:
                return Response({"error": "Property not found in this portfolio."}, status=status.HTTP_404_NOT_FOUND)
                
            try:
                entry = FinancingService.create_financing_entry(property_obj=property_obj, data=request.data)
                serializer = FinancingEntrySerializer(entry)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put', 'patch', 'delete'], url_path='financing/(?P<entry_id>[0-9a-f-]+)')
    def manage_financing(self, request, pk=None, entry_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        
        if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to manage financing entries in this portfolio.")
            
        try:
            entry = FinancingEntry.objects.get(id=entry_id, property__portfolio=portfolio)
        except:
            return Response({"error": "Financing entry not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.method in ['PUT', 'PATCH']:
            updated_entry = FinancingService.update_financing_entry(entry=entry, data=request.data)
            serializer = FinancingEntrySerializer(updated_entry)
            return Response(serializer.data)
            
        elif request.method == 'DELETE':
            FinancingService.delete_financing_entry(entry=entry)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='installments')
    def installments(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
            raise PermissionDenied("Access denied.")

        try:
            property_id = request.data.get('property')
            property_obj = portfolio.properties.get(id=property_id)
        except:
            return Response({"error": "Property not found in this portfolio."}, status=status.HTTP_404_NOT_FOUND)

        try:
            entry = InstallmentService.create_installment_entry(property_obj=property_obj, data=request.data)
            serializer = InstallmentEntrySerializer(entry)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put', 'patch', 'delete'], url_path='installments/(?P<installment_id>[0-9a-f-]+)')
    def manage_installment(self, request, pk=None, installment_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
            raise PermissionDenied("Access denied.")

        try:
            entry = InstallmentEntry.objects.get(id=installment_id, property__portfolio=portfolio)
        except InstallmentEntry.DoesNotExist:
            return Response({"error": "Installment entry not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.method in ['PUT', 'PATCH']:
            updated_entry = InstallmentService.update_installment_entry(entry=entry, data=request.data)
            serializer = InstallmentEntrySerializer(updated_entry)
            return Response(serializer.data)
            
        elif request.method == 'DELETE':
            InstallmentService.delete_installment_entry(entry=entry)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='financing/amortization-total')
    def portfolio_amortization(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this portfolio's amortization schedule.")

        schedule = FinancingSelectors.get_portfolio_total_amortization(portfolio)
        return Response(schedule)

    @action(detail=True, methods=['get'], url_path='financing/(?P<entry_id>[^/.]+)/amortization')
    def entry_amortization(self, request, pk=None, entry_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this amortization schedule.")
            
        try:
            entry = FinancingEntry.objects.get(id=entry_id, property__portfolio=portfolio)
        except:
            return Response({"error": "Financing entry not found"}, status=status.HTTP_404_NOT_FOUND)

        schedule = FinancingSelectors.get_amortization_schedule(entry)
        return Response(schedule)

    @action(detail=True, methods=['get'], url_path='installments-schedule-total')
    def portfolio_installments_schedule(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("Access denied.")

        schedule = InstallmentSelectors.get_portfolio_total_installments(portfolio)
        return Response(schedule)

    @action(detail=True, methods=['get'], url_path='installments/(?P<installment_id>[^/.]+)/schedule')
    def installment_schedule(self, request, pk=None, installment_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("Access denied.")

        try:
            entry = InstallmentEntry.objects.get(id=installment_id, property__portfolio=portfolio)
        except InstallmentEntry.DoesNotExist:
            return Response({"error": "Installment entry not found"}, status=status.HTTP_404_NOT_FOUND)

        schedule = InstallmentSelectors.get_installment_schedule(entry)
        return Response(schedule)

    @action(detail=True, methods=['get', 'post'], url_path='off-plan')
    def off_plan_model(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this portfolio's off-plan model.")

        data = OffPlanSelectors.get_off_plan_data_for_portfolio(portfolio)
        return Response(data)

    @action(detail=True, methods=['patch'], url_path='off-plan/(?P<property_id>[0-9a-f-]+)/details')
    def update_off_plan_details(self, request, pk=None, property_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to edit off-plan details.")

        try:
            property_obj = portfolio.properties.get(id=property_id, status="OFF_PLAN")
        except Property.DoesNotExist:
            return Response({"error": "Off-plan property not found."}, status=status.HTTP_404_NOT_FOUND)

        details = OffPlanService.update_off_plan_details(property_obj, request.data)
        serializer = OffPlanDetailsSerializer(details)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], url_path='off-plan/(?P<property_id>[0-9a-f-]+)/schedule')
    def off_plan_schedule(self, request, pk=None, property_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this off-plan schedule.")

        try:
            property_obj = portfolio.properties.get(id=property_id, status="OFF_PLAN")
        except Property.DoesNotExist:
            return Response({"error": "Off-plan property not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'GET':
            data = OffPlanSelectors.get_payment_schedule(property_obj)
            return Response(data)
        
        elif request.method == 'POST':
            if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
                raise PermissionDenied("You do not have permission to add milestones.")
            
            milestone = OffPlanService.create_milestone(property_obj, request.data)
            serializer = OffPlanMilestoneSerializer(milestone)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path='off-plan/milestones/(?P<milestone_id>[0-9a-f-]+)')
    def manage_milestone(self, request, pk=None, milestone_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to manage milestones.")

        try:
            milestone = OffPlanMilestone.objects.get(id=milestone_id, property__portfolio=portfolio)
        except OffPlanMilestone.DoesNotExist:
            return Response({"error": "Milestone not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'PATCH':
            updated_milestone = OffPlanService.update_milestone(milestone_id, request.data)
            serializer = OffPlanMilestoneSerializer(updated_milestone)
            return Response(serializer.data)
            
        elif request.method == 'DELETE':
            OffPlanService.delete_milestone(milestone_id)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='cash-flow')
    def cash_flow(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this portfolio's cash flow model.")

        start_year = request.query_params.get('start_year')
        end_year = request.query_params.get('end_year')
        
        if start_year: start_year = int(start_year)
        if end_year: end_year = int(end_year)

        data = CashFlowSelectors.get_portfolio_cash_flow(portfolio, start_year, end_year)
        return Response(data)

    @action(detail=True, methods=['get', 'post'], url_path='sales')
    def sales(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this portfolio's sales and disposals.")

        if request.method == 'GET':
            sales_with_metrics = PropertySaleSelector.get_sales_for_portfolio(portfolio)
            serializer = PropertySaleWithMetricsSerializer(sales_with_metrics, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
                raise PermissionDenied("You do not have permission to add sales entries to this portfolio.")
            
            try:
                property_id = request.data.get('property')
                property_obj = portfolio.properties.get(id=property_id)
            except:
                return Response({"error": "Property not found in this portfolio."}, status=status.HTTP_404_NOT_FOUND)
                
            try:
                sale = PropertySaleService.create_property_sale(property_obj=property_obj, data=request.data)
                serializer = PropertySaleSerializer(sale)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put', 'patch', 'delete'], url_path='sales/(?P<sale_id>[0-9a-f-]+)')
    def manage_sale(self, request, pk=None, sale_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        
        if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to manage sales entries in this portfolio.")
            
        try:
            sale = PropertySale.objects.get(id=sale_id, property__portfolio=portfolio)
        except:
            return Response({"error": "Sale entry not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.method in ['PUT', 'PATCH']:
            updated_sale = PropertySaleService.update_property_sale(sale=sale, data=request.data)
            serializer = PropertySaleSerializer(updated_sale)
            return Response(serializer.data)
            
        elif request.method == 'DELETE':
            PropertySaleService.delete_property_sale(sale=sale)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='dashboard')
    def dashboard(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this portfolio's dashboard.")

        reference_date_str = request.query_params.get('reference_date')
        reference_date = None
        if reference_date_str:
            try:
                reference_date = datetime.strptime(reference_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        data = PortfolioDashboardSelector.get_dashboard_data(portfolio, reference_date=reference_date)
        return Response(data)

    @action(detail=True, methods=['get'], url_path='tax-analysis')
    def taxation_analysis(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this portfolio's tax analysis.")

        data = TaxationAnalysisSelector.get_taxation_analysis(portfolio)
        return Response(data)

    @action(detail=True, methods=['get'], url_path='investors')
    def list_investors(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        investors = user_adapter.get_investors_for_re_portfolio(pk)
        data = [{"id": str(u.id), "email": u.email, "first_name": u.first_name, "last_name": u.last_name} for u in investors]
        return Response(data)

    @action(detail=True, methods=['get'], url_path='investor-log')
    def investor_log(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        assumptions = getattr(portfolio, "assumptions", None)
        if not assumptions:
             return Response({"error": "Assumptions not found"}, status=status.HTTP_400_BAD_REQUEST)

        inception_date = assumptions.inception_date
        inception_year = inception_date.year
        end_year = inception_year + assumptions.forecast_horizon - 1
        
        # 1. Investor Table Data (Current)
        investor_stats = RealEstateInvestorSelector.get_investor_stats(portfolio)
        investors_list = RealEstateInvestorStatsSerializer(investor_stats, many=True).data
        total_units_current = float(portfolio.total_units)
        for inv in investors_list:
            inv["ownership_percentage"] = (float(inv["units"]) / total_units_current * 100.0) if total_units_current > 0 else 0.0

        # 2. Unified Capital Pipeline (Historical + Projections)
        pipeline = RealEstateInvestorSelector.get_unified_capital_pipeline(portfolio)
        investor_actions = RealEstateInvestorSelector.get_investor_actions(portfolio)
        
        # Aggregate Invested Capital by year (Primary only)
        invested_by_year = {}
        for action in investor_actions:
            if action.type == "PRIMARY_INVESTMENT":
                invested_by_year[action.year] = invested_by_year.get(action.year, 0.0) + float(action.amount)

        possible_sources = portfolio.possible_capital_sources.all()
        possible_by_year = {}
        for source in possible_sources:
            possible_by_year[source.year] = possible_by_year.get(source.year, 0.0) + float(source.amount)

        graph_data = []
        cumulative_invested = 0.0
        cumulative_required = 0.0
        cumulative_possible = 0.0

        for yr in range(inception_year, end_year + 1):
            year_data = pipeline.get(yr)
            if not year_data:
                continue

            cumulative_invested += invested_by_year.get(yr, 0.0)
            cumulative_required += float(year_data["net_required"])
            cumulative_possible += possible_by_year.get(yr, 0.0)
            
            # Point-in-time NAV Metrics
            ref_date = datetime(yr, 12, 31).date()
            nav_metrics = PortfolioSelectors.get_portfolio_nav_metrics(portfolio, reference_date=ref_date)
            
            graph_data.append({
                "year": yr,
                "is_actuals": year_data["is_actuals"],
                "total_capital_invested": float(cumulative_invested),
                "total_capital_required": float(cumulative_required),
                "total_capital_with_possible": float(cumulative_invested + cumulative_possible),
                "portfolio_value": float(nav_metrics["nav"]),
                "units_at_year": float(nav_metrics["total_units"]),
                "price_per_unit": float(nav_metrics["price_per_unit"]),
                "cash_reserves": float(nav_metrics["cash_reserves"]),
                "assets_value": float(nav_metrics["total_market_value_held"]),
                "capital_breakdown": year_data["breakdown"],
                "yearly_required": float(year_data["net_required"]),
                "uses": float(year_data["uses"]),
                "sources": float(year_data["sources"]),
                "assets_breakdown": nav_metrics["assets_breakdown"],
                "cash_breakdown": nav_metrics["cash_change_breakdown"],
                "assets_change_breakdown": nav_metrics.get("assets_change_breakdown", [])
            })

        # 3. Final Metrics & Comparison
        final_nav_metrics = PortfolioSelectors.get_portfolio_nav_metrics(portfolio)
        
        # Calculate NAV for the end of the previous year
        prev_year = datetime.now().year - 1
        ref_date_prev = datetime(prev_year, 12, 31).date()
        prev_nav_metrics = PortfolioSelectors.get_portfolio_nav_metrics(portfolio, reference_date=ref_date_prev)

        # Dashboard-level metrics for the card view
        dashboard_data = PortfolioDashboardSelector.get_dashboard_data(portfolio)
        aggregated = dashboard_data.get("metrics", {})

        return Response({
            "investors": investors_list,
            "graph_data": graph_data,
            "actions": RealEstateInvestorActionSerializer(investor_actions, many=True).data,
            "possible_capital_sources": RealEstatePossibleCapitalSourceSerializer(possible_sources, many=True).data,
            "total_units": total_units_current,
            "nav_metrics": {
                "total_market_value_held": float(final_nav_metrics["total_market_value_held"]),
                "total_investments": float(final_nav_metrics["total_investments"]),
                "total_net_proceeds": float(final_nav_metrics["total_net_proceeds"]),
                "cash_reserves": float(final_nav_metrics["cash_reserves"]),
                "nav": float(final_nav_metrics["nav"]),
                "total_units": float(final_nav_metrics["total_units"]),
                "price_per_unit": float(final_nav_metrics["price_per_unit"]),
                "prev_year_nav": float(prev_nav_metrics["nav"]),
                "prev_year_price_per_unit": float(prev_nav_metrics["price_per_unit"]),
                "prev_year_market_value": float(prev_nav_metrics["total_market_value_held"]),
                "prev_year_invested_capital": float(prev_nav_metrics["total_investments"]),
                "prev_year": prev_year,
                # New Card Metrics
                "developer": assumptions.developer,
                "liquidation_index": dashboard_data.get("liquidation_index", {}).get("portfolio_average", 0),
                "portfolio_irr": float(aggregated.get("portfolio_simple_irr", 0)),
                "irr_yield": float(aggregated.get("portfolio_net_yield", 0)),
                "irr_capital_growth": float(aggregated.get("portfolio_avg_appreciation", 0)),
                "weighted_net_yield": float(aggregated.get("portfolio_net_yield", 0)),
                "weighted_occupancy": float(100.0 - float(aggregated.get("portfolio_vacancy_rate", 0))),
                "property_count_active": aggregated.get("property_count_active", 0),
                "annual_cash_flow_current": float(aggregated.get("net_cash_flow_y1", 0)),
                # Calculate prev year cash flow for YOY comparison
                "annual_cash_flow_prev": float(PortfolioDashboardSelector.get_dashboard_data(portfolio, reference_date=ref_date_prev).get("metrics", {}).get("net_cash_flow_y1", 0))
            }
        })

    @action(detail=True, methods=['get', 'post'], url_path='investor-actions')
    def investor_actions(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        if request.method == 'GET':
            actions = RealEstateInvestorSelector.get_investor_actions(portfolio)
            serializer = RealEstateInvestorActionSerializer(actions, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
                raise PermissionDenied("Access denied.")
            
            serializer = RealEstateInvestorActionSerializer(data=request.data)
            if serializer.is_valid():
                try:
                    action_obj = RealEstateInvestorService.create_investor_action(
                        actor=request.user,
                        data={**serializer.validated_data, "portfolio": portfolio}
                    )
                    return Response(RealEstateInvestorActionSerializer(action_obj).data, status=status.HTTP_201_CREATED)
                except ValueError as e:
                    return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='investor-actions/(?P<action_id>[0-9a-f-]+)')
    def manage_investor_action(self, request, pk=None, action_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        action_obj = RealEstateInvestorSelector.get_investor_action_by_id(action_id)
        if not action_obj or action_obj.portfolio != portfolio:
            return Response({"error": "Action not found"}, status=status.HTTP_404_NOT_FOUND)
        
        RealEstateInvestorService.delete_investor_action(action_obj)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='possible-capital-sources')
    def possible_capital_sources(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        if request.method == 'GET':
            sources = portfolio.possible_capital_sources.all()
            serializer = RealEstatePossibleCapitalSourceSerializer(sources, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
                raise PermissionDenied("Access denied.")
            
            serializer = RealEstatePossibleCapitalSourceSerializer(data=request.data)
            if serializer.is_valid():
                source = serializer.save(portfolio=portfolio)
                return Response(RealEstatePossibleCapitalSourceSerializer(source).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='possible-capital-sources/(?P<source_id>[0-9a-f-]+)')
    def manage_possible_source(self, request, pk=None, source_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
            raise PermissionDenied("Access denied.")
            
        try:
            source = portfolio.possible_capital_sources.get(id=source_id)
            source.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except RealEstatePossibleCapitalSource.DoesNotExist:
            return Response({"error": "Source not found"}, status=status.HTTP_404_NOT_FOUND)

    # -----------------------------
    # Bookkeeping Actions
    # -----------------------------
    @action(detail=True, methods=['get'], url_path='ledgers')
    def ledgers(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_ledger(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        years = LedgerSelectors.get_ledger_years(portfolio)
        serializer = LedgerYearSerializer(years, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='ledgers/initialize')
    def initialize_ledger(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_edit_ledger(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        year = request.data.get('year')
        if not year:
            return Response({"error": "Year is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            year = int(year)
            LedgerSyncService.sync_historical_data(portfolio, year)
            ledger_year = LedgerYear.objects.get(portfolio=portfolio, year=year)
            serializer = LedgerYearSerializer(ledger_year)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='ledgers/(?P<year_id>[0-9a-f-]+)/sync-cash-flow')
    def sync_cash_flow(self, request, pk=None, year_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_edit_ledger(request.user, portfolio):
            raise PermissionDenied("Access denied.")

        try:
            ledger_year = LedgerSelectors.get_ledger_year_by_id(year_id)
            LedgerSyncService.sync_projected_cash_flow(portfolio, ledger_year.year)
            return Response({"message": "Cash flow synced successfully."})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        
    @action(detail=True, methods=['post'], url_path='ledgers/(?P<year_id>[0-9a-f-]+)/close')
    def trial_balance(self, request, pk=None, year_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_ledger(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        try:
            ledger_year = LedgerSelectors.get_ledger_year_by_id(year_id)
            if ledger_year.portfolio != portfolio:
                return Response({"error": "Ledger year not found for this portfolio."}, status=status.HTTP_404_NOT_FOUND)
            
            data = LedgerSelectors.get_trial_balance(ledger_year)
            return Response(data)
        except LedgerYear.DoesNotExist:
            return Response({"error": "Ledger year not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'], url_path='ledgers/(?P<year_id>[0-9a-f-]+)/accounts/(?P<account_id>[0-9a-f-]+)/t-account')
    def t_account(self, request, pk=None, year_id=None, account_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_ledger(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        try:
            ledger_year = LedgerSelectors.get_ledger_year_by_id(year_id)
            account = LedgerAccount.objects.get(id=account_id, portfolio=portfolio)
            
            data = LedgerSelectors.get_t_account_details(ledger_year, account)
            return Response(data)
        except (LedgerYear.DoesNotExist, LedgerAccount.DoesNotExist):
            return Response({"error": "Resource not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='ledgers/(?P<year_id>[0-9a-f-]+)/transactions')
    def manual_transaction(self, request, pk=None, year_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_edit_ledger(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        try:
            ledger_year = LedgerSelectors.get_ledger_year_by_id(year_id)
            
            # Extract entries and convert to LedgerAccount objects
            entries_data = request.data.get('entries', [])
            processed_entries = []
            for e in entries_data:
                account = LedgerAccount.objects.get(id=e['account_id'], portfolio=portfolio)
                processed_entries.append({
                    "account": account,
                    "amount": Decimal(str(e['amount'])),
                    "entry_type": e['entry_type']
                })
            
            transaction_obj = LedgerTransactionService.create_transaction(
                portfolio=portfolio,
                ledger_year=ledger_year,
                description=request.data.get('description'),
                date=datetime.strptime(request.data.get('date'), '%Y-%m-%d').date(),
                entries=processed_entries
            )
            
            serializer = LedgerTransactionSerializer(transaction_obj)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='ledgers/(?P<year_id>[0-9a-f-]+)/pl-statement')
    def pl_statement(self, request, pk=None, year_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_ledger(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        try:
            ledger_year = LedgerSelectors.get_ledger_year_by_id(year_id)
            if ledger_year.portfolio != portfolio:
                return Response({"error": "Ledger year not found for this portfolio."}, status=status.HTTP_404_NOT_FOUND)
            
            data = LedgerSelectors.get_pl_statement(ledger_year)
            return Response(data)
        except LedgerYear.DoesNotExist:
            return Response({"error": "Ledger year not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'], url_path='ledgers/templates')
    def transaction_templates(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        accounts = LedgerAccount.objects.filter(portfolio=portfolio)
        
        def get_acc_id(name):
            acc = accounts.filter(name=name).first()
            return str(acc.id) if acc else None

        templates = [
            {
                "name": "General Expense",
                "entries": [
                    {"account_id": get_acc_id("Cash"), "entry_type": "CREDIT", "amount": 0},
                    {"account_id": None, "entry_type": "DEBIT", "amount": 0}
                ]
            },
            {
                "name": "Mortgage Interest Payment",
                "entries": [
                    {"account_id": get_acc_id("Financing Expenses"), "entry_type": "DEBIT", "amount": 0},
                    {"account_id": get_acc_id("Cash"), "entry_type": "CREDIT", "amount": 0}
                ]
            },
            {
                "name": "Mortgage Principal Payment",
                "entries": [
                    {"account_id": get_acc_id("Mortgage Payable"), "entry_type": "DEBIT", "amount": 0},
                    {"account_id": get_acc_id("Cash"), "entry_type": "CREDIT", "amount": 0}
                ]
            },
            {
                "name": "Depreciation Entry",
                "entries": [
                    {"account_id": get_acc_id("Depreciation Expense"), "entry_type": "DEBIT", "amount": 0},
                    {"account_id": get_acc_id("Retained Earnings"), "entry_type": "CREDIT", "amount": 0}
                ]
            },
            {
                "name": "Capital Injection",
                "entries": [
                    {"account_id": get_acc_id("Cash"), "entry_type": "DEBIT", "amount": 0},
                    {"account_id": get_acc_id("Paid-in Capital"), "entry_type": "CREDIT", "amount": 0}
                ]
            },
            {
                "name": "Rental Income",
                "entries": [
                    {"account_id": get_acc_id("Cash"), "entry_type": "DEBIT", "amount": 0},
                    {"account_id": get_acc_id("Rental Income"), "entry_type": "CREDIT", "amount": 0}
                ]
            }
        ]
        return Response(templates)

    @action(detail=True, methods=['post'], url_path='ledgers/(?P<year_id>[0-9a-f-]+)/close')
    def close_ledger(self, request, pk=None, year_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_finalize_ledger(request.user, portfolio):
            raise PermissionDenied("Access denied.")
        
        try:
            ledger_year = LedgerSelectors.get_ledger_year_by_id(year_id)
            ledger_year = LedgerYearService.close_year(ledger_year, request.user)
            serializer = LedgerYearSerializer(ledger_year)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='ledgers/(?P<year_id>[0-9a-f-]+)/delete')
    def delete_ledger(self, request, pk=None, year_id=None):
        if not PermissionService.is_super_admin(request.user):
            raise PermissionDenied("Only superadmins can delete ledgers.")
        
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        try:
            ledger_year = LedgerSelectors.get_ledger_year_by_id(year_id)
            if ledger_year.portfolio != portfolio:
                return Response({"error": "Ledger year not found for this portfolio."}, status=status.HTTP_404_NOT_FOUND)
            
            LedgerYearService.delete_year(ledger_year)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class RealEstateReportListView(APIView):
    """
    Lists all reports for a specific portfolio.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolio_id = request.query_params.get("portfolio_id")
        if not portfolio_id:
            return Response({"error": "portfolio_id query param is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        portfolio = get_object_or_404(RealEstatePortfolio, id=portfolio_id)
        if not PermissionService.is_super_admin(request.user):
            # For now, strict check. Could be expanded to SC roles.
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
            
        reports = portfolio.reports.all()
        return Response(RealEstateReportSerializer(reports, many=True).data)

    def post(self, request):
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Only super admins can create reports."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            report = RealEstateReportService.create_report(
                actor=request.user,
                data=request.data,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response(RealEstateReportSerializer(report).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class RealEstateReportDetailView(APIView):
    """
    Handles updating and deleting specific reports.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, report_id):
        report = RealEstateReportSelector.get_report_by_id(report_id)
        if not report:
             return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Super admin check for now
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        return Response(RealEstateReportSerializer(report).data)

    def patch(self, request, report_id):
        report = RealEstateReportSelector.get_report_by_id(report_id)
        if not report:
             return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
             
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            report = RealEstateReportService.update_report(
                actor=request.user,
                report=report,
                data=request.data,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response(RealEstateReportSerializer(report).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, report_id):
        report = RealEstateReportSelector.get_report_by_id(report_id)
        if not report:
             return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
             
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        RealEstateReportService.delete_report(
            actor=request.user,
            report=report,
            ip_address=request.META.get("REMOTE_ADDR")
        )
        return Response({"message": "Report deleted."}, status=status.HTTP_200_OK)

class RealEstateReportRegenerateView(APIView):
    """
    Triggers regeneration of the static report.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, report_id):
        report = RealEstateReportSelector.get_report_by_id(report_id)
        if not report:
            return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
            
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            
        report = RealEstateReportService.regenerate_report(
            actor=request.user,
            report=report,
            ip_address=request.META.get("REMOTE_ADDR")
        )
        return Response(RealEstateReportSerializer(report).data)

class PublicRealEstateReportView(APIView):
    """
    Endpoint for public access to real estate reports via slug.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        report = get_object_or_404(RealEstateReport, slug=slug)
        
        if report.status != "ACTIVE":
            # If not active, only super admin can see it
            from rest_framework_simplejwt.authentication import JWTAuthentication
            auth = JWTAuthentication().authenticate(request)
            if not auth or not PermissionService.is_super_admin(auth[0]):
                return Response({"error": "Report is not active or available."}, status=status.HTTP_403_FORBIDDEN)
        
        # Aggregate institutional performance data
        performance_data = RealEstateReportSelector.get_portfolio_performance_data(report.portfolio)
        
        data = RealEstateReportSerializer(report).data
        data["performance_data"] = performance_data
        
        return Response(data)
