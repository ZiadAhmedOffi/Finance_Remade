from django.db import transaction
from funds.models import Distribution, FundLog
from users.services.audit_service import AuditService

class DistributionService:
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
        """
        fund = distribution.fund
        metadata = {
            "distribution_id": str(distribution.id),
            "amount": float(distribution.amount),
            "type": distribution.type
        }
        
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
