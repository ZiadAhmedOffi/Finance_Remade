from django.db import transaction
from funds.models import InvestorAction, Fund, CurrentInvestorStats, FundLog
from funds.selectors import fund_selectors
from funds.interfaces.user_interface import UserInterface
from users.services.audit_service import AuditService
from funds.selectors import investor_selectors

class InvestorService:
    def __init__(self, user_interface: UserInterface):
        self.user_interface = user_interface

    @transaction.atomic
    def create_investor_action(self, actor, validated_data, ip_address):
        fund = validated_data["fund"]
        action_type = validated_data["type"]
        year = validated_data["year"]
        amount = float(validated_data.get("amount", 0.0) or 0.0)
        investor = validated_data["investor"]

        if action_type == "PRIMARY_INVESTMENT":
            is_first = not InvestorAction.objects.filter(fund=fund, type="PRIMARY_INVESTMENT").exists()
            if is_first:
                units = amount
            else:
                prev_year_portfolio = fund_selectors.get_total_fund_portfolio(fund, year - 1)
                prev_year_units = fund_selectors.get_total_units_at_year(fund, year - 1)
                if prev_year_units > 0 and prev_year_portfolio > 0:
                    units = amount / (prev_year_portfolio / prev_year_units)
                else:
                    units = amount
            
            validated_data["units"] = units
            action = InvestorAction.objects.create(**validated_data)
            
            fund.total_units = float(fund.total_units) + units
            fund.save(update_fields=["total_units"])

            stats, _ = CurrentInvestorStats.objects.get_or_create(investor=investor, fund=fund)
            stats.amount_invested = float(stats.amount_invested) + amount
            stats.total_units = float(stats.total_units) + units
            stats.save()

        elif action_type == "SECONDARY_EXIT":
            seller = validated_data["investor"] # investor field in SECONDARY_EXIT is the seller
            buyer = validated_data["investor_sold_to"]
            pct_sold = float(validated_data["percentage_sold"])
            discount = float(validated_data.get("discount_percentage", 0.0) or 0.0)
            
            seller_units = investor_selectors.calculate_investor_units(seller, fund)
            
            total_units_at_basis_year = fund_selectors.get_total_units_at_year(fund, year - 1)
            if total_units_at_basis_year == 0:
                 total_units_at_basis_year = float(fund.total_units)

            units_transferred = (pct_sold / 100.0) * total_units_at_basis_year
            
            if units_transferred > seller_units + 0.0001:
                 raise ValueError(f"Units to sell ({units_transferred:.4f}) exceed seller units ({seller_units:.4f}).")

            validated_data["units"] = units_transferred
            action = InvestorAction.objects.create(**validated_data)
            price = float(action.amount)
            
            # Update seller stats
            seller_stats, _ = CurrentInvestorStats.objects.get_or_create(investor=seller, fund=fund)
            seller_stats.total_units = float(seller_stats.total_units) - units_transferred
            # amount_invested reduction logic might depend on cost basis, but current views don't seem to reduce it here.
            # However, realized_gain should probably be updated.
            seller_stats.save()

            if buyer:
                # Create a SECONDARY_INVESTMENT for the buyer
                InvestorAction.objects.create(
                    investor=buyer,
                    fund=fund,
                    type="SECONDARY_INVESTMENT",
                    year=year,
                    amount=price,
                    percentage_sold=pct_sold,
                    discount_percentage=discount,
                    investor_selling=seller,
                    units=units_transferred
                )
                # Update buyer stats
                buyer_stats, _ = CurrentInvestorStats.objects.get_or_create(investor=buyer, fund=fund)
                buyer_stats.amount_invested = float(buyer_stats.amount_invested) + price
                buyer_stats.total_units = float(buyer_stats.total_units) + units_transferred
                buyer_stats.save()
        
        else:
            action = InvestorAction.objects.create(**validated_data)

        # Common Logging
        FundLog.objects.create(
            actor=actor,
            target_fund=action.fund,
            action="INVESTOR_ACTION_CREATED",
            metadata={"action_id": str(action.id), "type": action.type, "investor": action.investor.email}
        )
        AuditService.log(
            actor=actor,
            action="INVESTOR_ACTION_CREATED",
            fund=action.fund,
            target_user=action.investor,
            metadata={"action_id": str(action.id), "type": action.type},
            ip=ip_address
        )
        return action

    @transaction.atomic
    def update_investor_action(self, action_id, actor, data, ip_address):
        action = investor_selectors.get_investor_action_by_id(action_id)
        if not action:
            raise ValueError("Investor action not found")
        
        # NOTE: Updating an action might require complex unit recalculations if type/amount/units changed.
        # For now, following the simple update in views.py
        for attr, value in data.items():
            setattr(action, attr, value)
        action.save()

        FundLog.objects.create(
            actor=actor,
            target_fund=action.fund,
            action="INVESTOR_ACTION_UPDATED",
            metadata={"action_id": str(action.id), "type": action.type, "investor": action.investor.email}
        )
        AuditService.log(
            actor=actor,
            action="INVESTOR_ACTION_UPDATED",
            fund=action.fund,
            target_user=action.investor,
            metadata={"action_id": str(action.id), "type": action.type},
            ip=ip_address
        )
        return action

    @transaction.atomic
    def delete_investor_action(self, action_id, actor, ip_address):
        action = investor_selectors.get_investor_action_by_id(action_id)
        if not action:
            raise ValueError("Investor action not found")
        
        action_id_str = str(action.id)
        action_type = action.type
        investor_email = action.investor.email
        fund = action.fund
        target_user = action.investor
        units = float(action.units)
        
        if action.type == "PRIMARY_INVESTMENT":
            fund.total_units = float(fund.total_units) - units
            fund.save(update_fields=["total_units"])
            
            stats = CurrentInvestorStats.objects.filter(investor=target_user, fund=fund).first()
            if stats:
                stats.amount_invested = float(stats.amount_invested) - float(action.amount or 0)
                stats.total_units = float(stats.total_units) - units
                stats.save()

        action.delete()
        
        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="INVESTOR_ACTION_DELETED",
            metadata={"action_id": action_id_str, "type": action_type, "investor": investor_email}
        )
        AuditService.log(
            actor=actor,
            action="INVESTOR_ACTION_DELETED",
            fund=fund,
            target_user=target_user,
            metadata={"action_id": action_id_str, "type": action_type},
            ip=ip_address
        )
        return True
