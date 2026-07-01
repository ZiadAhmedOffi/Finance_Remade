from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from compliance.models import ComplianceState
from compliance.api.serializers import (
    ComplianceRescreenSerializer,
    ComplianceCaseMutationSerializer,
    ComplianceCaseDetailSerializer,
    ComplianceCaseSerializer,
    ComplianceProfileSerializer,
    ComplianceRestrictionSerializer,
    EvidenceDocumentCreateSerializer,
    EvidenceDocumentSerializer,
    EntityComplianceProfileCreateSerializer,
    EntityRelationshipCreateSerializer,
    PartyRelationshipSerializer,
    RiskAssessmentCreateSerializer,
    RiskAssessmentSerializer,
    RestrictionCreateSerializer,
    ReviewTaskSerializer,
    ReviewTaskAssignmentSerializer,
    VendorCaseSerializer,
    VendorSyncSerializer,
)
from compliance.permissions import IsComplianceStaff
from compliance.services.case_management_service import ComplianceCaseManagementService
from compliance.services.evidence_service import ComplianceEvidenceService
from compliance.services.profile_service import ComplianceProfileService
from compliance.services.risk_service import ComplianceRiskService
from compliance.services.vendor_service import ComplianceVendorService
from compliance.selectors.compliance_selectors import (
    get_active_restrictions_for_user,
    get_case_for_user,
    get_cases_for_user,
    get_evidence_documents_queryset,
    get_cases_queryset,
    get_profile_for_user,
    get_primary_profile_for_user,
    get_profiles_queryset,
    get_restrictions_queryset,
    get_review_tasks_queryset,
    get_vendor_cases_queryset,
)

User = get_user_model()


class ComplianceHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "message": "Compliance app scaffold is installed.",
            }
        )


class CurrentComplianceProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_primary_profile_for_user(request.user)
        if profile is None:
            return Response({"error": "Compliance profile not found."}, status=404)

        data = ComplianceProfileSerializer(profile).data
        data["active_restrictions"] = ComplianceRestrictionSerializer(
            get_active_restrictions_for_user(request.user),
            many=True,
        ).data
        return Response(data)


class MyComplianceCasesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cases = get_cases_for_user(request.user)
        return Response(ComplianceCaseSerializer(cases, many=True).data)


class ComplianceCaseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, case_id):
        case = get_case_for_user(request.user, case_id)
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)
        return Response(ComplianceCaseDetailSerializer(case).data)


class MyComplianceCaseSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, case_id):
        case = get_case_for_user(request.user, case_id)
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)
        if case.state not in [ComplianceState.DRAFT, ComplianceState.WAITING_FOR_APPLICANT]:
            return Response({"error": "Case cannot be submitted from its current state."}, status=400)

        vendor_case = ComplianceVendorService.queue_case_submission(case=case, actor=request.user)
        return Response(VendorCaseSerializer(vendor_case).data, status=202)


class MyComplianceCaseEvidenceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, case_id):
        case = get_case_for_user(request.user, case_id)
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)
        documents = get_evidence_documents_queryset().filter(case=case)
        return Response(EvidenceDocumentSerializer(documents, many=True).data)

    def post(self, request, case_id):
        case = get_case_for_user(request.user, case_id)
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)

        serializer = EvidenceDocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = ComplianceEvidenceService.add_evidence_document(
            case=case,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(EvidenceDocumentSerializer(document).data, status=201)


class ComplianceAdminProfileListView(APIView):
    permission_classes = [IsComplianceStaff]

    def get(self, request):
        profiles = get_profiles_queryset()
        state = request.query_params.get("state")
        risk_tier = request.query_params.get("risk_tier")
        search = request.query_params.get("search")

        if state:
            profiles = profiles.filter(current_state=state)
        if risk_tier:
            profiles = profiles.filter(current_risk_tier=risk_tier)
        if search:
            profiles = profiles.filter(
                Q(party__display_name__icontains=search) | Q(party__email__icontains=search)
            )

        return Response(ComplianceProfileSerializer(profiles[:100], many=True).data)


class ComplianceAdminCaseListView(APIView):
    permission_classes = [IsComplianceStaff]

    def get(self, request):
        cases = get_cases_queryset()
        state = request.query_params.get("state")
        risk_tier = request.query_params.get("risk_tier")
        case_type = request.query_params.get("case_type")
        profile_id = request.query_params.get("profile_id")

        if state:
            cases = cases.filter(state=state)
        if risk_tier:
            cases = cases.filter(risk_tier=risk_tier)
        if case_type:
            cases = cases.filter(case_type=case_type)
        if profile_id:
            cases = cases.filter(profile_id=profile_id)

        return Response(ComplianceCaseSerializer(cases[:100], many=True).data)


class ComplianceAdminCaseDetailView(APIView):
    permission_classes = [IsComplianceStaff]

    def get(self, request, case_id):
        case = get_cases_queryset().filter(id=case_id).first()
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)
        return Response(ComplianceCaseDetailSerializer(case).data)


