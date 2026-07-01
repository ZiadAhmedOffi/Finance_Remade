from django.db import transaction

from compliance.models import ComplianceAuditEvent, EvidenceDocument


class ComplianceEvidenceService:
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
    def add_evidence_document(
        cls,
        *,
        case,
        actor,
        document_type,
        storage_mode="VENDOR_REFERENCE",
        vendor_reference="",
        storage_reference="",
        expires_at=None,
        metadata=None,
    ):
        document = EvidenceDocument.objects.create(
            case=case,
            document_type=document_type,
            storage_mode=storage_mode,
            vendor_reference=vendor_reference,
            storage_reference=storage_reference,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        cls._create_audit_event(
            "EVIDENCE_DOCUMENT_ADDED",
            actor=actor,
            case=case,
            metadata={
                "document_id": str(document.id),
                "document_type": document.document_type,
                "storage_mode": document.storage_mode,
            },
        )
        return document
