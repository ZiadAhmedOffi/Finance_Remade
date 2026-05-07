from django.db import transaction
from django.utils import timezone
from ..models import RealEstatePortfolio, RealEstateAssumptions
from users.services.audit_service import AuditService

class PortfolioService:
    @staticmethod
    @transaction.atomic
    def create_portfolio(*, actor, data):
        """
        Creates a new real estate portfolio and its default assumptions.
        """
        from ..api.serializers import RealEstatePortfolioSerializer
        
        serializer = RealEstatePortfolioSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        portfolio = serializer.save(created_by=actor)

        # Create default assumptions
        RealEstateAssumptions.objects.create(
            portfolio=portfolio,
            inception_date=timezone.now().date(),
            # Other fields use model defaults
        )

        AuditService.log(
            actor=actor,
            action="RE_PORTFOLIO_CREATED",
            metadata={"portfolio_id": str(portfolio.id), "name": portfolio.name}
        )

        return portfolio

    @staticmethod
    @transaction.atomic
    def update_assumptions(*, actor, portfolio, data):
        """
        Updates the assumptions for a portfolio.
        """
        assumptions = portfolio.assumptions
        from ..api.serializers import RealEstateAssumptionsSerializer
        
        serializer = RealEstateAssumptionsSerializer(assumptions, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        AuditService.log(
            actor=actor,
            action="RE_ASSUMPTIONS_UPDATED",
            metadata={"portfolio_id": str(portfolio.id)}
        )

        return assumptions
