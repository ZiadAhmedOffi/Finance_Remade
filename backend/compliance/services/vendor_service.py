from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from compliance.jobs.dispatcher import dispatch_job
from compliance.models import (
    ComplianceAuditEvent,
    ComplianceCase,
    ComplianceProfile,
    ComplianceState,
    MonitoringEvent,
    MonitoringEventType,
    ReviewTask,
    ReviewTaskType,
    ScreeningCheck,
    SyncStatus,
    TaskPriority,
    VendorCase,
    VendorName,
)
from compliance.selectors.compliance_selectors import get_cases_queryset, get_vendor_cases_queryset
from compliance.services.profile_service import ComplianceProfileService
from compliance.vendor.adapters import get_vendor_adapter

User = get_user_model()


class ComplianceVendorService:
    @staticmethod
    def _priority_from_risk_tier(risk_tier):
        return {
            "LOW": TaskPriority.LOW,
            "MEDIUM": TaskPriority.MEDIUM,
            "HIGH": TaskPriority.HIGH,
            "PROHIBITED": TaskPriority.CRITICAL,
        }.get(risk_tier, TaskPriority.MEDIUM)

    @staticmethod
    def _create_audit_event(event_type, *, actor=None, profile=None, case=None, metadata=None):
        return ComplianceAuditEvent.objects.create(
            event_type=event_type,
            actor=actor,
            profile=profile or (case.profile if case else None),
            case=case,
            metadata=metadata or {},
        )

    @classmethod
    def queue_case_submission(cls, *, case, actor=None):
        cls._create_audit_event(
            "VENDOR_CASE_SUBMISSION_QUEUED",
            actor=actor,
            case=case,
            metadata={"vendor_name": VendorName.PRIMARY},
        )
        return dispatch_job("submit_case_job", case_id=str(case.id), actor_id=str(actor.id) if actor else None)

    @classmethod
    @transaction.atomic
    def submit_case(cls, *, case_id, actor_id=None):
        case = get_cases_queryset().filter(id=case_id).first()
        if case is None:
            raise ValueError("Compliance case not found.")

        actor = User.objects.filter(id=actor_id).first() if actor_id else None
        adapter = get_vendor_adapter(VendorName.PRIMARY)
        normalized = adapter.start_case(case)

        vendor_case, created = VendorCase.objects.get_or_create(
            case=case,
            vendor_name=VendorName.PRIMARY,
            external_case_id=normalized.external_case_id,
            defaults={
                "sync_status": normalized.sync_status,
                "raw_payload": normalized.raw_payload,
                "last_synced_at": timezone.now(),
            },
        )
        if not created:
            vendor_case.sync_status = normalized.sync_status
            vendor_case.raw_payload = normalized.raw_payload
            vendor_case.last_synced_at = timezone.now()
            vendor_case.last_error = ""
            vendor_case.save(update_fields=["sync_status", "raw_payload", "last_synced_at", "last_error", "updated_at"])

        for result in normalized.screening_results:
            ScreeningCheck.objects.update_or_create(
                case=case,
                vendor_case=vendor_case,
                check_type=result.check_type,
                defaults={
                    "outcome": result.outcome,
                    "severity": result.severity,
                    "summary": result.summary,
                    "vendor_reference": result.vendor_reference,
                    "raw_payload": result.raw_payload,
                    "completed_at": timezone.now() if result.outcome in ["PASSED", "FAILED", "REVIEW"] else None,
                },
            )

        case.state = ComplianceState.WAITING_FOR_VENDOR
        if case.submitted_at is None:
            case.submitted_at = timezone.now()
        case.save(update_fields=["state", "submitted_at"])
        case.profile.current_state = ComplianceState.WAITING_FOR_VENDOR
        case.profile.save(update_fields=["current_state", "updated_at"])

        cls._create_audit_event(
            "VENDOR_CASE_SUBMITTED",
            actor=actor,
            case=case,
            metadata={
                "vendor_case_id": str(vendor_case.id),
                "external_case_id": vendor_case.external_case_id,
                "sync_status": vendor_case.sync_status,
            },
        )
        return vendor_case

    @classmethod
    def queue_vendor_sync(cls, *, vendor_case, actor=None, payload=None):
        cls._create_audit_event(
            "VENDOR_CASE_SYNC_QUEUED",
            actor=actor,
            case=vendor_case.case,
            metadata={
                "vendor_case_id": str(vendor_case.id),
                "vendor_name": vendor_case.vendor_name,
            },
        )
        return dispatch_job(
            "sync_vendor_case_job",
            vendor_case_id=str(vendor_case.id),
            payload=payload or {},
            actor_id=str(actor.id) if actor else None,
        )

    @classmethod
    @transaction.atomic
    def sync_vendor_case(cls, *, vendor_case_id, payload=None, actor_id=None):
        vendor_case = get_vendor_cases_queryset().filter(id=vendor_case_id).first()
        if vendor_case is None:
            raise ValueError("Vendor case not found.")

        actor = User.objects.filter(id=actor_id).first() if actor_id else None
        adapter = get_vendor_adapter(vendor_case.vendor_name)
        normalized = adapter.sync_case(vendor_case, raw_payload=payload or {})

        vendor_case.sync_status = normalized.sync_status
        vendor_case.raw_payload = normalized.raw_payload
        vendor_case.last_error = normalized.error_message
        vendor_case.last_synced_at = timezone.now()
        vendor_case.save(update_fields=["sync_status", "raw_payload", "last_error", "last_synced_at", "updated_at"])

        completed_at = timezone.now()
        for result in normalized.screening_results:
            ScreeningCheck.objects.update_or_create(
                case=vendor_case.case,
                vendor_case=vendor_case,
                check_type=result.check_type,
                defaults={
                    "outcome": result.outcome,
                    "severity": result.severity,
                    "summary": result.summary,
                    "vendor_reference": result.vendor_reference,
                    "raw_payload": result.raw_payload,
                    "completed_at": completed_at if result.outcome in ["PASSED", "FAILED", "REVIEW"] else None,
                },
            )

        if normalized.sync_status == SyncStatus.SYNCED:
            vendor_case.case.state = ComplianceState.IN_REVIEW
            vendor_case.case.save(update_fields=["state"])
            vendor_case.case.profile.current_state = ComplianceState.IN_REVIEW
            vendor_case.case.profile.save(update_fields=["current_state", "updated_at"])
            ReviewTask.objects.get_or_create(
                case=vendor_case.case,
                task_type=ReviewTaskType.INITIAL_REVIEW,
                status="OPEN",
                defaults={
                    "priority": cls._priority_from_risk_tier(vendor_case.case.risk_tier),
                    "reason": "Vendor checks completed and case is ready for analyst review.",
                },
            )
        elif normalized.sync_status == SyncStatus.FAILED:
            vendor_case.case.state = ComplianceState.WAITING_FOR_VENDOR
            vendor_case.case.save(update_fields=["state"])

        cls._create_audit_event(
            "VENDOR_CASE_SYNCED",
            actor=actor,
            case=vendor_case.case,
            metadata={
                "vendor_case_id": str(vendor_case.id),
                "sync_status": vendor_case.sync_status,
                "error_message": vendor_case.last_error,
                "screening_count": len(normalized.screening_results),
            },
        )
        return vendor_case

    @classmethod
    def process_vendor_webhook(cls, *, vendor_name, payload):
        adapter = get_vendor_adapter(vendor_name)
        normalized = adapter.normalize_webhook(payload)
        vendor_case = get_vendor_cases_queryset().filter(
            vendor_name=vendor_name,
            external_case_id=normalized.external_case_id,
        ).first()
        if vendor_case is None:
            raise ValueError("Vendor case not found for webhook payload.")
        return cls.sync_vendor_case(vendor_case_id=str(vendor_case.id), payload=payload)

    @classmethod
    @transaction.atomic
    def rescreen_profile(cls, *, profile_id, source="manual", metadata=None):
        profile = ComplianceProfile.objects.select_related("party").filter(id=profile_id).first()
        if profile is None:
            raise ValueError("Compliance profile not found.")

        latest_case = profile.cases.order_by("-opened_at").first()
        policy_version = latest_case.policy_version if latest_case else ComplianceProfileService.get_default_policy_version()

        case = ComplianceCase.objects.create(
            profile=profile,
            case_type="ONGOING_MONITORING",
            state=ComplianceState.DRAFT,
            risk_tier=profile.current_risk_tier,
            policy_version=policy_version,
            metadata={"source": source, **(metadata or {})},
        )
        MonitoringEvent.objects.create(
            profile=profile,
            case=case,
            event_type=MonitoringEventType.PERIODIC_REVIEW_DUE,
            source=source,
            metadata=metadata or {},
        )
        cls._create_audit_event(
            "PROFILE_RESCREEN_QUEUED",
            profile=profile,
            case=case,
            metadata={"source": source, **(metadata or {})},
        )
        return cls.queue_case_submission(case=case)
