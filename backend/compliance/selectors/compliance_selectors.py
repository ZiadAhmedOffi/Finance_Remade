from compliance.models import ComplianceCase, ComplianceProfile, ComplianceRestriction, EvidenceDocument, ReviewTask, VendorCase


def get_primary_profile_for_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return ComplianceProfile.objects.filter(user=user).select_related("party").first()


def get_active_restrictions_for_user(user):
    profile = get_primary_profile_for_user(user)
    if profile is None:
        return ComplianceRestriction.objects.none()
    return ComplianceRestriction.objects.filter(profile=profile, active=True)


def get_cases_for_user(user):
    profile = get_primary_profile_for_user(user)
    if profile is None:
        return ComplianceCase.objects.none()
    return (
        ComplianceCase.objects.filter(profile=profile)
        .select_related("policy_version", "profile", "profile__party")
        .order_by("-opened_at")
    )


def get_case_for_user(user, case_id):
    return get_cases_for_user(user).filter(id=case_id).first()


def get_profile_for_user(user, profile_id):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return (
        ComplianceProfile.objects.filter(user=user, id=profile_id)
        .select_related("party", "user")
        .first()
    )


def get_profiles_queryset():
    return ComplianceProfile.objects.select_related("party", "user").order_by("-created_at")


def get_cases_queryset():
    return (
        ComplianceCase.objects.select_related("policy_version", "profile", "profile__party", "profile__user")
        .prefetch_related("restrictions", "review_tasks", "screening_checks", "vendor_cases", "decisions")
        .order_by("-opened_at")
    )


def get_review_tasks_queryset():
    return (
        ReviewTask.objects.select_related("case", "case__profile", "case__profile__party", "assignee")
        .order_by("status", "sla_due_at", "-created_at")
    )


def get_restrictions_queryset():
    return (
        ComplianceRestriction.objects.select_related("profile", "profile__party", "case")
        .order_by("-started_at")
    )


def get_vendor_cases_queryset():
    return (
        VendorCase.objects.select_related("case", "case__profile", "case__profile__party")
        .prefetch_related("screening_checks")
        .order_by("-updated_at")
    )


def get_evidence_documents_queryset():
    return (
        EvidenceDocument.objects.select_related("case", "case__profile", "case__profile__party")
        .order_by("-created_at")
    )
