from django.db import transaction

from compliance.models import ComplianceAuditEvent, RiskAssessment


class ComplianceRiskService:
    @staticmethod
    def _create_audit_event(event_type, *, actor=None, case=None, metadata=None):
        return ComplianceAuditEvent.objects.create(
            event_type=event_type,
            actor=actor,
            profile=case.profile if case else None,
            case=case,
            metadata=metadata or {},
        )

    @classmethod
    @transaction.atomic
    def record_risk_assessment(
        cls,
        *,
        case,
        actor,
        risk_tier,
        triggered_rules=None,
        score_snapshot=None,
    ):
        assessment = RiskAssessment.objects.create(
            case=case,
            policy_version=case.policy_version,
            risk_tier=risk_tier,
            triggered_rules=triggered_rules or [],
            score_snapshot=score_snapshot or {},
            assessed_by=actor,
        )

        case.risk_tier = risk_tier
        case.save(update_fields=["risk_tier"])

        profile = case.profile
        profile.current_risk_tier = risk_tier
        profile.save(update_fields=["current_risk_tier", "updated_at"])

        cls._create_audit_event(
            "RISK_ASSESSMENT_RECORDED",
            actor=actor,
            case=case,
            metadata={
                "risk_assessment_id": str(assessment.id),
                "risk_tier": assessment.risk_tier,
                "triggered_rules": assessment.triggered_rules,
            },
        )
        return assessment
