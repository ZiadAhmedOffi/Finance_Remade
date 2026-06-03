from django.db import transaction
from ..models import RealEstateInvestorAction, RealEstatePortfolio, RealEstateInvestorStats
from ..selectors.portfolio_selectors import PortfolioSelectors
from ..selectors.investor_selectors import RealEstateInvestorSelector
from decimal import Decimal
from datetime import date

class RealEstateInvestorService:
    """
    Service for handling investor actions in a real estate portfolio.
    """

    @staticmethod
    @transaction.atomic
    def create_investor_action(actor, data):
        portfolio = data["portfolio"]
        action_type = data["type"]
        year = data["year"]
        amount = Decimal(str(data.get("amount", 0.0) or 0.0))
        investor = data["investor"]

        if action_type == "PRIMARY_INVESTMENT":
            # Use price per unit from the end of the previous year
            prev_year_date = date(year - 1, 12, 31)
            nav_metrics = PortfolioSelectors.get_portfolio_nav_metrics(portfolio, reference_date=prev_year_date)
            
            # Check if this is truly the first investment (no units exist yet)
            if portfolio.total_units == 0:
                units = amount # Initial price is 1.0
            else:
                price_per_unit = nav_metrics["price_per_unit"]
                units = amount / price_per_unit
            
            data["units"] = units
            action = RealEstateInvestorAction.objects.create(**data)
            
            portfolio.total_units = Decimal(str(portfolio.total_units)) + units
            portfolio.save(update_fields=["total_units"])

        elif action_type == "SECONDARY_EXIT":
            seller = data["investor"]
            buyer = data.get("investor_sold_to")
            pct_sold = Decimal(str(data["percentage_sold"]))
            
            seller_units = RealEstateInvestorSelector.calculate_investor_units(seller, portfolio)
            
            # Use units from previous year as the base for the percentage sold (consistent with funds)
            total_units_at_basis_year = PortfolioSelectors.get_total_units_at_year(portfolio, year - 1)
            if total_units_at_basis_year == 0:
                 total_units_at_basis_year = float(portfolio.total_units)
            
            units_transferred = (pct_sold / Decimal('100.0')) * Decimal(str(total_units_at_basis_year))
            
            if units_transferred > Decimal(str(seller_units)) + Decimal('0.0001'):
                 raise ValueError(f"Units to sell ({units_transferred:.4f}) exceed seller units ({seller_units:.4f}).")

            data["units"] = units_transferred
            action = RealEstateInvestorAction.objects.create(**data)
            
            if buyer:
                # Create a SECONDARY_INVESTMENT for the buyer
                RealEstateInvestorAction.objects.create(
                    investor=buyer,
                    portfolio=portfolio,
                    type="SECONDARY_INVESTMENT",
                    year=year,
                    amount=amount,
                    percentage_sold=pct_sold,
                    discount_percentage=data.get("discount_percentage", 0.0),
                    investor_selling=seller,
                    units=units_transferred
                )
        
        else: # SECONDARY_INVESTMENT or other
            action = RealEstateInvestorAction.objects.create(**data)

        # Bookkeeping Integration
        if action.type == "PRIMARY_INVESTMENT":
            from .ledger_sync_service import LedgerSyncService
            LedgerSyncService.sync_investor_investment(action)

        return action

    @staticmethod
    @transaction.atomic
    def update_investor_action(action, data):
        for attr, value in data.items():
            setattr(action, attr, value)
        action.save()
        return action

    @staticmethod
    @transaction.atomic
    def delete_investor_action(action):
        portfolio = action.portfolio
        units = Decimal(str(action.units))

        if action.type == "PRIMARY_INVESTMENT":
            portfolio.total_units = Decimal(str(portfolio.total_units)) - units
            portfolio.save(update_fields=["total_units"])
            
        action.delete()
        return True
