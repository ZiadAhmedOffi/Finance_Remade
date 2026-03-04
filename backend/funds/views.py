from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Fund, FundLog, ModelInput, InvestmentDeal
from .serializers import FundSerializer, FundLogSerializer, ModelInputSerializer, InvestmentDealSerializer
from users.services.permission_service import PermissionService
from users.services.audit_service import AuditService


import json

class ModelInputDetailView(APIView):
    """
    Handles retrieval and update of financial model inputs for a specific fund.
    Only Super Admins and Fund Steering Committee members can update.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id, is_active=True)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        # Ensure model inputs exist (they should due to signal, but just in case)
        model_inputs, created = ModelInput.objects.get_or_create(fund=fund)
        serializer = ModelInputSerializer(model_inputs)
        return Response(serializer.data)

    def put(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id, is_active=True)
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        model_inputs = get_object_or_404(ModelInput, fund=fund)
        old_data = ModelInputSerializer(model_inputs).data
        
        serializer = ModelInputSerializer(model_inputs, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Ensure metadata is JSON-safe
            metadata = json.loads(json.dumps(
                {"old": old_data, "new": serializer.data}, 
                default=str
            ))
            
            # Log the change
            FundLog.objects.create(
                actor=request.user,
                target_fund=fund,
                action="MODEL_INPUTS_UPDATED",
                metadata=metadata
            )
            AuditService.log(
                actor=request.user,
                action="MODEL_INPUTS_UPDATED",
                fund=fund,
                metadata=metadata,
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvestmentDealListView(APIView):
    """
    Handles listing and creating investment deals for a specific fund.
    View access is open to all fund members; creation is restricted to SC and Admins.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id, is_active=True)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deals = fund.deals.all()
        serializer = InvestmentDealSerializer(deals, many=True)
        return Response(serializer.data)

    def post(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id, is_active=True)
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = InvestmentDealSerializer(data=request.data)
        if serializer.is_valid():
            deal = serializer.save(fund=fund)
            
            # Log the change
            FundLog.objects.create(
                actor=request.user,
                target_fund=fund,
                action="DEAL_CREATED",
                metadata={"deal_id": str(deal.id), "name": deal.name}
            )
            AuditService.log(
                actor=request.user,
                action="DEAL_CREATED",
                fund=fund,
                metadata={"deal_id": str(deal.id)},
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvestmentDealDetailView(APIView):
    """
    Handles updating and deleting specific investment deals.
    Restricted to Super Admins and Fund Steering Committee members.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, fund_id, deal_id):
        fund = get_object_or_404(Fund, id=fund_id, is_active=True)
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deal = get_object_or_404(InvestmentDeal, id=deal_id, fund=fund)
        serializer = InvestmentDealSerializer(deal, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Log the change
            FundLog.objects.create(
                actor=request.user,
                target_fund=fund,
                action="DEAL_UPDATED",
                metadata={"deal_id": str(deal.id), "name": deal.name}
            )
            AuditService.log(
                actor=request.user,
                action="DEAL_UPDATED",
                fund=fund,
                metadata={"deal_id": str(deal.id)},
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, fund_id, deal_id):
        fund = get_object_or_404(Fund, id=fund_id, is_active=True)
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deal = get_object_or_404(InvestmentDeal, id=deal_id, fund=fund)
        deal_name = deal.name
        deal_id_str = str(deal.id)
        deal.delete()
        
        # Log the change
        FundLog.objects.create(
            actor=request.user,
            target_fund=fund,
            action="DEAL_DELETED",
            metadata={"deal_id": deal_id_str, "name": deal_name}
        )
        AuditService.log(
            actor=request.user,
            action="DEAL_DELETED",
            fund=fund,
            metadata={"deal_id": deal_id_str},
            ip=request.META.get("REMOTE_ADDR")
        )
        return Response({"message": "Deal deleted."}, status=status.HTTP_200_OK)


class FundListView(APIView):
    """
    Lists funds accessible to the user or creates new funds (Super Admin only).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """ List all active funds for admins, or funds where the user has a role. """
        if PermissionService.is_super_admin(request.user):
            funds = Fund.objects.filter(is_active=True)
        else:
            # For non-superadmins, show funds where they have ANY role (SC or Investor)
            # This is a bit simplified, but follows the "dashboard" requirement
            from users.models import UserRoleAssignment
            fund_ids = UserRoleAssignment.objects.filter(user=request.user).values_list("fund_id", flat=True)
            funds = Fund.objects.filter(id__in=fund_ids, is_active=True)
        
        serializer = FundSerializer(funds, many=True)
        return Response(serializer.data)

    def post(self, request):
        """ Create a new fund. Only Super Admins. """
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Only super admins can create funds."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = FundSerializer(data=request.data)
        if serializer.is_valid():
            fund = serializer.save(created_by=request.user)
            FundLog.objects.create(
                actor=request.user,
                target_fund=fund,
                action="FUND_CREATED"
            )
            AuditService.log(
                actor=request.user,
                action="FUND_CREATED",
                fund=fund,
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FundDetailView(APIView):
    """
    Detailed view for a single fund, including update and deactivation (delete).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id, is_active=True)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = FundSerializer(fund)
        return Response(serializer.data)

    def put(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id, is_active=True)
        
        if not PermissionService.can_edit_fund(request.user, fund):
            FundLog.objects.create(
                actor=request.user,
                target_fund=fund,
                action="FUND_INFO_UPDATE_FAILED",
                success=False,
                metadata={"reason": "Permission denied", "attempted_data": request.data}
            )
            AuditService.log(
                actor=request.user,
                action="FUND_INFO_UPDATE_FAILED",
                fund=fund,
                metadata={"reason": "Permission denied"},
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = FundSerializer(fund, data=request.data, partial=True)
        if serializer.is_valid():
            old_data = {"name": fund.name, "description": fund.description}
            new_data = serializer.validated_data
            serializer.save()
            FundLog.objects.create(
                actor=request.user,
                target_fund=fund,
                action="FUND_INFO_UPDATED",
                success=True,
                metadata={"old": old_data, "new": {k: v for k, v in new_data.items() if k in ["name", "description"]}}
            )
            AuditService.log(
                actor=request.user,
                action="FUND_INFO_UPDATED",
                fund=fund,
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data)
        
        FundLog.objects.create(
            actor=request.user,
            target_fund=fund,
            action="FUND_INFO_UPDATE_FAILED",
            success=False,
            metadata={"errors": {k: [str(e) for e in v] for k, v in serializer.errors.items()}}
        )
        AuditService.log(
            actor=request.user,
            action="FUND_INFO_UPDATE_FAILED",
            fund=fund,
            metadata={"errors": serializer.errors},
            ip=request.META.get("REMOTE_ADDR")
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, fund_id):
        """ Deactivate fund. Only Super Admin. """
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        fund = get_object_or_404(Fund, id=fund_id)
        fund.is_active = False
        fund.save()
        
        FundLog.objects.create(
            actor=request.user,
            target_fund=fund,
            action="FUND_DEACTIVATED"
        )
        AuditService.log(
            actor=request.user,
            action="FUND_DEACTIVATED",
            fund=fund,
            ip=request.META.get("REMOTE_ADDR")
        )
        return Response({"message": "Fund deactivated."}, status=status.HTTP_200_OK)

class FundLogListView(APIView):
    """
    Lists all audit logs related to a specific fund.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        logs = fund.logs.all()
        serializer = FundLogSerializer(logs, many=True)
        return Response(serializer.data)
