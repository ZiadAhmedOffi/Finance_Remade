from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Fund, FundLog, ModelInput, InvestmentDeal, CurrentDeal, InvestmentRound
from .serializers import (
    FundSerializer, 
    FundLogSerializer, 
    ModelInputSerializer, 
    InvestmentDealSerializer,
    CurrentDealSerializer,
    InvestmentRoundSerializer
)
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
        fund = get_object_or_404(Fund, id=fund_id)
        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
             
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        # Ensure model inputs exist (they should due to signal, but just in case)
        model_inputs, created = ModelInput.objects.get_or_create(fund=fund)
        serializer = ModelInputSerializer(model_inputs)
        return Response(serializer.data)

    def put(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

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
        fund = get_object_or_404(Fund, id=fund_id)
        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deals = fund.deals.all()
        serializer = InvestmentDealSerializer(deals, many=True)
        return Response(serializer.data)

    def post(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

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
                metadata={"deal_id": str(deal.id), "company_name": deal.company_name}
            )
            AuditService.log(
                actor=request.user,
                action="DEAL_CREATED",
                fund=fund,
                metadata={"deal_id": str(deal.id), "company_name": deal.company_name},
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
        fund = get_object_or_404(Fund, id=fund_id)
        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

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
                metadata={"deal_id": str(deal.id), "company_name": deal.company_name}
            )
            AuditService.log(
                actor=request.user,
                action="DEAL_UPDATED",
                fund=fund,
                metadata={"deal_id": str(deal.id), "company_name": deal.company_name},
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, fund_id, deal_id):
        """
        Deletes a specific investment deal.
        Restricted to Super Admins and Fund Steering Committee members.
        """
        fund = get_object_or_404(Fund, id=fund_id)
        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deal = get_object_or_404(InvestmentDeal, id=deal_id, fund=fund)
        company_name = deal.company_name
        deal_id_str = str(deal.id)
        deal.delete()
        
        # Log the change
        FundLog.objects.create(
            actor=request.user,
            target_fund=fund,
            action="DEAL_DELETED",
            metadata={"deal_id": deal_id_str, "company_name": company_name}
        )
        AuditService.log(
            actor=request.user,
            action="DEAL_DELETED",
            fund=fund,
            metadata={"deal_id": deal_id_str, "company_name": company_name},
            ip=request.META.get("REMOTE_ADDR")
        )
        return Response({"message": "Deal deleted."}, status=status.HTTP_200_OK)


class CurrentDealListView(APIView):
    """
    Handles listing and creating current deals (deals already made) for a specific fund.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deals = fund.current_deals.all()
        serializer = CurrentDealSerializer(deals, many=True)
        return Response(serializer.data)

    def post(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = CurrentDealSerializer(data=request.data)
        if serializer.is_valid():
            deal = serializer.save(fund=fund)
            
            # Log the change
            FundLog.objects.create(
                actor=request.user,
                target_fund=fund,
                action="CURRENT_DEAL_CREATED",
                metadata={"deal_id": str(deal.id), "company_name": deal.company_name}
            )
            AuditService.log(
                actor=request.user,
                action="CURRENT_DEAL_CREATED",
                fund=fund,
                metadata={"deal_id": str(deal.id), "company_name": deal.company_name},
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentDealDetailView(APIView):
    """
    Handles updating and deleting specific current deals.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, fund_id, deal_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deal = get_object_or_404(CurrentDeal, id=deal_id, fund=fund)
        serializer = CurrentDealSerializer(deal, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Log the change
            FundLog.objects.create(
                actor=request.user,
                target_fund=fund,
                action="CURRENT_DEAL_UPDATED",
                metadata={"deal_id": str(deal.id), "company_name": deal.company_name}
            )
            AuditService.log(
                actor=request.user,
                action="CURRENT_DEAL_UPDATED",
                fund=fund,
                metadata={"deal_id": str(deal.id), "company_name": deal.company_name},
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, fund_id, deal_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deal = get_object_or_404(CurrentDeal, id=deal_id, fund=fund)
        company_name = deal.company_name
        deal_id_str = str(deal.id)
        deal.delete()
        
        # Log the change
        FundLog.objects.create(
            actor=request.user,
            target_fund=fund,
            action="CURRENT_DEAL_DELETED",
            metadata={"deal_id": deal_id_str, "company_name": company_name}
        )
        AuditService.log(
            actor=request.user,
            action="CURRENT_DEAL_DELETED",
            fund=fund,
            metadata={"deal_id": deal_id_str, "company_name": company_name},
            ip=request.META.get("REMOTE_ADDR")
        )
        return Response({"message": "Current deal deleted."}, status=status.HTTP_200_OK)


class InvestmentRoundListView(APIView):
    """
    Handles listing and creating investment rounds for a company.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        company_name = request.query_params.get("company_name")
        if not company_name:
            # If no company name provided, return all rounds for the fund
            rounds = fund.investment_rounds.all()
        else:
            rounds = fund.investment_rounds.filter(company_name=company_name)
        
        serializer = InvestmentRoundSerializer(rounds, many=True)
        return Response(serializer.data)

    def post(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = InvestmentRoundSerializer(data=request.data)
        if serializer.is_valid():
            company_name = serializer.validated_data["company_name"]
            exercise_pro_rata = serializer.validated_data.get("exercise_pro_rata", False)
            amount_invested = serializer.validated_data.get("amount_invested", 0)
            target_valuation = serializer.validated_data["target_valuation"]
            year = serializer.validated_data["year"]
            
            # Find the "main" deal to use as parent if exercising pro rata
            main_deal = fund.current_deals.filter(company_name=company_name, is_pro_rata=False).first()
            
            # Temporary save round to get data for CurrentDeal
            round_obj = serializer.save(fund=fund)
            
            associated_deal = None
            # If pro rata exercised, create a new CurrentDeal
            if exercise_pro_rata and amount_invested > 0:
                associated_deal = CurrentDeal.objects.create(
                    fund=fund,
                    company_name=company_name,
                    company_type=main_deal.company_type if main_deal else "",
                    industry=main_deal.industry if main_deal else "",
                    entry_year=year,
                    latest_valuation_year=year,
                    amount_invested=amount_invested,
                    entry_valuation=target_valuation, # Use target valuation as entry valuation for pro-rata
                    latest_valuation=target_valuation,
                    is_pro_rata=True,
                    parent_deal=main_deal
                )
            
            # Update latest valuation of ALL deals for this company
            fund.current_deals.filter(company_name=company_name).update(
                latest_valuation=target_valuation,
                latest_valuation_year=year
            )
            
            # Re-save round with associated_deal link
            if associated_deal:
                round_obj.associated_deal = associated_deal
                round_obj.save()
            
            # Log the change
            FundLog.objects.create(
                actor=request.user,
                target_fund=fund,
                action="CURRENT_DEAL_UPDATED",
                metadata={"company_name": company_name, "round_id": str(round_obj.id)}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvestmentRoundDetailView(APIView):
    """
    Handles updating and deleting specific investment rounds.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, fund_id, round_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        round_obj = get_object_or_404(InvestmentRound, id=round_id, fund=fund)
        serializer = InvestmentRoundSerializer(round_obj, data=request.data, partial=True)
        if serializer.is_valid():
            company_name = round_obj.company_name
            exercise_pro_rata = serializer.validated_data.get("exercise_pro_rata", round_obj.exercise_pro_rata)
            amount_invested = serializer.validated_data.get("amount_invested", round_obj.amount_invested)
            target_valuation = serializer.validated_data.get("target_valuation", round_obj.target_valuation)
            year = serializer.validated_data.get("year", round_obj.year)
            
            # Update or Create associated deal
            if exercise_pro_rata and amount_invested > 0:
                main_deal = fund.current_deals.filter(company_name=company_name, is_pro_rata=False).first()
                if round_obj.associated_deal:
                    # Update existing deal
                    deal = round_obj.associated_deal
                    deal.amount_invested = amount_invested
                    deal.entry_year = year
                    deal.latest_valuation_year = year
                    deal.entry_valuation = target_valuation
                    deal.latest_valuation = target_valuation
                    deal.save()
                else:
                    # Create new deal
                    new_deal = CurrentDeal.objects.create(
                        fund=fund,
                        company_name=company_name,
                        company_type=main_deal.company_type if main_deal else "",
                        industry=main_deal.industry if main_deal else "",
                        entry_year=year,
                        latest_valuation_year=year,
                        amount_invested=amount_invested,
                        entry_valuation=target_valuation,
                        latest_valuation=target_valuation,
                        is_pro_rata=True,
                        parent_deal=main_deal
                    )
                    round_obj.associated_deal = new_deal
            elif round_obj.associated_deal:
                # User unchecked pro rata or amount is 0, delete the deal
                round_obj.associated_deal.delete()
                round_obj.associated_deal = None
            
            # Save round
            round_obj = serializer.save()

            # Always update latest valuation for all deals to reflect the potentially updated target_valuation of the round
            fund.current_deals.filter(company_name=company_name).update(
                latest_valuation=target_valuation,
                latest_valuation_year=year
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, fund_id, round_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        round_obj = get_object_or_404(InvestmentRound, id=round_id, fund=fund)
        company_name = round_obj.company_name
        
        # Delete associated deal if exists
        if round_obj.associated_deal:
            round_obj.associated_deal.delete()
            
        round_obj.delete()

        # Recalculate latest valuation from the remaining rounds
        remaining_rounds = fund.investment_rounds.filter(company_name=company_name).order_by('-year', '-created_at')
        if remaining_rounds.exists():
            latest = remaining_rounds.first()
            fund.current_deals.filter(company_name=company_name).update(
                latest_valuation=latest.target_valuation,
                latest_valuation_year=latest.year
            )
        else:
            # Revert to original deal entry valuation if possible
            main_deal = fund.current_deals.filter(company_name=company_name, is_pro_rata=False).first()
            if main_deal:
                fund.current_deals.filter(company_name=company_name).update(
                    latest_valuation=main_deal.entry_valuation + main_deal.amount_invested,
                    latest_valuation_year=main_deal.entry_year
                )

        return Response({"message": "Round deleted."}, status=status.HTTP_200_OK)


class FundListView(APIView):
    """
    Lists funds accessible to the user or creates new funds (Super Admin only).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """ List all funds for admins, or funds where the user has a role. """
        if PermissionService.is_super_admin(request.user):
            funds = Fund.objects.all()
        else:
            # For non-superadmins, show active funds where they have ANY role
            from users.models import UserRoleAssignment
            fund_ids = UserRoleAssignment.objects.filter(user=request.user).values_list("fund_id", flat=True)
            funds = Fund.objects.filter(id__in=fund_ids).exclude(status="DEACTIVATED")
        
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
    Detailed view for a single fund, including update and status change.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = FundSerializer(fund)
        return Response(serializer.data)

    def put(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        
        # Check if the user is trying to update status
        new_status = request.data.get("status")
        if new_status and new_status != fund.status:
            # SC can change status only for their assigned funds, Super Admin for all.
            # PermissionService.can_edit_fund already covers this check.
            if not PermissionService.can_edit_fund(request.user, fund):
                 return Response({"error": "Permission denied to change status."}, status=status.HTTP_403_FORBIDDEN)
            
            old_status = fund.status
            fund.status = new_status
            fund.save()
            
            FundLog.objects.create(
                actor=request.user,
                target_fund=fund,
                action="FUND_STATUS_UPDATED",
                metadata={"old": old_status, "new": new_status}
            )
            AuditService.log(
                actor=request.user,
                action="FUND_STATUS_UPDATED",
                fund=fund,
                metadata={"old": old_status, "new": new_status},
                ip=request.META.get("REMOTE_ADDR")
            )
            # If only status was sent, we can return here
            if len(request.data) == 1:
                return Response(FundSerializer(fund).data)

        if not PermissionService.can_edit_fund(request.user, fund):
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
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, fund_id):
        """ Deactivate fund. Only Super Admin or SC. """
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        old_status = fund.status
        fund.status = "DEACTIVATED"
        fund.save()
        
        FundLog.objects.create(
            actor=request.user,
            target_fund=fund,
            action="FUND_STATUS_UPDATED",
            metadata={"old": old_status, "new": "DEACTIVATED"}
        )
        AuditService.log(
            actor=request.user,
            action="FUND_STATUS_UPDATED",
            fund=fund,
            metadata={"old": old_status, "new": "DEACTIVATED"},
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

def calculate_irr(real_moic, exit_horizon):
    """
    Calculates IRR based on the formula: [(Real MOIC to Investors)^(1/Exit Horizon) - 1]
    """
    if real_moic <= 0 or exit_horizon <= 0:
        return 0.0
    return (float(real_moic) ** (1.0 / float(exit_horizon))) - 1.0

class FundPerformanceView(APIView):
    """
    Calculates performance metrics for the three dashboard tabs:
    1. Dashboard Tab
    2. Aggregated Exits Tab
    3. Admin Fee Tab
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deals = fund.deals.all()
        current_deals = fund.current_deals.all()
        model_inputs = getattr(fund, "model_inputs", None)
        
        if not model_inputs:
            return Response({"error": "Model inputs not found for this fund."}, status=status.HTTP_400_BAD_REQUEST)

        exit_horizon = float(model_inputs.exit_horizon)
        management_fee_pct = float(model_inputs.management_fee)

        # 1. Deal Prognosis Metrics (Future Only)
        total_invested = sum(deal.amount_invested for deal in deals)
        deal_serializer = InvestmentDealSerializer(deals, many=True)
        deals_data = deal_serializer.data
        gross_exit_value = sum(float(d["exit_value"]) for d in deals_data)
        
        total_invested_float = float(total_invested)
        moic = gross_exit_value / total_invested_float if total_invested_float > 0 else 0
        
        # Calculate Real MOIC for Prognosis (Pro-forma)
        p_profit = gross_exit_value - total_invested_float
        p_carry_pct = 0.0
        p_tier1_moic = float(model_inputs.least_expected_moic_tier_1)
        p_tier2_moic = float(model_inputs.least_expected_moic_tier_2)
        if moic < p_tier1_moic:
            p_carry_pct = 0.0
        elif moic < p_tier2_moic:
            p_carry_pct = float(model_inputs.tier_1_carry)
        else:
            p_carry_pct = float(model_inputs.tier_2_carry)
        
        p_carry_amount = p_profit * (p_carry_pct / 100.0) if p_profit > 0 else 0
        p_total_fees = total_invested_float * (management_fee_pct / 100.0)
        p_net_to_investors = gross_exit_value - (p_total_fees + p_carry_amount)
        p_real_moic = p_net_to_investors / total_invested_float if total_invested_float > 0 else 0
        
        # Use new IRR formula
        irr = calculate_irr(p_real_moic, exit_horizon)

        # 2. Current Deals Metrics (Past Only)
        c_total_invested = sum(d.amount_invested for d in current_deals)
        c_deal_serializer = CurrentDealSerializer(current_deals, many=True)
        c_deals_data = c_deal_serializer.data
        c_gross_exit_value = sum(float(d["final_exit_amount"]) for d in c_deals_data)
        
        c_total_invested_float = float(c_total_invested)
        c_moic = c_gross_exit_value / c_total_invested_float if c_total_invested_float > 0 else 0
        
        # Calculate Real MOIC for Current Deals
        c_profit = c_gross_exit_value - c_total_invested_float
        c_carry_pct = 0.0
        if c_moic < p_tier1_moic:
            c_carry_pct = 0.0
        elif c_moic < p_tier2_moic:
            c_carry_pct = float(model_inputs.tier_1_carry)
        else:
            c_carry_pct = float(model_inputs.tier_2_carry)
        
        c_carry_amount = c_profit * (c_carry_pct / 100.0) if c_profit > 0 else 0
        c_total_fees = c_total_invested_float * (management_fee_pct / 100.0)
        c_net_to_investors = c_gross_exit_value - (c_total_fees + c_carry_amount)
        c_real_moic = c_net_to_investors / c_total_invested_float if c_total_invested_float > 0 else 0
        
        # Use new IRR formula
        c_irr = calculate_irr(c_real_moic, exit_horizon)


        # 3. Performance Table (Combined for charts)
        from datetime import datetime
        current_year = datetime.now().year
        start_year = int(model_inputs.inception_year)
        fund_life = int(model_inputs.fund_life)
        end_year = start_year + fund_life - 1
        
        # Adjust start/end years based on deals
        all_entry_years = [d["entry_year"] for d in deals_data] + [d["entry_year"] for d in c_deals_data]
        all_exit_years = [d["exit_year"] for d in deals_data] + [d["latest_valuation_year"] for d in c_deals_data]
        
        if all_entry_years:
            start_year = min(start_year, min(all_entry_years))
        if all_exit_years:
            end_year = max(end_year, max(all_exit_years))

        if end_year - start_year > 100:
            end_year = start_year + 100

        # Group deals by year
        current_deals_by_year = {}
        for d in c_deals_data:
            yr = d["entry_year"]
            current_deals_by_year.setdefault(yr, []).append(d)
            
        prognosis_deals_by_year = {}
        for d in deals_data:
            yr = d["entry_year"]
            prognosis_deals_by_year.setdefault(yr, []).append(d)
        
        performance_table = []
        current_portfolio_value = 0.0
        prognosis_portfolio_value = 0.0
        
        cumulative_injection_no_prognosis = 0.0
        cumulative_injection_with_prognosis = 0.0
        
        cumulative_deals_count_current = 0
        cumulative_deals_count_prognosis = 0
        
        safe_c_irr = c_irr if c_irr and c_irr > -1 else 0.0
        safe_p_irr = irr if irr and irr > -1 else 0.0
        
        for year in range(start_year, end_year + 1):
            # 1. Current deals data for this year
            year_current_deals = current_deals_by_year.get(year, [])
            c_injection = sum(float(d["amount_invested"]) for d in year_current_deals)
            c_deals_count = len(year_current_deals)
            
            # 2. Prognosis deals data for this year
            year_prognosis_deals = prognosis_deals_by_year.get(year, [])
            p_injection = sum(float(d["amount_invested"]) for d in year_prognosis_deals)
            p_deals_count = len(year_prognosis_deals)
            
            # Appreciation
            c_appreciation = current_portfolio_value * safe_c_irr
            p_appreciation = prognosis_portfolio_value * safe_p_irr
            
            # Start values for the record
            c_start_val = current_portfolio_value
            p_start_val = prognosis_portfolio_value
            
            # Update portfolio values
            current_portfolio_value += c_injection + c_appreciation
            prognosis_portfolio_value += p_injection + p_appreciation
            
            # Cumulative injections
            cumulative_injection_no_prognosis += c_injection
            cumulative_injection_with_prognosis += c_injection + p_injection
            
            # Cumulative deals
            cumulative_deals_count_current += c_deals_count
            cumulative_deals_count_prognosis += p_deals_count
            
            # Totals
            total_portfolio_value_with_prognosis = current_portfolio_value + prognosis_portfolio_value
            
            performance_table.append({
                "year": year,
                "current_year": current_year,
                "is_future": year > current_year,
                
                # For Graph 1 (Annual Portfolio Value Expansion - Bars)
                "injection_current": c_injection if year <= current_year else 0,
                "appreciation_current": c_appreciation if year <= current_year else 0,
                
                "injection_prognosis": p_injection if year >= current_year else 0, 
                "appreciation_prognosis": p_appreciation if year >= current_year else 0,
                
                "appreciation_of_current_after_cutoff": c_appreciation if year > current_year else 0,
                "injection_of_current_after_cutoff": c_injection if year > current_year else 0,
                
                # For Graph 2 (Capital Appreciation - Lines)
                "total_portfolio_value_no_prognosis": current_portfolio_value,
                "total_portfolio_value_with_prognosis": total_portfolio_value_with_prognosis,
                "cumulative_injection_no_prognosis": cumulative_injection_no_prognosis,
                "cumulative_injection_with_prognosis": cumulative_injection_with_prognosis,

                # For Investment Velocity Graphs
                "deals_count_current": c_deals_count,
                "deals_count_prognosis": p_deals_count,
                "cumulative_deals_count_current": cumulative_deals_count_current,
                "cumulative_deals_count_prognosis": cumulative_deals_count_current + cumulative_deals_count_prognosis,
            })

        # 4. Aggregated Exits (using only Current Deals)
        cases = [
            {"name": "Base Case", "multiplier": 1.0},
            {"name": "Upside Case", "multiplier": 1.2},
            {"name": "High Growth Case", "multiplier": 1.5},
        ]
        aggregated_exits = []
        
        # Use only Current Deals for Aggregated Exits
        total_combined_invested = float(c_total_invested)
        total_combined_gev = float(c_gross_exit_value)
        
        for case in cases:
            # Case GEV applies multiplier to current deals valuation
            case_gev = total_combined_gev * case["multiplier"]
            profit_before_carry = case_gev - total_combined_invested
            case_moic = case_gev / total_combined_invested if total_combined_invested > 0 else 0
            
            if case_moic < p_tier1_moic:
                case_carry_pct = 0.0
            elif case_moic < p_tier2_moic:
                case_carry_pct = float(model_inputs.tier_1_carry)
            else:
                case_carry_pct = float(model_inputs.tier_2_carry)
            
            case_carry_amount = profit_before_carry * (case_carry_pct / 100.0) if profit_before_carry > 0 else 0
            case_total_fees = total_combined_invested * (management_fee_pct / 100.0)
            case_net_to_investors = case_gev - (case_total_fees + case_carry_amount)
            case_real_moic = case_net_to_investors / total_combined_invested if total_combined_invested > 0 else 0
            
            # New IRR formula for each case
            case_irr = calculate_irr(case_real_moic, exit_horizon)
            
            aggregated_exits.append({
                "case": case["name"],
                "gev": case_gev,
                "profit_before_carry": profit_before_carry,
                "gross_moic": case_moic,
                "carry_pct": case_carry_pct,
                "carry_amount": case_carry_amount,
                "total_fees": case_total_fees,
                "net_to_investors": case_net_to_investors,
                "real_moic": case_real_moic,
                "irr": case_irr
            })

        # 5. Admin Fee Tab
        target_fund_size = float(model_inputs.target_fund_size)
        admin_pct = float(model_inputs.admin_cost)
        total_admin_cost = (admin_pct / 100.0) * target_fund_size
        operations_fee = (management_fee_pct / 100.0) * target_fund_size
        management_fees_total = (management_fee_pct / 100.0) * target_fund_size * float(model_inputs.fund_life)
        
        admin_fee_data = {
            "total_admin_cost": total_admin_cost,
            "operations_fee": operations_fee,
            "management_fees": management_fees_total,
            "total_costs": total_admin_cost + operations_fee + management_fees_total,
            "inception_year": int(model_inputs.inception_year),
            "fund_life": int(model_inputs.fund_life)
        }

        return Response({
            "dashboard": {
                "total_invested": total_invested_float,
                "gross_exit_value": gross_exit_value,
                "moic": moic,
                "irr": irr,
                "real_moic": p_real_moic,
                "total_deals": deals.count(),
                "performance_table": performance_table
            },
            "current_deals_metrics": {
                "total_invested": c_total_invested_float,
                "gross_exit_value": c_gross_exit_value,
                "moic": c_moic,
                "irr": c_irr,
                "real_moic": c_real_moic,
                "total_deals": current_deals.count()
            },
            "aggregated_exits": aggregated_exits,
            "admin_fee": admin_fee_data
        })
