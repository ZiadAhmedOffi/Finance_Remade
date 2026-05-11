from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .serializers import (
    RealEstatePortfolioSerializer, 
    RealEstateAssumptionsSerializer,
    PropertySerializer,
    PropertyWithMetricsSerializer,
    FinancingEntrySerializer,
    FinancingEntryWithMetricsSerializer,
    OffPlanDetailsSerializer,
    OffPlanMilestoneSerializer
)
from ..models import FinancingEntry, Property, OffPlanMilestone
from ..selectors.portfolio_selectors import PortfolioSelectors
from ..selectors.property_selectors import PropertySelector
from ..selectors.financing_selectors import FinancingSelectors
from ..selectors.off_plan_selectors import OffPlanSelectors
from ..services.portfolio_service import PortfolioService
from ..services.property_service import PropertyService
from ..services.financing_service import FinancingService
from ..services.off_plan_service import OffPlanService
from users.services.permission_service import PermissionService

class RealEstatePortfolioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RealEstatePortfolioSerializer

    def get_queryset(self):
        user = self.request.user
        if PermissionService.is_super_admin(user):
            return PortfolioSelectors.get_portfolios()
        
        # For non-superadmins, we should filter based on role assignments
        # This is a bit complex for a single query, so we'll just filter 
        # in the selector or here.
        portfolios = PortfolioSelectors.get_portfolios()
        return [p for p in portfolios if PermissionService.can_view_re_portfolio(user, p)]

    def perform_create(self, serializer):
        if not PermissionService.is_super_admin(self.request.user):
            raise PermissionDenied("Only superadmins can create portfolios.")
        
        PortfolioService.create_portfolio(
            actor=self.request.user,
            data=self.request.data
        )

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
            entries_with_metrics = FinancingSelectors.get_financing_entries_for_portfolio(portfolio)
            serializer = FinancingEntryWithMetricsSerializer(entries_with_metrics, many=True)
            return Response(serializer.data)
        
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

    @action(detail=True, methods=['get'], url_path='off-plan')
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

    @action(detail=True, methods=['get'], url_path='off-plan/(?P<property_id>[0-9a-f-]+)/schedule')
    def off_plan_schedule(self, request, pk=None, property_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_view_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to view this off-plan schedule.")

        try:
            property_obj = portfolio.properties.get(id=property_id, status="OFF_PLAN")
        except Property.DoesNotExist:
            return Response({"error": "Off-plan property not found."}, status=status.HTTP_404_NOT_FOUND)

        data = OffPlanSelectors.get_payment_schedule(property_obj)
        return Response(data)

    @action(detail=True, methods=['patch'], url_path='off-plan/milestones/(?P<milestone_id>[0-9a-f-]+)')
    def update_milestone(self, request, pk=None, milestone_id=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        if not PermissionService.can_edit_re_portfolio(request.user, portfolio):
            raise PermissionDenied("You do not have permission to edit milestones.")

        try:
            milestone = OffPlanMilestone.objects.get(id=milestone_id, property__portfolio=portfolio)
        except OffPlanMilestone.DoesNotExist:
            return Response({"error": "Milestone not found."}, status=status.HTTP_404_NOT_FOUND)

        updated_milestone = OffPlanService.update_milestone(milestone_id, request.data)
        serializer = OffPlanMilestoneSerializer(updated_milestone)
        return Response(serializer.data)
