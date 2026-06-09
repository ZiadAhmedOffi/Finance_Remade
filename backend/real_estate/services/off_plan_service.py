from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from ..models import Property, OffPlanDetails, OffPlanMilestone

class OffPlanService:
    @staticmethod
    @transaction.atomic
    def ensure_off_plan_details(property_obj: Property) -> OffPlanDetails:
        """
        Ensures a property has OffPlanDetails and default milestones if it's OFF_PLAN.
        """
        if property_obj.status != "OFF_PLAN":
            return None
            
        details, created = OffPlanDetails.objects.get_or_create(
            property=property_obj,
            defaults={
                "construction_start_date": property_obj.purchase_date,
                "expected_completion_date": property_obj.purchase_date + timedelta(days=365*2),
                "appreciation_rate_at_completion": Decimal("25.00")
            }
        )
        
        if created:
            # Create default milestones
            OffPlanService.create_default_milestones(property_obj)
            
        return details

    @staticmethod
    @transaction.atomic
    def create_default_milestones(property_obj: Property):
        """
        Creates standard milestones for an off-plan property.
        """
        # Delete existing ones to avoid duplicates if reset
        property_obj.milestones.all().delete()
        
        start_date = property_obj.purchase_date
        completion_date = start_date + timedelta(days=365*2)
        
        milestones = [
            ("Down Payment", start_date, Decimal("20.00")),
            ("Construction at 30%", start_date + timedelta(days=180), Decimal("10.00")),
            ("Handover 50%", start_date + timedelta(days=365), Decimal("20.00")),
            ("Finishing", start_date + timedelta(days=540), Decimal("10.00")),
        ]
        
        for name, date, pct in milestones:
            OffPlanMilestone.objects.create(
                property=property_obj,
                milestone_name=name,
                date=date,
                percentage_of_price=pct
            )
        
        # Sync with Ledger
        from .ledger_sync_service import LedgerSyncService
        LedgerSyncService.sync_off_plan_creation(property_obj)

    @staticmethod
    @transaction.atomic
    def update_off_plan_details(property_obj: Property, data: dict) -> OffPlanDetails:
        """
        Updates Off-Plan details.
        """
        details = OffPlanService.ensure_off_plan_details(property_obj)
        if not details:
            return None
            
        from django.utils.dateparse import parse_date
        if "construction_start_date" in data:
            csd = data["construction_start_date"]
            details.construction_start_date = parse_date(csd) if isinstance(csd, str) else csd
        if "expected_completion_date" in data:
            ecd = data["expected_completion_date"]
            details.expected_completion_date = parse_date(ecd) if isinstance(ecd, str) else ecd
        if "appreciation_rate_at_completion" in data:
            details.appreciation_rate_at_completion = Decimal(str(data["appreciation_rate_at_completion"]))
        if "sale_at_completion" in data:
            details.sale_at_completion = data["sale_at_completion"]
            
        details.save()

        # Sync with Ledger
        from .ledger_sync_service import LedgerSyncService
        LedgerSyncService.sync_off_plan_creation(property_obj)
        
        return details

    @staticmethod
    @transaction.atomic
    def create_milestone(property_obj: Property, data: dict) -> OffPlanMilestone:
        """
        Creates a new milestone for an off-plan property.
        """
        from django.utils.dateparse import parse_date
        m_date = data.get('date', timezone.now().date())
        if isinstance(m_date, str):
            m_date = parse_date(m_date)

        milestone = OffPlanMilestone.objects.create(
            property=property_obj,
            milestone_name=data.get('milestone_name', 'New Milestone'),
            date=m_date,
            percentage_of_price=Decimal(str(data.get('percentage_of_price', '0.00')))
        )

        # Sync with Ledger
        from .ledger_sync_service import LedgerSyncService
        LedgerSyncService.sync_off_plan_creation(property_obj)

        return milestone

    @staticmethod
    @transaction.atomic
    def update_milestone(milestone_id: str, data: dict) -> OffPlanMilestone:
        """
        Updates a specific milestone.
        """
        milestone = OffPlanMilestone.objects.get(id=milestone_id)
        if "date" in data:
            from django.utils.dateparse import parse_date
            m_date = data["date"]
            milestone.date = parse_date(m_date) if isinstance(m_date, str) else m_date
        if "percentage_of_price" in data:
            milestone.percentage_of_price = Decimal(str(data["percentage_of_price"]))
        if "milestone_name" in data:
            milestone.milestone_name = data["milestone_name"]
            
        milestone.save()

        # Sync with Ledger
        from .ledger_sync_service import LedgerSyncService
        LedgerSyncService.sync_off_plan_creation(milestone.property)

        return milestone

    @staticmethod
    @transaction.atomic
    def delete_milestone(milestone_id: str):
        """
        Deletes a milestone.
        """
        milestone = OffPlanMilestone.objects.filter(id=milestone_id).first()
        if milestone:
            property_obj = milestone.property
            milestone.delete()
            # Sync with Ledger
            from .ledger_sync_service import LedgerSyncService
            LedgerSyncService.sync_off_plan_creation(property_obj)