class ComplianceAdminCaseEvidenceListCreateView(APIView):
    permission_classes = [IsComplianceStaff]

    def get(self, request, case_id):
        case = get_cases_queryset().filter(id=case_id).first()
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)
        documents = get_evidence_documents_queryset().filter(case=case)
        return Response(EvidenceDocumentSerializer(documents, many=True).data)

    def post(self, request, case_id):
        case = get_cases_queryset().filter(id=case_id).first()
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)

        serializer = EvidenceDocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = ComplianceEvidenceService.add_evidence_document(
            case=case,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(EvidenceDocumentSerializer(document).data, status=201)


class ComplianceAdminCaseRiskAssessmentCreateView(APIView):
    permission_classes = [IsComplianceStaff]

    def post(self, request, case_id):
        case = get_cases_queryset().filter(id=case_id).first()
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)

        serializer = RiskAssessmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assessment = ComplianceRiskService.record_risk_assessment(
            case=case,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(RiskAssessmentSerializer(assessment).data, status=201)


class ComplianceReviewTaskListView(APIView):
    permission_classes = [IsComplianceStaff]

    def get(self, request):
        tasks = get_review_tasks_queryset()
        status_filter = request.query_params.get("status")
        assignee = request.query_params.get("assignee")
        priority = request.query_params.get("priority")

        if status_filter:
            tasks = tasks.filter(status=status_filter)
        if assignee:
            tasks = tasks.filter(assignee_id=assignee)
        if priority:
            tasks = tasks.filter(priority=priority)

        return Response(ReviewTaskSerializer(tasks[:100], many=True).data)


class ComplianceAdminCaseAssignTaskView(APIView):
    permission_classes = [IsComplianceStaff]

    def post(self, request, case_id):
        case = get_cases_queryset().filter(id=case_id).first()
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)

        serializer = ReviewTaskAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignee = None
        assignee_id = serializer.validated_data.get("assignee_id")
        if assignee_id is not None:
            assignee = User.objects.filter(id=assignee_id, is_active=True).first()
            if assignee is None:
                return Response({"error": "Assignee not found."}, status=404)

        task = ComplianceCaseManagementService.assign_review_task(
            case=case,
            actor=request.user,
            assignee=assignee,
            task_type=serializer.validated_data["task_type"],
            priority=serializer.validated_data["priority"],
            reason=serializer.validated_data.get("reason", ""),
            notes=serializer.validated_data.get("notes", ""),
            sla_due_at=serializer.validated_data.get("sla_due_at"),
        )
        return Response(ReviewTaskSerializer(task).data, status=201)


class ComplianceAdminCaseRequestInformationView(APIView):
    permission_classes = [IsComplianceStaff]

    def post(self, request, case_id):
        case = get_cases_queryset().filter(id=case_id).first()
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)

        serializer = ComplianceCaseMutationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = ComplianceCaseManagementService.request_information(
            case=case,
            actor=request.user,
            notes=serializer.validated_data.get("notes", ""),
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return Response(ComplianceCaseDetailSerializer(case).data)


class ComplianceAdminCaseApproveView(APIView):
    permission_classes = [IsComplianceStaff]

    def post(self, request, case_id):
        case = get_cases_queryset().filter(id=case_id).first()
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)

        serializer = ComplianceCaseMutationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            case = ComplianceCaseManagementService.approve_case(
                case=case,
                actor=request.user,
                notes=serializer.validated_data.get("notes", ""),
                metadata=serializer.validated_data.get("metadata", {}),
            )
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(ComplianceCaseDetailSerializer(case).data)


class ComplianceAdminCaseRejectView(APIView):
    permission_classes = [IsComplianceStaff]

    def post(self, request, case_id):
        case = get_cases_queryset().filter(id=case_id).first()
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)

        serializer = ComplianceCaseMutationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            case = ComplianceCaseManagementService.reject_case(
                case=case,
                actor=request.user,
                notes=serializer.validated_data.get("notes", ""),
                metadata=serializer.validated_data.get("metadata", {}),
            )
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(ComplianceCaseDetailSerializer(case).data)


