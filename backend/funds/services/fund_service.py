from django.db import transaction
from funds.models import Fund, FundLog, ModelInput
from users.services.audit_service import AuditService
import json

class FundService:
    @staticmethod
    @transaction.atomic
    def create_fund(*, actor, data):
        """
        Creates a new fund and logs the action.
        """
        from funds.api.serializers import FundSerializer  # Local import to avoid circular dependency
        
        serializer = FundSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        fund = serializer.save(created_by=actor)
        
        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="FUND_CREATED"
        )
        
        AuditService.log(
            actor=actor,
            action="FUND_CREATED",
            fund=fund
        )
        
        return fund

    @staticmethod
    @transaction.atomic
    def update_fund(*, actor, fund, data):
        """
        Updates an existing fund, handles status changes, and logs the actions.
        """
        from funds.api.serializers import FundSerializer
        
        # Handle status change separately for logging
        new_status = data.get("status")
        if new_status and new_status != fund.status:
            old_status = fund.status
            fund.status = new_status
            fund.save()
            
            FundLog.objects.create(
                actor=actor,
                target_fund=fund,
                action="FUND_STATUS_UPDATED",
                metadata={"old": old_status, "new": new_status}
            )
            AuditService.log(
                actor=actor,
                action="FUND_STATUS_UPDATED",
                fund=fund,
                metadata={"old": old_status, "new": new_status}
            )

        # Handle other updates
        serializer = FundSerializer(fund, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        old_info = {"name": fund.name, "description": fund.description}
        serializer.save()
        new_info = {k: v for k, v in serializer.validated_data.items() if k in ["name", "description"]}
        
        if new_info:
            FundLog.objects.create(
                actor=actor,
                target_fund=fund,
                action="FUND_INFO_UPDATED",
                success=True,
                metadata={"old": old_info, "new": new_info}
            )
            AuditService.log(
                actor=actor,
                action="FUND_INFO_UPDATED",
                fund=fund
            )
            
        return fund

    @staticmethod
    @transaction.atomic
    def deactivate_fund(*, actor, fund):
        """
        Deactivates a fund.
        """
        old_status = fund.status
        fund.status = "DEACTIVATED"
        fund.save()
        
        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="FUND_STATUS_UPDATED",
            metadata={"old": old_status, "new": "DEACTIVATED"}
        )
        AuditService.log(
            actor=actor,
            action="FUND_STATUS_UPDATED",
            fund=fund,
            metadata={"old": old_status, "new": "DEACTIVATED"}
        )
        return fund

    @staticmethod
    @transaction.atomic
    def update_model_input(*, actor, fund, data):
        """
        Updates financial model inputs for a fund.
        """
        from funds.api.serializers import ModelInputSerializer
        
        model_inputs, _ = ModelInput.objects.get_or_create(fund=fund)
        old_data = ModelInputSerializer(model_inputs).data
        
        serializer = ModelInputSerializer(model_inputs, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Ensure metadata is JSON-safe
        metadata = json.loads(json.dumps(
            {"old": old_data, "new": serializer.data}, 
            default=str
        ))
        
        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="MODEL_INPUTS_UPDATED",
            metadata=metadata
        )
        AuditService.log(
            actor=actor,
            action="MODEL_INPUTS_UPDATED",
            fund=fund,
            metadata=metadata
        )
        
        return model_inputs
