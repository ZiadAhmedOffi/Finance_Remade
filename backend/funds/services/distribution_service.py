from django.db import transaction
from funds.models import Distribution, FundLog, InvestorAction
from users.services.audit_service import AuditService
from funds.selectors import investor_selectors, fund_selectors
from decimal import Decimal

class DistributionService:
    @staticmethod
    @transaction.atomic
    def distribute_to_investors(*, actor, distribution):
        """
        Allocates a fund-level distribution to investors pro-rata.
        Creates InvestorAction entries (DIVIDEND_PAYOUT or DIVIDEND_REINVESTMENT).
        """
        fund = distribution.fund
        dist_date = distribution.date
        dist_year = dist_date.year
        dist_amount = Decimal(str(distribution.amount))
        
        # Get total fund units at distribution date
        total_fund_units = fund_selectors.get_total_units_at_year(fund, dist_year)
        if total_fund_units == 0:
            total_fund_units = float(fund.total_units)
            
        if total_fund_units == 0:
            return []

        # Get all investors in the fund
        from users.models import UserRoleAssignment
        investors = UserRoleAssignment.objects.filter(
            fund=fund, 
            role__name="INVESTOR"
        ).select_related('user')
        
        nav_metrics = None
        if fund.default_dividend_treatment == "REINVEST":
            # We need Price Per Unit for reinvestment
            nav_metrics = fund_selectors.get_fund_nav_metrics(fund, reference_date=dist_date)
        
        actions = []
        for assignment in investors:
            investor = assignment.user
            # Calculate investor units at dist_date
            investor_units = investor_selectors.calculate_investor_units(investor, fund, dist_year)
            if investor_units == 0:
                continue
                
            ownership_pct = Decimal(str(investor_units)) / Decimal(str(total_fund_units))
            investor_share = dist_amount * ownership_pct
            
            # Determine treatment
            treatment = assignment.dividend_treatment
            if treatment == "DEFAULT":
                treatment = fund.default_dividend_treatment
            
            if distribution.type == "EXIT_PROCEED":
                action_type = "EXIT_PAYOUT" if treatment == "CASH" else "EXIT_REINVESTMENT"
            else:
                action_type = "DIVIDEND_PAYOUT" if treatment == "CASH" else "DIVIDEND_REINVESTMENT"
            
            units_to_add = Decimal('0.0000')
            
            if action_type in ["DIVIDEND_REINVESTMENT", "EXIT_REINVESTMENT"]:
                if nav_metrics and nav_metrics["price_per_unit"] > 0:
                    units_to_add = investor_share / Decimal(str(nav_metrics["price_per_unit"]))
                else:
                    # Fallback if price is 0 (shouldn't happen for active fund)
                    units_to_add = Decimal('0.0000')

            action = InvestorAction.objects.create(
                investor=investor,
                fund=fund,
                type=action_type,
                year=dist_year,
                date=dist_date,
                amount=investor_share,
                units=units_to_add,
                distribution=distribution
            )
            actions.append(action)
            
        # Log the mass action
        AuditService.log(
            actor=actor,
            action="DISTRIBUTION_ALLOCATED",
            fund=fund,
            metadata={
                "distribution_id": str(distribution.id),
                "total_investors": len(actions),
                "total_amount": float(dist_amount)
            }
        )
        
        return actions

    @staticmethod
    @transaction.atomic
    def create_distribution(*, actor, fund, data):
        """
        Creates a new distribution and logs the action.
        """
        distribution = Distribution.objects.create(fund=fund, **data)
        
        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="DISTRIBUTION_CREATED",
            metadata={
                "distribution_id": str(distribution.id),
                "amount": float(distribution.amount),
                "type": distribution.type
            }
        )
        
        AuditService.log(
            actor=actor,
            action="DISTRIBUTION_CREATED",
            fund=fund,
            metadata={
                "distribution_id": str(distribution.id),
                "amount": float(distribution.amount),
                "type": distribution.type
            }
        )
        
        return distribution

    @staticmethod
    @transaction.atomic
    def update_distribution(*, actor, distribution, data):
        """
        Updates an existing distribution and logs the action.
        """
        old_data = {
            "amount": float(distribution.amount),
            "type": distribution.type,
            "date": str(distribution.date)
        }
        
        for attr, value in data.items():
            setattr(distribution, attr, value)
        distribution.save()
        
        new_data = {
            "amount": float(distribution.amount),
            "type": distribution.type,
            "date": str(distribution.date)
        }
        
        FundLog.objects.create(
            actor=actor,
            target_fund=distribution.fund,
            action="DISTRIBUTION_UPDATED",
            metadata={"old": old_data, "new": new_data}
        )
        
        AuditService.log(
            actor=actor,
            action="DISTRIBUTION_UPDATED",
            fund=distribution.fund,
            metadata={"old": old_data, "new": new_data}
        )
        
        return distribution

    @staticmethod
    @transaction.atomic
    def delete_distribution(*, actor, distribution):
        """
        Deletes a distribution and logs the action.
        Also cleans up any allocated investor actions.
        """
        fund = distribution.fund
        metadata = {
            "distribution_id": str(distribution.id),
            "amount": float(distribution.amount),
            "type": distribution.type,
            "allocated_actions_deleted": distribution.investor_actions.count()
        }
        
        # Clean up allocated actions
        distribution.investor_actions.all().delete()
        
        distribution.delete()
        
        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="DISTRIBUTION_DELETED",
            metadata=metadata
        )
        
        AuditService.log(
            actor=actor,
            action="DISTRIBUTION_DELETED",
            fund=fund,
            metadata=metadata
        )
        
        return True