class ComplianceAdminCaseRestrictView(APIView):
    permission_classes = [IsComplianceStaff]

    def post(self, request, case_id):
        case = get_cases_queryset().filter(id=case_id).first()
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)

        serializer = RestrictionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            restriction = ComplianceCaseManagementService.restrict_case(
                case=case,
                actor=request.user,
                restriction_type=serializer.validated_data["restriction_type"],
                reason_code=serializer.validated_data["reason_code"],
                notes=serializer.validated_data.get("notes", ""),
                metadata=serializer.validated_data.get("metadata", {}),
            )
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(ComplianceRestrictionSerializer(restriction).data, status=201)


class ComplianceAdminRestrictionLiftView(APIView):
    permission_classes = [IsComplianceStaff]

    def post(self, request, restriction_id):
        restriction = get_restrictions_queryset().filter(id=restriction_id).first()
        if restriction is None:
            return Response({"error": "Compliance restriction not found."}, status=404)

        serializer = ComplianceCaseMutationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            restriction = ComplianceCaseManagementService.lift_restriction(
                restriction=restriction,
                actor=request.user,
                notes=serializer.validated_data.get("notes", ""),
                metadata=serializer.validated_data.get("metadata", {}),
            )
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(ComplianceRestrictionSerializer(restriction).data)


class ComplianceAdminCaseSubmitVendorView(APIView):
    permission_classes = [IsComplianceStaff]

    def post(self, request, case_id):
        case = get_cases_queryset().filter(id=case_id).first()
        if case is None:
            return Response({"error": "Compliance case not found."}, status=404)

        vendor_case = ComplianceVendorService.queue_case_submission(case=case, actor=request.user)
        return Response(VendorCaseSerializer(vendor_case).data, status=202)


class ComplianceAdminVendorCaseSyncView(APIView):
    permission_classes = [IsComplianceStaff]

    def post(self, request, vendor_case_id):
        vendor_case = get_vendor_cases_queryset().filter(id=vendor_case_id).first()
        if vendor_case is None:
            return Response({"error": "Vendor case not found."}, status=404)

        serializer = VendorSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        synced_vendor_case = ComplianceVendorService.queue_vendor_sync(
            vendor_case=vendor_case,
            actor=request.user,
            payload=serializer.validated_data.get("payload", {}),
        )
        return Response(VendorCaseSerializer(synced_vendor_case).data, status=202)


class ComplianceAdminProfileRescreenView(APIView):
    permission_classes = [IsComplianceStaff]

    def post(self, request, profile_id):
        profile = get_profiles_queryset().filter(id=profile_id).first()
        if profile is None:
            return Response({"error": "Compliance profile not found."}, status=404)

        serializer = ComplianceRescreenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vendor_case = ComplianceVendorService.rescreen_profile(
            profile_id=str(profile.id),
            source=serializer.validated_data.get("source") or "manual",
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return Response(VendorCaseSerializer(vendor_case).data, status=202)


class PrimaryVendorWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        configured_secret = getattr(settings, "COMPLIANCE_PRIMARY_VENDOR_WEBHOOK_SECRET", "")
        if configured_secret:
            provided_secret = request.headers.get("X-Compliance-Webhook-Secret", "")
            if provided_secret != configured_secret:
                return Response({"error": "Invalid webhook secret."}, status=403)

        try:
            vendor_case = ComplianceVendorService.process_vendor_webhook(
                vendor_name="PRIMARY",
                payload=request.data,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        return Response(VendorCaseSerializer(vendor_case).data, status=202)


class EntityComplianceProfileCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EntityComplianceProfileCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = ComplianceProfileService.create_entity_profile(
            owner_user=request.user,
            **serializer.validated_data,
        )
        return Response(ComplianceProfileSerializer(profile).data, status=201)


class EntityRelationshipCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, profile_id):
        entity_profile = get_profile_for_user(request.user, profile_id)
        if entity_profile is None:
            return Response({"error": "Entity compliance profile not found."}, status=404)
        if entity_profile.party.party_type != "ENTITY":
            return Response({"error": "Relationships can only be attached to entity profiles."}, status=400)

        serializer = EntityRelationshipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        party_data = serializer.validated_data["party"]
        related_profile = ComplianceProfileService.create_related_individual_party(**party_data)
        relationship = ComplianceProfileService.attach_related_party(
            entity_profile=entity_profile,
            related_profile=related_profile,
            relationship_type=serializer.validated_data["relationship_type"],
            ownership_percentage=serializer.validated_data.get("ownership_percentage"),
            control_notes=serializer.validated_data.get("control_notes", ""),
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return Response(PartyRelationshipSerializer(relationship).data, status=201)
