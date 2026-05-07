from ..models import RealEstatePortfolio

class PortfolioSelectors:
    @staticmethod
    def get_portfolios():
        """
        Returns all active real estate portfolios.
        """
        return RealEstatePortfolio.objects.filter(status="ACTIVE").select_related('assumptions', 'created_by')

    @staticmethod
    def get_portfolio_by_id(portfolio_id):
        """
        Returns a single portfolio by ID.
        """
        return RealEstatePortfolio.objects.select_related('assumptions', 'created_by').get(id=portfolio_id)
