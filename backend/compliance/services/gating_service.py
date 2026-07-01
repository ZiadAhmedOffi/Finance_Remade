from dataclasses import dataclass, field

from compliance.models import ComplianceState, RestrictionType
from compliance.selectors.compliance_selectors import get_active_restrictions_for_user, get_primary_profile_for_user


@dataclass(frozen=True)
class ComplianceDecision:
    allowed: bool
    reason_code: str
    restriction_types: list[str] = field(default_factory=list)


def _blocked_decision(reason_code: str, restriction_types: list[str]) -> ComplianceDecision:
    return ComplianceDecision(allowed=False, reason_code=reason_code, restriction_types=restriction_types)


def _base_operability_decision(user) -> ComplianceDecision:
    profile = get_primary_profile_for_user(user)
    if profile is None:
        return _blocked_decision("NO_COMPLIANCE_PROFILE", [])

    if profile.current_state != ComplianceState.APPROVED or profile.operability_blocked:
        restriction_types = [restriction.restriction_type for restriction in get_active_restrictions_for_user(user)]
        return _blocked_decision("COMPLIANCE_NOT_APPROVED", restriction_types)

    return ComplianceDecision(allowed=True, reason_code="APPROVED")


def can_activate_investor(user) -> ComplianceDecision:
    return _base_operability_decision(user)


def can_assign_investor_role(user) -> ComplianceDecision:
    return _base_operability_decision(user)


def can_commit_capital(user) -> ComplianceDecision:
    decision = _base_operability_decision(user)
    if not decision.allowed:
        return decision
    return ComplianceDecision(allowed=True, reason_code="APPROVED")


def can_receive_distribution(user) -> ComplianceDecision:
    decision = _base_operability_decision(user)
    if not decision.allowed:
        return decision

    restriction_types = [restriction.restriction_type for restriction in get_active_restrictions_for_user(user)]
    if RestrictionType.DISTRIBUTIONS in restriction_types or RestrictionType.FULL_ACCOUNT_RESTRICTION in restriction_types:
        return _blocked_decision("DISTRIBUTION_RESTRICTED", restriction_types)

    return ComplianceDecision(allowed=True, reason_code="APPROVED")


def can_transfer_interest(user) -> ComplianceDecision:
    decision = _base_operability_decision(user)
    if not decision.allowed:
        return decision

    restriction_types = [restriction.restriction_type for restriction in get_active_restrictions_for_user(user)]
    if RestrictionType.TRANSFERS in restriction_types or RestrictionType.FULL_ACCOUNT_RESTRICTION in restriction_types:
        return _blocked_decision("TRANSFER_RESTRICTED", restriction_types)

    return ComplianceDecision(allowed=True, reason_code="APPROVED")

