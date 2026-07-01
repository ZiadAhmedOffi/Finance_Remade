from compliance.services.vendor_service import ComplianceVendorService


def submit_case_job(*, case_id, actor_id=None):
    return ComplianceVendorService.submit_case(case_id=case_id, actor_id=actor_id)


def sync_vendor_case_job(*, vendor_case_id, payload=None, actor_id=None):
    return ComplianceVendorService.sync_vendor_case(vendor_case_id=vendor_case_id, payload=payload or {}, actor_id=actor_id)


def process_vendor_webhook_job(*, vendor_name, payload):
    return ComplianceVendorService.process_vendor_webhook(vendor_name=vendor_name, payload=payload)


def rescreen_profile_job(*, profile_id, source="manual", metadata=None):
    return ComplianceVendorService.rescreen_profile(profile_id=profile_id, source=source, metadata=metadata or {})
