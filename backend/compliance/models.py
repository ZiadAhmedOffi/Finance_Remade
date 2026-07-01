import uuid

from django.conf import settings
from django.db import models


class PartyType(models.TextChoices):
    INDIVIDUAL = "INDIVIDUAL", "Individual"
    ENTITY = "ENTITY", "Entity"


class ComplianceCaseType(models.TextChoices):
    INDIVIDUAL_KYC = "INDIVIDUAL_KYC", "Individual KYC"
    ENTITY_KYB = "ENTITY_KYB", "Entity KYB"
    UBO_KYC = "UBO_KYC", "UBO KYC"
    CONTROLLER_KYC = "CONTROLLER_KYC", "Controller KYC"
    ONGOING_MONITORING = "ONGOING_MONITORING", "Ongoing Monitoring"


class ComplianceState(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    IN_REVIEW = "IN_REVIEW", "In Review"
    WAITING_FOR_APPLICANT = "WAITING_FOR_APPLICANT", "Waiting For Applicant"
    WAITING_FOR_VENDOR = "WAITING_FOR_VENDOR", "Waiting For Vendor"
    ESCALATED = "ESCALATED", "Escalated"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    RESTRICTED = "RESTRICTED", "Restricted"
    EXPIRED = "EXPIRED", "Expired"


class RiskTier(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    PROHIBITED = "PROHIBITED", "Prohibited"


class RelationshipType(models.TextChoices):
    BENEFICIAL_OWNER = "BENEFICIAL_OWNER", "Beneficial Owner"
    CONTROLLER = "CONTROLLER", "Controller"
    AUTHORIZED_SIGNER = "AUTHORIZED_SIGNER", "Authorized Signer"
    DIRECTOR = "DIRECTOR", "Director"


class VendorName(models.TextChoices):
    PRIMARY = "PRIMARY", "Primary Vendor"


class SyncStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    SYNCED = "SYNCED", "Synced"
    FAILED = "FAILED", "Failed"


class ScreeningCheckType(models.TextChoices):
    IDENTITY = "IDENTITY", "Identity"
    BUSINESS = "BUSINESS", "Business"
    SANCTIONS = "SANCTIONS", "Sanctions"
    PEP = "PEP", "PEP"
    ADVERSE_MEDIA = "ADVERSE_MEDIA", "Adverse Media"
    DOCUMENT = "DOCUMENT", "Document"


class ScreeningOutcome(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PASSED = "PASSED", "Passed"
    REVIEW = "REVIEW", "Review"
    FAILED = "FAILED", "Failed"


class MatchSeverity(models.TextChoices):
    INFO = "INFO", "Info"
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class ReviewTaskType(models.TextChoices):
    INITIAL_REVIEW = "INITIAL_REVIEW", "Initial Review"
    REQUEST_INFORMATION = "REQUEST_INFORMATION", "Request Information"
    ESCALATION_REVIEW = "ESCALATION_REVIEW", "Escalation Review"
    PERIODIC_REVIEW = "PERIODIC_REVIEW", "Periodic Review"
    ALERT_REVIEW = "ALERT_REVIEW", "Alert Review"


class ReviewTaskStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    BLOCKED = "BLOCKED", "Blocked"
    COMPLETED = "COMPLETED", "Completed"
    CANCELED = "CANCELED", "Canceled"


class TaskPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class DecisionType(models.TextChoices):
    APPROVE = "APPROVE", "Approve"
    REJECT = "REJECT", "Reject"
    RESTRICT = "RESTRICT", "Restrict"
    ESCALATE = "ESCALATE", "Escalate"
    REQUEST_INFORMATION = "REQUEST_INFORMATION", "Request Information"


class RestrictionType(models.TextChoices):
    INVESTOR_OPERABILITY = "INVESTOR_OPERABILITY", "Investor Operability"
    CAPITAL_ACTIVITY = "CAPITAL_ACTIVITY", "Capital Activity"
    DISTRIBUTIONS = "DISTRIBUTIONS", "Distributions"
    TRANSFERS = "TRANSFERS", "Transfers"
    FULL_ACCOUNT_RESTRICTION = "FULL_ACCOUNT_RESTRICTION", "Full Account Restriction"


class MonitoringEventType(models.TextChoices):
    PROFILE_CHANGE = "PROFILE_CHANGE", "Profile Change"
    OWNERSHIP_CHANGE = "OWNERSHIP_CHANGE", "Ownership Change"
    CAPITAL_ACTIVITY = "CAPITAL_ACTIVITY", "Capital Activity"
    TRANSFER_ACTIVITY = "TRANSFER_ACTIVITY", "Transfer Activity"
    VENDOR_ALERT = "VENDOR_ALERT", "Vendor Alert"
    DOCUMENT_EXPIRY = "DOCUMENT_EXPIRY", "Document Expiry"
    PERIODIC_REVIEW_DUE = "PERIODIC_REVIEW_DUE", "Periodic Review Due"


class PolicyVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_key = models.CharField(max_length=100, db_index=True)
    version = models.CharField(max_length=50)
    jurisdiction_scope = models.CharField(max_length=100)
    subject_scope = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("policy_key", "version")
        indexes = [
            models.Index(fields=["policy_key", "jurisdiction_scope"]),
        ]

    def __str__(self):
        return f"{self.policy_key}:{self.version}"


class ComplianceParty(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    party_type = models.CharField(max_length=20, choices=PartyType.choices, db_index=True)
    display_name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    jurisdiction = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    incorporation_date = models.DateField(null=True, blank=True)
    external_reference = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["party_type", "display_name"]),
            models.Index(fields=["country_code"]),
        ]

    def __str__(self):
        return self.display_name


class ComplianceProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    party = models.ForeignKey(ComplianceParty, on_delete=models.CASCADE, related_name="profiles")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_profiles",
    )
    current_state = models.CharField(max_length=30, choices=ComplianceState.choices, default=ComplianceState.DRAFT)
    current_risk_tier = models.CharField(max_length=20, choices=RiskTier.choices, default=RiskTier.MEDIUM)
    operability_blocked = models.BooleanField(default=True, db_index=True)
    is_legacy_subject = models.BooleanField(default=False, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["current_state", "operability_blocked"]),
            models.Index(fields=["is_legacy_subject"]),
        ]

    def __str__(self):
        return f"{self.party.display_name} profile"


