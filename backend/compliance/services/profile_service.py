from datetime import datetime, timezone as dt_timezone

from compliance.models import (
    ComplianceCase,
    ComplianceCaseType,
    ComplianceParty,
    ComplianceProfile,
    ComplianceState,
    PartyRelationship,
    PartyType,
    PolicyVersion,
    RelationshipType,
    RiskTier,
)


class ComplianceProfileService:
    DEFAULT_POLICY_KEY = "PHASE1_DEFAULT"
    DEFAULT_POLICY_VERSION = "v1"

    @classmethod
    def get_default_policy_version(cls):
        policy_version, _ = PolicyVersion.objects.get_or_create(
            policy_key=cls.DEFAULT_POLICY_KEY,
            version=cls.DEFAULT_POLICY_VERSION,
            defaults={
                "jurisdiction_scope": "MENA_US",
                "subject_scope": "INDIVIDUAL_AND_ENTITY",
                "description": "Initial scaffold policy version for Phase 1 compliance onboarding.",
                "effective_from": datetime(2026, 1, 1, tzinfo=dt_timezone.utc),
            },
        )
        return policy_version

    @classmethod
    def ensure_individual_profile_for_user(cls, user, *, create_case=False):
        display_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip() or user.email
        party, _ = ComplianceParty.objects.get_or_create(
            email=user.email,
            party_type=PartyType.INDIVIDUAL,
            defaults={
                "display_name": display_name,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "country_code": "",
                "jurisdiction": "",
                "metadata": {
                    "company": user.company,
                    "job_title": user.job_title,
                    "phone_number": user.phone_number,
                },
            },
        )

        profile, _ = ComplianceProfile.objects.get_or_create(
            user=user,
            party=party,
            defaults={
                "current_state": ComplianceState.DRAFT,
                "current_risk_tier": RiskTier.MEDIUM,
                "operability_blocked": True,
            },
        )

        if create_case:
            cls.ensure_case_for_profile(profile, ComplianceCaseType.INDIVIDUAL_KYC)

        return profile

    @classmethod
    def ensure_case_for_profile(cls, profile, case_type):
        policy_version = cls.get_default_policy_version()
        case = ComplianceCase.objects.filter(
            profile=profile,
            case_type=case_type,
            closed_at__isnull=True,
        ).first()
        if case is None:
            case = ComplianceCase.objects.create(
                profile=profile,
                case_type=case_type,
                state=ComplianceState.DRAFT,
                risk_tier=RiskTier.MEDIUM,
                policy_version=policy_version,
            )
        return case

    @classmethod
    def create_entity_profile(
        cls,
        *,
        owner_user,
        display_name,
        legal_name,
        jurisdiction="",
        country_code="",
        incorporation_date=None,
        external_reference="",
        metadata=None,
    ):
        party = ComplianceParty.objects.create(
            party_type=PartyType.ENTITY,
            display_name=display_name,
            legal_name=legal_name or display_name,
            jurisdiction=jurisdiction,
            country_code=country_code,
            incorporation_date=incorporation_date,
            external_reference=external_reference,
            metadata=metadata or {},
        )
        profile = ComplianceProfile.objects.create(
            party=party,
            user=owner_user,
            current_state=ComplianceState.DRAFT,
            current_risk_tier=RiskTier.MEDIUM,
            operability_blocked=True,
        )
        cls.ensure_case_for_profile(profile, ComplianceCaseType.ENTITY_KYB)
        return profile

    @classmethod
    def create_related_individual_party(
        cls,
        *,
        first_name,
        last_name,
        email="",
        jurisdiction="",
        country_code="",
        metadata=None,
    ):
        display_name = " ".join(part for part in [first_name, last_name] if part).strip() or email
        party = ComplianceParty.objects.create(
            party_type=PartyType.INDIVIDUAL,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            email=email,
            jurisdiction=jurisdiction,
            country_code=country_code,
            metadata=metadata or {},
        )
        profile = ComplianceProfile.objects.create(
            party=party,
            user=None,
            current_state=ComplianceState.DRAFT,
            current_risk_tier=RiskTier.MEDIUM,
            operability_blocked=True,
        )
        cls.ensure_case_for_profile(profile, ComplianceCaseType.UBO_KYC)
        return profile

    @classmethod
    def attach_related_party(
        cls,
        *,
        entity_profile,
        related_profile,
        relationship_type,
        ownership_percentage=None,
        control_notes="",
        metadata=None,
    ):
        relationship = PartyRelationship.objects.create(
            from_party=entity_profile.party,
            to_party=related_profile.party,
            relationship_type=relationship_type,
            ownership_percentage=ownership_percentage,
            control_notes=control_notes,
            metadata=metadata or {},
        )

        case_type = {
            RelationshipType.BENEFICIAL_OWNER: ComplianceCaseType.UBO_KYC,
            RelationshipType.CONTROLLER: ComplianceCaseType.CONTROLLER_KYC,
            RelationshipType.AUTHORIZED_SIGNER: ComplianceCaseType.CONTROLLER_KYC,
            RelationshipType.DIRECTOR: ComplianceCaseType.CONTROLLER_KYC,
        }[relationship_type]
        cls.ensure_case_for_profile(related_profile, case_type)
        return relationship
