from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .serializers import RealEstatePortfolioSerializer, RealEstateAssumptionsSerializer
from ..selectors.portfolio_selectors import PortfolioSelectors
from ..services.portfolio_service import PortfolioService

class RealEstatePortfolioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RealEstatePortfolioSerializer

    def get_queryset(self):
        return PortfolioSelectors.get_portfolios()

    def perform_create(self, serializer):
        PortfolioService.create_portfolio(
            actor=self.request.user,
            data=self.request.data
        )

    @action(detail=True, methods=['get', 'put', 'patch'], url_path='assumptions')
    def assumptions(self, request, pk=None):
        portfolio = PortfolioSelectors.get_portfolio_by_id(pk)
        
        if request.method == 'GET':
            serializer = RealEstateAssumptionsSerializer(portfolio.assumptions)
            return Response(serializer.data)
        
        elif request.method in ['PUT', 'PATCH']:
            assumptions = PortfolioService.update_assumptions(
                actor=request.user,
                portfolio=portfolio,
                data=request.data
            )
            serializer = RealEstateAssumptionsSerializer(assumptions)
            return Response(serializer.data)