class ComplianceCase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(ComplianceProfile, on_delete=models.CASCADE, related_name="cases")
    case_type = models.CharField(max_length=30, choices=ComplianceCaseType.choices, db_index=True)
    state = models.CharField(max_length=30, choices=ComplianceState.choices, default=ComplianceState.DRAFT, db_index=True)
    risk_tier = models.CharField(max_length=20, choices=RiskTier.choices, default=RiskTier.MEDIUM, db_index=True)
    policy_version = models.ForeignKey(PolicyVersion, on_delete=models.PROTECT, related_name="cases")
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["case_type", "state"]),
            models.Index(fields=["risk_tier", "state"]),
        ]


class PartyRelationship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_party = models.ForeignKey(ComplianceParty, on_delete=models.CASCADE, related_name="outgoing_relationships")
    to_party = models.ForeignKey(ComplianceParty, on_delete=models.CASCADE, related_name="incoming_relationships")
    relationship_type = models.CharField(max_length=30, choices=RelationshipType.choices, db_index=True)
    ownership_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    control_notes = models.TextField(blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["relationship_type"]),
        ]


class VendorCase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(ComplianceCase, on_delete=models.CASCADE, related_name="vendor_cases")
    vendor_name = models.CharField(max_length=20, choices=VendorName.choices, default=VendorName.PRIMARY)
    external_case_id = models.CharField(max_length=255, db_index=True)
    sync_status = models.CharField(max_length=20, choices=SyncStatus.choices, default=SyncStatus.PENDING, db_index=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("vendor_name", "external_case_id")


class ScreeningCheck(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(ComplianceCase, on_delete=models.CASCADE, related_name="screening_checks")
    vendor_case = models.ForeignKey(VendorCase, on_delete=models.SET_NULL, null=True, blank=True, related_name="screening_checks")
    check_type = models.CharField(max_length=30, choices=ScreeningCheckType.choices, db_index=True)
    outcome = models.CharField(max_length=20, choices=ScreeningOutcome.choices, default=ScreeningOutcome.PENDING, db_index=True)
    severity = models.CharField(max_length=20, choices=MatchSeverity.choices, default=MatchSeverity.INFO)
    vendor_reference = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["check_type", "outcome"]),
            models.Index(fields=["severity"]),
        ]


class EvidenceDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(ComplianceCase, on_delete=models.CASCADE, related_name="evidence_documents")
    document_type = models.CharField(max_length=100)
    storage_mode = models.CharField(max_length=30, default="VENDOR_REFERENCE")
    vendor_reference = models.CharField(max_length=255, blank=True)
    storage_reference = models.CharField(max_length=500, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["document_type"]),
            models.Index(fields=["expires_at"]),
        ]


class RiskAssessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(ComplianceCase, on_delete=models.CASCADE, related_name="risk_assessments")
    policy_version = models.ForeignKey(PolicyVersion, on_delete=models.PROTECT, related_name="risk_assessments")
    risk_tier = models.CharField(max_length=20, choices=RiskTier.choices, db_index=True)
    triggered_rules = models.JSONField(default=list, blank=True)
    score_snapshot = models.JSONField(default=dict, blank=True)
    assessed_at = models.DateTimeField(auto_now_add=True)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_risk_assessments",
    )


class ReviewTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(ComplianceCase, on_delete=models.CASCADE, related_name="review_tasks")
    task_type = models.CharField(max_length=30, choices=ReviewTaskType.choices, db_index=True)
    status = models.CharField(max_length=20, choices=ReviewTaskStatus.choices, default=ReviewTaskStatus.OPEN, db_index=True)
    priority = models.CharField(max_length=20, choices=TaskPriority.choices, default=TaskPriority.MEDIUM, db_index=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_review_tasks",
    )
    sla_due_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["sla_due_at"]),
        ]


class CaseDecision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(ComplianceCase, on_delete=models.CASCADE, related_name="decisions")
    decision_type = models.CharField(max_length=30, choices=DecisionType.choices, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="compliance_case_decisions",
    )
    policy_version = models.ForeignKey(PolicyVersion, on_delete=models.PROTECT, related_name="case_decisions")
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["decision_type", "created_at"]),
        ]


class ComplianceRestriction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(ComplianceProfile, on_delete=models.CASCADE, related_name="restrictions")
    case = models.ForeignKey(ComplianceCase, on_delete=models.SET_NULL, null=True, blank=True, related_name="restrictions")
    restriction_type = models.CharField(max_length=40, choices=RestrictionType.choices, db_index=True)
    reason_code = models.CharField(max_length=100, db_index=True)
    active = models.BooleanField(default=True, db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    lifted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["active", "restriction_type"]),
        ]


class MonitoringEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(ComplianceProfile, on_delete=models.CASCADE, related_name="monitoring_events")
    case = models.ForeignKey(ComplianceCase, on_delete=models.SET_NULL, null=True, blank=True, related_name="monitoring_events")
    event_type = models.CharField(max_length=40, choices=MonitoringEventType.choices, db_index=True)
    source = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict, blank=True)
    triggered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["event_type", "processed_at"]),
        ]


class ComplianceAuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_audit_events",
    )
    profile = models.ForeignKey(ComplianceProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")
    case = models.ForeignKey(ComplianceCase, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
        ]

