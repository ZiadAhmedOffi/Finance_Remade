from django.contrib import admin

from compliance import models


@admin.register(models.PolicyVersion)
class PolicyVersionAdmin(admin.ModelAdmin):
    list_display = ("policy_key", "version", "jurisdiction_scope", "subject_scope", "effective_from")


@admin.register(models.ComplianceParty)
class CompliancePartyAdmin(admin.ModelAdmin):
    list_display = ("display_name", "party_type", "country_code", "jurisdiction", "created_at")
    search_fields = ("display_name", "legal_name", "email")


@admin.register(models.ComplianceProfile)
class ComplianceProfileAdmin(admin.ModelAdmin):
    list_display = ("party", "user", "current_state", "current_risk_tier", "operability_blocked", "is_legacy_subject")
    list_filter = ("current_state", "current_risk_tier", "operability_blocked", "is_legacy_subject")


@admin.register(models.ComplianceCase)
class ComplianceCaseAdmin(admin.ModelAdmin):
    list_display = ("id", "profile", "case_type", "state", "risk_tier", "opened_at")
    list_filter = ("case_type", "state", "risk_tier")

