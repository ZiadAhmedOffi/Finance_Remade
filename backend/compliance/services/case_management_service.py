from django.db import transaction
from django.utils import timezone

from compliance.models import (
    CaseDecision,
    ComplianceAuditEvent,
    ComplianceRestriction,
    ComplianceState,
    DecisionType,
    ReviewTask,
    TaskPriority,
    ReviewTaskType,
    ReviewTaskStatus,
)
from users.services.permission_service import PermissionService


class ComplianceCaseManagementService:
    @staticmethod
    def _create_audit_event(event_type, *, actor, case, metadata=None):
        return ComplianceAuditEvent.objects.create(
            event_type=event_type,
            actor=actor,
            profile=case.profile,
            case=case,
            metadata=metadata or {},
        )

    @staticmethod
    def _create_case_decision(case, *, actor, decision_type, notes="", metadata=None):
        return CaseDecision.objects.create(
            case=case,
            decision_type=decision_type,
            actor=actor,
            policy_version=case.policy_version,
            notes=notes,
            metadata=metadata or {},
        )

    @staticmethod
    def _mark_open_tasks(case, *, status, notes_suffix=""):
        now = timezone.now()
        open_tasks = case.review_tasks.exclude(status__in=[ReviewTaskStatus.COMPLETED, ReviewTaskStatus.CANCELED])
        for task in open_tasks:
            task.status = status
            if status in [ReviewTaskStatus.COMPLETED, ReviewTaskStatus.CANCELED]:
                task.completed_at = now
            if notes_suffix:
                task.notes = f"{task.notes}\n{notes_suffix}".strip()
            task.save(update_fields=["status", "completed_at", "notes"])

    @staticmethod
    def _has_manager_authority(actor):
        return PermissionService.is_super_admin(actor) or PermissionService.is_access_manager(actor)

    @classmethod
    @transaction.atomic
    def assign_review_task(
        cls,
        *,
        case,
        actor,
        assignee=None,
        task_type,
        priority,
        reason="",
        notes="",
        sla_due_at=None,
    ):
        task = ReviewTask.objects.create(
            case=case,
            assignee=assignee,
            task_type=task_type,
            priority=priority,
            reason=reason,
            notes=notes,
            sla_due_at=sla_due_at,
        )

        if case.state in [ComplianceState.DRAFT, ComplianceState.SUBMITTED, ComplianceState.WAITING_FOR_APPLICANT]:
            case.state = ComplianceState.IN_REVIEW
            case.save(update_fields=["state"])
            case.profile.current_state = ComplianceState.IN_REVIEW
            case.profile.save(update_fields=["current_state", "updated_at"])

        cls._create_audit_event(
            "REVIEW_TASK_ASSIGNED",
            actor=actor,
            case=case,
            metadata={
                "task_id": str(task.id),
                "task_type": task.task_type,
                "priority": task.priority,
                "assignee_id": str(assignee.id) if assignee else None,
            },
        )
        return task

    @classmethod
    @transaction.atomic
    def request_information(cls, *, case, actor, notes="", metadata=None):
        cls._create_case_decision(
            case,
            actor=actor,
            decision_type=DecisionType.REQUEST_INFORMATION,
            notes=notes,
            metadata=metadata,
        )

        case.state = ComplianceState.WAITING_FOR_APPLICANT
        case.save(update_fields=["state"])
        case.profile.current_state = ComplianceState.WAITING_FOR_APPLICANT
        case.profile.operability_blocked = True
        case.profile.save(update_fields=["current_state", "operability_blocked", "updated_at"])

        cls._mark_open_tasks(
            case,
            status=ReviewTaskStatus.BLOCKED,
            notes_suffix="Blocked pending applicant response.",
        )

        task = ReviewTask.objects.create(
            case=case,
            task_type=ReviewTaskType.REQUEST_INFORMATION,
            status=ReviewTaskStatus.OPEN,
            priority=(
                case.profile.current_risk_tier
                if case.profile.current_risk_tier in [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH]
                else TaskPriority.MEDIUM
            ),
            reason="Additional applicant information required.",
            notes=notes,
        )

        cls._create_audit_event(
            "CASE_INFORMATION_REQUESTED",
            actor=actor,
            case=case,
            metadata={
                "decision_type": DecisionType.REQUEST_INFORMATION,
                "task_id": str(task.id),
                **(metadata or {}),
            },
        )
        return case

    @classmethod
    @transaction.atomic
    def approve_case(cls, *, case, actor, notes="", metadata=None):
        if not cls._has_manager_authority(actor):
            raise PermissionError("Manager authority is required to approve compliance cases.")

        cls._create_case_decision(
            case,
            actor=actor,
            decision_type=DecisionType.APPROVE,
            notes=notes,
            metadata=metadata,
        )

        now = timezone.now()
        case.state = ComplianceState.APPROVED
        case.closed_at = now
        case.save(update_fields=["state", "closed_at"])

        profile = case.profile
        profile.current_state = ComplianceState.APPROVED
        profile.current_risk_tier = case.risk_tier
        profile.operability_blocked = False
        profile.save(update_fields=["current_state", "current_risk_tier", "operability_blocked", "updated_at"])

        cls._mark_open_tasks(case, status=ReviewTaskStatus.COMPLETED, notes_suffix="Closed by approval decision.")
        cls._create_audit_event(
            "CASE_APPROVED",
            actor=actor,
            case=case,
            metadata={"decision_type": DecisionType.APPROVE, **(metadata or {})},
        )
        return case

    @classmethod
    @transaction.atomic
    def reject_case(cls, *, case, actor, notes="", metadata=None):
        if not cls._has_manager_authority(actor):
            raise PermissionError("Manager authority is required to reject compliance cases.")

        cls._create_case_decision(
            case,
            actor=actor,
            decision_type=DecisionType.REJECT,
            notes=notes,
            metadata=metadata,
        )

        now = timezone.now()
        case.state = ComplianceState.REJECTED
        case.closed_at = now
        case.save(update_fields=["state", "closed_at"])

        profile = case.profile
        profile.current_state = ComplianceState.REJECTED
        profile.current_risk_tier = case.risk_tier
        profile.operability_blocked = True
        profile.save(update_fields=["current_state", "current_risk_tier", "operability_blocked", "updated_at"])

        cls._mark_open_tasks(case, status=ReviewTaskStatus.CANCELED, notes_suffix="Closed by rejection decision.")
        cls._create_audit_event(
            "CASE_REJECTED",
            actor=actor,
            case=case,
            metadata={"decision_type": DecisionType.REJECT, **(metadata or {})},
        )
        return case

    @classmethod
    @transaction.atomic
    def restrict_case(
        cls,
        *,
        case,
        actor,
        restriction_type,
        reason_code,
        notes="",
        metadata=None,
    ):
        if not cls._has_manager_authority(actor):
            raise PermissionError("Manager authority is required to restrict compliance cases.")

        cls._create_case_decision(
            case,
            actor=actor,
            decision_type=DecisionType.RESTRICT,
            notes=notes,
            metadata={
                "restriction_type": restriction_type,
                "reason_code": reason_code,
                **(metadata or {}),
            },
        )

        restriction = ComplianceRestriction.objects.create(
            profile=case.profile,
            case=case,
            restriction_type=restriction_type,
            reason_code=reason_code,
            metadata={
                "notes": notes,
                "previous_case_state": case.state,
                "previous_profile_state": case.profile.current_state,
                **(metadata or {}),
            },
        )

        case.state = ComplianceState.RESTRICTED
        case.save(update_fields=["state"])

        profile = case.profile
        profile.current_state = ComplianceState.RESTRICTED
        profile.operability_blocked = True
        profile.save(update_fields=["current_state", "operability_blocked", "updated_at"])

        cls._mark_open_tasks(case, status=ReviewTaskStatus.BLOCKED, notes_suffix="Case restricted pending resolution.")
        cls._create_audit_event(
            "CASE_RESTRICTED",
            actor=actor,
            case=case,
            metadata={
                "decision_type": DecisionType.RESTRICT,
                "restriction_id": str(restriction.id),
                "restriction_type": restriction.restriction_type,
                "reason_code": restriction.reason_code,
                **(metadata or {}),
            },
        )
        return restriction

    @classmethod
    @transaction.atomic
    def lift_restriction(cls, *, restriction, actor, notes="", metadata=None):
        if not cls._has_manager_authority(actor):
            raise PermissionError("Manager authority is required to lift compliance restrictions.")
        if not restriction.active:
            return restriction

        restriction.active = False
        restriction.lifted_at = timezone.now()
        restriction.metadata = {
            **restriction.metadata,
            "lift_notes": notes,
            "lift_metadata": metadata or {},
        }
        restriction.save(update_fields=["active", "lifted_at", "metadata"])

        profile = restriction.profile
        remaining_active = ComplianceRestriction.objects.filter(profile=profile, active=True).exists()
        if not remaining_active:
            previous_profile_state = restriction.metadata.get("previous_profile_state")
            restored_profile_state = (
                previous_profile_state
                if previous_profile_state in ComplianceState.values
                else ComplianceState.IN_REVIEW
            )
            profile.current_state = restored_profile_state
            profile.operability_blocked = restored_profile_state != ComplianceState.APPROVED
            profile.save(update_fields=["current_state", "operability_blocked", "updated_at"])

            if restriction.case and restriction.case.state == ComplianceState.RESTRICTED:
                previous_case_state = restriction.metadata.get("previous_case_state")
                restriction.case.state = (
                    previous_case_state
                    if previous_case_state in ComplianceState.values
                    else ComplianceState.IN_REVIEW
                )
                restriction.case.save(update_fields=["state"])

        case = restriction.case or profile.cases.order_by("-opened_at").first()
        if case is not None:
            cls._create_audit_event(
                "RESTRICTION_LIFTED",
                actor=actor,
                case=case,
                metadata={
                    "restriction_id": str(restriction.id),
                    "restriction_type": restriction.restriction_type,
                    "reason_code": restriction.reason_code,
                    **(metadata or {}),
                },
            )
        return restriction
