from dataclasses import dataclass, field

from compliance.models import MatchSeverity, ScreeningCheckType, ScreeningOutcome, SyncStatus, VendorName


@dataclass
class NormalizedScreeningResult:
    check_type: str
    outcome: str
    severity: str = MatchSeverity.INFO
    summary: str = ""
    vendor_reference: str = ""
    raw_payload: dict = field(default_factory=dict)


@dataclass
class NormalizedVendorUpdate:
    external_case_id: str
    sync_status: str
    raw_payload: dict = field(default_factory=dict)
    error_message: str = ""
    screening_results: list[NormalizedScreeningResult] = field(default_factory=list)


class BaseVendorAdapter:
    vendor_name = VendorName.PRIMARY

    def start_case(self, case):
        raise NotImplementedError

    def sync_case(self, vendor_case, raw_payload=None):
        raise NotImplementedError

    def normalize_webhook(self, payload):
        raise NotImplementedError


class PrimaryVendorAdapter(BaseVendorAdapter):
    """
    Scaffold adapter for the primary compliance vendor.
    All vendor-specific mapping should stay here so the rest of the app
    only works with normalized screening and sync records.
    """

    def _default_screening_results(self, case):
        if case.case_type == "ENTITY_KYB":
            return [
                NormalizedScreeningResult(
                    check_type=ScreeningCheckType.BUSINESS,
                    outcome=ScreeningOutcome.PENDING,
                    summary="Business verification queued with primary vendor.",
                ),
                NormalizedScreeningResult(
                    check_type=ScreeningCheckType.SANCTIONS,
                    outcome=ScreeningOutcome.PENDING,
                    summary="Entity sanctions screening queued with primary vendor.",
                ),
                NormalizedScreeningResult(
                    check_type=ScreeningCheckType.PEP,
                    outcome=ScreeningOutcome.PENDING,
                    summary="Entity PEP screening queued with primary vendor.",
                ),
                NormalizedScreeningResult(
                    check_type=ScreeningCheckType.ADVERSE_MEDIA,
                    outcome=ScreeningOutcome.PENDING,
                    summary="Entity adverse media screening queued with primary vendor.",
                ),
            ]

        return [
            NormalizedScreeningResult(
                check_type=ScreeningCheckType.IDENTITY,
                outcome=ScreeningOutcome.PENDING,
                summary="Identity verification queued with primary vendor.",
            ),
            NormalizedScreeningResult(
                check_type=ScreeningCheckType.DOCUMENT,
                outcome=ScreeningOutcome.PENDING,
                summary="Document verification queued with primary vendor.",
            ),
            NormalizedScreeningResult(
                check_type=ScreeningCheckType.SANCTIONS,
                outcome=ScreeningOutcome.PENDING,
                summary="Sanctions screening queued with primary vendor.",
            ),
            NormalizedScreeningResult(
                check_type=ScreeningCheckType.PEP,
                outcome=ScreeningOutcome.PENDING,
                summary="PEP screening queued with primary vendor.",
            ),
            NormalizedScreeningResult(
                check_type=ScreeningCheckType.ADVERSE_MEDIA,
                outcome=ScreeningOutcome.PENDING,
                summary="Adverse media screening queued with primary vendor.",
            ),
        ]

    def start_case(self, case):
        external_case_id = f"primary-{case.id}"
        return NormalizedVendorUpdate(
            external_case_id=external_case_id,
            sync_status=SyncStatus.IN_PROGRESS,
            raw_payload={
                "event": "case_submitted",
                "case_id": str(case.id),
                "case_type": case.case_type,
            },
            screening_results=self._default_screening_results(case),
        )

    def sync_case(self, vendor_case, raw_payload=None):
        payload = raw_payload or {}
        raw_screenings = payload.get("screenings") or []
        if raw_screenings:
            screening_results = [
                NormalizedScreeningResult(
                    check_type=item.get("check_type", ScreeningCheckType.IDENTITY),
                    outcome=item.get("outcome", ScreeningOutcome.REVIEW),
                    severity=item.get("severity", MatchSeverity.INFO),
                    summary=item.get("summary", ""),
                    vendor_reference=item.get("vendor_reference", ""),
                    raw_payload=item,
                )
                for item in raw_screenings
            ]
            sync_status = payload.get("sync_status", SyncStatus.SYNCED)
            error_message = payload.get("error_message", "")
        else:
            screening_results = []
            sync_status = payload.get("sync_status", vendor_case.sync_status or SyncStatus.IN_PROGRESS)
            error_message = payload.get("error_message", "")

        return NormalizedVendorUpdate(
            external_case_id=payload.get("external_case_id", vendor_case.external_case_id),
            sync_status=sync_status,
            raw_payload=payload,
            error_message=error_message,
            screening_results=screening_results,
        )

    def normalize_webhook(self, payload):
        external_case_id = payload.get("external_case_id")
        if not external_case_id:
            raise ValueError("Vendor webhook payload missing external_case_id.")
        return self.sync_case(
            type("VendorCaseStub", (), {"external_case_id": external_case_id, "sync_status": SyncStatus.IN_PROGRESS})(),
            raw_payload=payload,
        )


def get_vendor_adapter(vendor_name):
    if vendor_name == VendorName.PRIMARY:
        return PrimaryVendorAdapter()
    raise ValueError(f"Unsupported compliance vendor: {vendor_name}")
