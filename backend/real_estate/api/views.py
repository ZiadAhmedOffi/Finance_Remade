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
    PropertyWithMetricsSerializer
)
from ..selectors.portfolio_selectors import PortfolioSelectors
from ..selectors.property_selectors import PropertySelector
from ..services.portfolio_service import PortfolioService
from ..services.property_service import PropertyService
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
