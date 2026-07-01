from rest_framework import serializers

from compliance.models import (
    CaseDecision,
    ComplianceCase,
    ComplianceParty,
    ComplianceProfile,
    ComplianceRestriction,
    EvidenceDocument,
    RiskAssessment,
    RestrictionType,
    PartyRelationship,
    PolicyVersion,
    RelationshipType,
    RiskTier,
    ReviewTaskType,
    TaskPriority,
    ReviewTask,
    VendorCase,
)


class CompliancePartySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceParty
        fields = [
            "id",
            "party_type",
            "display_name",
            "legal_name",
            "first_name",
            "last_name",
            "email",
            "country_code",
            "jurisdiction",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CompliancePartyCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    jurisdiction = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=2, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class PolicyVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyVersion
        fields = [
            "id",
            "policy_key",
            "version",
            "jurisdiction_scope",
            "subject_scope",
            "effective_from",
            "effective_to",
        ]
        read_only_fields = fields


class ComplianceRestrictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceRestriction
        fields = [
            "id",
            "restriction_type",
            "reason_code",
            "active",
            "started_at",
            "lifted_at",
            "metadata",
        ]
        read_only_fields = fields


class CaseDecisionSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = CaseDecision
        fields = [
            "id",
            "decision_type",
            "actor",
            "actor_email",
            "policy_version",
            "notes",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class VendorCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorCase
        fields = [
            "id",
            "vendor_name",
            "external_case_id",
            "sync_status",
            "last_synced_at",
            "last_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class EvidenceDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceDocument
        fields = [
            "id",
            "document_type",
            "storage_mode",
            "vendor_reference",
            "storage_reference",
            "expires_at",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class RiskAssessmentSerializer(serializers.ModelSerializer):
    assessed_by_email = serializers.EmailField(source="assessed_by.email", read_only=True)

    class Meta:
        model = RiskAssessment
        fields = [
            "id",
            "risk_tier",
            "triggered_rules",
            "score_snapshot",
            "assessed_at",
            "assessed_by",
            "assessed_by_email",
        ]
        read_only_fields = fields


class ComplianceProfileSerializer(serializers.ModelSerializer):
    party = CompliancePartySerializer(read_only=True)

    class Meta:
        model = ComplianceProfile
        fields = [
            "id",
            "party",
            "current_state",
            "current_risk_tier",
            "operability_blocked",
            "is_legacy_subject",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class EntityComplianceProfileCreateSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=255)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    jurisdiction = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=2, required=False, allow_blank=True)
    incorporation_date = serializers.DateField(required=False, allow_null=True)
    external_reference = serializers.CharField(max_length=255, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class PartyRelationshipSerializer(serializers.ModelSerializer):
    from_party = CompliancePartySerializer(read_only=True)
    to_party = CompliancePartySerializer(read_only=True)

    class Meta:
        model = PartyRelationship
        fields = [
            "id",
            "from_party",
            "to_party",
            "relationship_type",
            "ownership_percentage",
            "control_notes",
            "effective_from",
            "effective_to",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class EntityRelationshipCreateSerializer(serializers.Serializer):
    relationship_type = serializers.ChoiceField(choices=RelationshipType.choices)
    ownership_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    control_notes = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)
    party = CompliancePartyCreateSerializer()


class ComplianceCaseSerializer(serializers.ModelSerializer):
    policy_version = PolicyVersionSerializer(read_only=True)

    class Meta:
        model = ComplianceCase
        fields = [
            "id",
            "case_type",
            "state",
            "risk_tier",
            "policy_version",
            "opened_at",
            "closed_at",
            "submitted_at",
        ]
        read_only_fields = fields


class ComplianceCaseDetailSerializer(ComplianceCaseSerializer):
    profile = ComplianceProfileSerializer(read_only=True)
    restrictions = ComplianceRestrictionSerializer(many=True, read_only=True)
    vendor_cases = VendorCaseSerializer(many=True, read_only=True)
    decisions = CaseDecisionSerializer(many=True, read_only=True)
    review_tasks = serializers.SerializerMethodField()
    evidence_documents = EvidenceDocumentSerializer(many=True, read_only=True)
    risk_assessments = RiskAssessmentSerializer(many=True, read_only=True)

    class Meta(ComplianceCaseSerializer.Meta):
        fields = ComplianceCaseSerializer.Meta.fields + [
            "profile",
            "metadata",
            "restrictions",
            "vendor_cases",
            "decisions",
            "review_tasks",
            "evidence_documents",
            "risk_assessments",
        ]

    def get_review_tasks(self, obj):
        return ReviewTaskSerializer(obj.review_tasks.order_by("-created_at"), many=True).data


class ReviewTaskSerializer(serializers.ModelSerializer):
    case = ComplianceCaseSerializer(read_only=True)
    assignee_email = serializers.EmailField(source="assignee.email", read_only=True)

    class Meta:
        model = ReviewTask
        fields = [
            "id",
            "case",
            "task_type",
            "status",
            "priority",
            "assignee",
            "assignee_email",
            "sla_due_at",
            "reason",
            "notes",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields


class ReviewTaskAssignmentSerializer(serializers.Serializer):
    assignee_id = serializers.UUIDField(required=False, allow_null=True)
    task_type = serializers.ChoiceField(choices=ReviewTaskType.choices)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, required=False, default=TaskPriority.MEDIUM)
    reason = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    sla_due_at = serializers.DateTimeField(required=False, allow_null=True)


class ComplianceCaseMutationSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class RestrictionCreateSerializer(ComplianceCaseMutationSerializer):
    restriction_type = serializers.ChoiceField(choices=RestrictionType.choices)
    reason_code = serializers.CharField(max_length=100)


class VendorSyncSerializer(serializers.Serializer):
    payload = serializers.JSONField(required=False)


class ComplianceRescreenSerializer(serializers.Serializer):
    source = serializers.CharField(required=False, allow_blank=True, default="manual")
    metadata = serializers.JSONField(required=False)


class EvidenceDocumentCreateSerializer(serializers.Serializer):
    document_type = serializers.CharField(max_length=100)
    storage_mode = serializers.CharField(max_length=30, required=False, default="VENDOR_REFERENCE")
    vendor_reference = serializers.CharField(max_length=255, required=False, allow_blank=True)
    storage_reference = serializers.CharField(max_length=500, required=False, allow_blank=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False)


class RiskAssessmentCreateSerializer(serializers.Serializer):
    risk_tier = serializers.ChoiceField(choices=RiskTier.choices)
    triggered_rules = serializers.ListField(child=serializers.CharField(), required=False)
    score_snapshot = serializers.JSONField(required=False)
