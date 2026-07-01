from django.db import transaction
from datetime import date
from compliance.services.gating_service import (
    can_commit_capital,
    can_receive_distribution,
    can_transfer_interest,
)
from funds.models import InvestorAction, Fund, CurrentInvestorStats, FundLog
from funds.selectors import fund_selectors
from funds.interfaces.user_interface import UserInterface
from users.services.audit_service import AuditService
from funds.selectors import investor_selectors

class InvestorService:
    def __init__(self, user_interface: UserInterface):
        self.user_interface = user_interface

    def _ensure_action_allowed(self, action_type, investor, buyer=None):
        if action_type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT", "DIVIDEND_REINVESTMENT", "EXIT_REINVESTMENT"]:
            decision = can_commit_capital(investor)
            if not decision.allowed:
                raise PermissionError(f"Compliance gate denied investor action: {decision.reason_code}")

        elif action_type in ["DIVIDEND_PAYOUT", "EXIT_PAYOUT"]:
            decision = can_receive_distribution(investor)
            if not decision.allowed:
                raise PermissionError(f"Compliance gate denied investor action: {decision.reason_code}")

        elif action_type == "SECONDARY_EXIT":
            seller_decision = can_transfer_interest(investor)
            if not seller_decision.allowed:
                raise PermissionError(f"Compliance gate denied transfer action: {seller_decision.reason_code}")
            if buyer is not None:
                buyer_decision = can_commit_capital(buyer)
                if not buyer_decision.allowed:
                    raise PermissionError(f"Compliance gate denied buyer action: {buyer_decision.reason_code}")

    @transaction.atomic
    def create_investor_action(self, actor, validated_data, ip_address):
        fund = validated_data["fund"]
        action_type = validated_data["type"]
        year = validated_data["year"]
        amount = float(validated_data.get("amount", 0.0) or 0.0)
        investor = validated_data["investor"]
        buyer = validated_data.get("investor_sold_to")

        self._ensure_action_allowed(action_type, investor, buyer=buyer)

        if action_type == "PRIMARY_INVESTMENT":
            is_first = not InvestorAction.objects.filter(fund=fund, type="PRIMARY_INVESTMENT").exists()
            if is_first:
                units = amount
            else:
                # Use NAV from the end of the previous year for pricing
                ref_date = date(year - 1, 12, 31)
                nav_metrics = fund_selectors.get_fund_nav_metrics(fund, reference_date=ref_date)
                price_per_unit = float(nav_metrics["price_per_unit"])
                
                if price_per_unit > 0:
                    units = amount / price_per_unit
                else:
                    units = amount
            
            validated_data["units"] = units
            action = InvestorAction.objects.create(**validated_data)

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

        target_investor = data.get("investor", action.investor)
        target_buyer = data.get("investor_sold_to", action.investor_sold_to)
        target_type = data.get("type", action.type)
        self._ensure_action_allowed(target_type, target_investor, buyer=target_buyer)
        
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
