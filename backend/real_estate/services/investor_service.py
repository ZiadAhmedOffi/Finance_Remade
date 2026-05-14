from django.db import transaction
from ..models import RealEstateInvestorAction, RealEstatePortfolio, RealEstateInvestorStats
from ..selectors.portfolio_selectors import PortfolioSelectors
from ..selectors.investor_selectors import RealEstateInvestorSelector
from decimal import Decimal

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
            nav_metrics = PortfolioSelectors.get_portfolio_nav_metrics(portfolio)
            if portfolio.total_units == 0:
                units = amount # Initial price is 1.0
            else:
                price_per_unit = nav_metrics["price_per_unit"]
                units = amount / price_per_unit
            
            data["units"] = units
            action = RealEstateInvestorAction.objects.create(**data)
            
            portfolio.total_units = Decimal(str(portfolio.total_units)) + units
            portfolio.save(update_fields=["total_units"])

            stats, _ = RealEstateInvestorStats.objects.get_or_create(investor=investor, portfolio=portfolio)
            stats.amount_invested = Decimal(str(stats.amount_invested)) + amount
            stats.capital_deployed = Decimal(str(stats.capital_deployed)) + amount
            stats.units = Decimal(str(stats.units)) + units
            stats.save()

        elif action_type == "SECONDARY_EXIT":
            seller = data["investor"]
            buyer = data.get("investor_sold_to")
            pct_sold = Decimal(str(data["percentage_sold"]))
            
            seller_units = RealEstateInvestorSelector.calculate_investor_units(seller, portfolio)
            
            # Use total units from previous year or current if year 0
            # For simplicity, using current total units as base for the percentage
            total_units_base = Decimal(str(portfolio.total_units))
            units_transferred = (pct_sold / Decimal('100.0')) * total_units_base
            
            if units_transferred > Decimal(str(seller_units)) + Decimal('0.0001'):
                 raise ValueError(f"Units to sell ({units_transferred:.4f}) exceed seller units ({seller_units:.4f}).")

            data["units"] = units_transferred
            action = RealEstateInvestorAction.objects.create(**data)
            price = amount
            
            # Update seller stats
            seller_stats, _ = RealEstateInvestorStats.objects.get_or_create(investor=seller, portfolio=portfolio)
            seller_stats.units = Decimal(str(seller_stats.units)) - units_transferred
            # realized_gain += (sale_price - cost_basis_of_units)
            # cost_basis_of_units = (total_amount_invested / total_units) * units_transferred
            if Decimal(str(seller_stats.units)) + units_transferred > 0:
                cost_basis_of_units = (Decimal(str(seller_stats.amount_invested)) / (Decimal(str(seller_stats.units)) + units_transferred)) * units_transferred
                seller_stats.amount_invested = Decimal(str(seller_stats.amount_invested)) - cost_basis_of_units
                seller_stats.realized_gain = Decimal(str(seller_stats.realized_gain)) + (price - cost_basis_of_units)
            
            seller_stats.save()

            if buyer:
                # Create a SECONDARY_INVESTMENT for the buyer
                RealEstateInvestorAction.objects.create(
                    investor=buyer,
                    portfolio=portfolio,
                    type="SECONDARY_INVESTMENT",
                    year=year,
                    amount=price,
                    percentage_sold=pct_sold,
                    discount_percentage=data.get("discount_percentage", 0.0),
                    investor_selling=seller,
                    units=units_transferred
                )
                # Update buyer stats
                buyer_stats, _ = RealEstateInvestorStats.objects.get_or_create(investor=buyer, portfolio=portfolio)
                buyer_stats.amount_invested = Decimal(str(buyer_stats.amount_invested)) + price
                buyer_stats.units = Decimal(str(buyer_stats.units)) + units_transferred
                buyer_stats.save()
        
        else: # SECONDARY_INVESTMENT or other
            action = RealEstateInvestorAction.objects.create(**data)

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
        investor = action.investor
        units = Decimal(str(action.units))
        amount = Decimal(str(action.amount or 0))

        if action.type == "PRIMARY_INVESTMENT":
            portfolio.total_units = Decimal(str(portfolio.total_units)) - units
            portfolio.save(update_fields=["total_units"])
            
            stats = RealEstateInvestorStats.objects.filter(investor=investor, portfolio=portfolio).first()
            if stats:
                stats.amount_invested = Decimal(str(stats.amount_invested)) - amount
                stats.capital_deployed = Decimal(str(stats.capital_deployed)) - amount
                stats.units = Decimal(str(stats.units)) - units
                stats.save()

        action.delete()
        return True
