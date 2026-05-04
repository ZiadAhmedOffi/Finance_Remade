from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from funds.selectors import (
    fund_selectors, 
    deal_selectors, 
    investor_selectors, 
    risk_assessment_selectors, 
    report_selectors
)
from funds.services.fund_service import FundService
from funds.services.deal_service import DealService
from funds.services.investor_service import InvestorService
from funds.services.risk_assessment_service import RiskAssessmentService
from funds.services.report_service import ReportService
from funds.utils import calculators
from funds.utils.liquidityUtils import calculateLiquidityIndex
from users.services.permission_service import PermissionService
from funds.models import Fund, FundLog, ModelInput, InvestmentDeal, CurrentDeal, InvestmentRound, InvestorAction, RiskAssessment, CurrentInvestorStats, PossibleCapitalSource, Report, InvestorRequest
from funds.api.serializers import (
    FundSerializer, 
    FundLogSerializer, 
    ModelInputSerializer, 
    InvestmentDealSerializer,
    CurrentDealSerializer,
    InvestmentRoundSerializer,
    InvestorActionSerializer,
    RiskAssessmentSerializer,
    PossibleCapitalSourceSerializer,
    ReportSerializer,
    InvestorRequestSerializer
)
import math # Import math module
from django.contrib.auth import get_user_model
from funds.interfaces.user_service_adapter import UserServiceAdapter

user_adapter = UserServiceAdapter()
deal_service = DealService()
investor_service = InvestorService(user_adapter)

User = get_user_model()

class InvestorListView(APIView):
    """
    Lists all users who have the INVESTOR role.
    Used for the dropdown in Investor Action creation.
    Only Super Admins can access this.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        investors = user_adapter.get_investors()
        data = [{"id": str(u.id), "email": u.email, "first_name": u.first_name, "last_name": u.last_name} for u in investors]
        return Response(data)

class InvestorActionListView(APIView):
    """
    Handles listing and creating investor actions.
    Creation restricted to Super Admins.
    Listing shows all for superadmins, or only own for investors.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if PermissionService.is_super_admin(request.user):
            actions = InvestorAction.objects.all()
        else:
            actions = investor_selectors.get_investor_actions_by_investor(request.user)
        
        serializer = InvestorActionSerializer(actions, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Only super admins can create investor actions."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = InvestorActionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                investor_service.create_investor_action(
                    actor=request.user,
                    validated_data=serializer.validated_data,
                    ip_address=request.META.get("REMOTE_ADDR")
                )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class InvestorActionDetailView(APIView):
    """
    Handles updating and deleting specific investor actions.
    Restricted to Super Admins and SC members of the fund.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, action_id):
        action = investor_selectors.get_investor_action_by_id(action_id)
        if not action:
            return Response({"error": "Action not found."}, status=status.HTTP_404_NOT_FOUND)

        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, action.fund)):
            return Response({"error": "Only super admins and SC members can update investor actions."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = InvestorActionSerializer(action, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                investor_service.update_investor_action(
                    action_id=action_id,
                    actor=request.user,
                    data=serializer.validated_data,
                    ip_address=request.META.get("REMOTE_ADDR")
                )
                return Response(serializer.data)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, action_id):
        try:
            investor_service.delete_investor_action(
                action_id=action_id,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response({"message": "Investor action deleted."}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

class PossibleCapitalSourceListView(APIView):
    """
    Handles listing and creating possible capital sources for a fund.
    Creation restricted to Super Admins and SC members.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        sources = PossibleCapitalSource.objects.filter(fund=fund)
        serializer = PossibleCapitalSourceSerializer(sources, many=True)
        return Response(serializer.data)

    def post(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, fund)):
            return Response({"error": "Only super admins and SC members can add capital sources."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PossibleCapitalSourceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(fund=fund)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PossibleCapitalSourceDetailView(APIView):
    """
    Handles updating and deleting specific capital sources.
    Restricted to Super Admins and SC members.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, source_id):
        source = get_object_or_404(PossibleCapitalSource, id=source_id)
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, source.fund)):
            return Response({"error": "Only super admins and SC members can update capital sources."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PossibleCapitalSourceSerializer(source, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, source_id):
        source = get_object_or_404(PossibleCapitalSource, id=source_id)
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, source.fund)):
            return Response({"error": "Only super admins and SC members can delete capital sources."}, status=status.HTTP_403_FORBIDDEN)
        
        source.delete()
        return Response({"message": "Capital source deleted."}, status=status.HTTP_200_OK)

class InvestorDashboardView(APIView):
    """
    Calculates metrics for the Investor Dashboard.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        investor = request.user
        # In case a superadmin wants to see a specific investor's dashboard
        target_investor_id = request.query_params.get("investor_id")
        if target_investor_id and PermissionService.is_super_admin(investor):
            investor = get_object_or_404(User, id=target_investor_id)

        data = investor_selectors.calculate_dashboard_metrics(investor)

        return Response({
            "metrics": data["metrics"],
            "portfolio": data["portfolio_table"],
            "pie_chart": data["pie_chart_data"],
            "line_graph": data["line_graph_data"]
        })

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
        
        # Ensure model inputs exist
        model_inputs = fund_selectors.get_fund_model_input(fund)
        if not model_inputs:
             model_inputs, _ = ModelInput.objects.get_or_create(fund=fund)
             
        serializer = ModelInputSerializer(model_inputs)
        return Response(serializer.data)

    def put(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            model_inputs = FundService.update_model_input(actor=request.user, fund=fund, data=request.data)
            return Response(ModelInputSerializer(model_inputs).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InvestmentDealListView(APIView):
    """
    Handles listing and creating investment deals for a specific fund.
    View access is open to all fund members; creation is restricted to SC and Admins.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deals = deal_selectors.get_deals_for_fund(fund)
        serializer = InvestmentDealSerializer(deals, many=True)
        return Response(serializer.data)

    def post(self, request, fund_id):
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = InvestmentDealSerializer(data=request.data)
        if serializer.is_valid():
            deal_service.create_investment_deal(
                fund=fund,
                actor=request.user,
                data=serializer.validated_data,
                ip_address=request.META.get("REMOTE_ADDR")
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
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = InvestmentDealSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            try:
                deal_service.update_investment_deal(
                    deal_id=deal_id,
                    actor=request.user,
                    data=serializer.validated_data,
                    ip_address=request.META.get("REMOTE_ADDR")
                )
                return Response(serializer.data)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, fund_id, deal_id):
        """
        Deletes a specific investment deal.
        Restricted to Super Admins and Fund Steering Committee members.
        """
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            deal_service.delete_investment_deal(
                deal_id=deal_id,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response({"message": "Deal deleted."}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class CurrentDealListView(APIView):
    """
    Handles listing and creating current deals (deals already made) for a specific fund.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deals = deal_selectors.get_current_deals_for_fund(fund)
        serializer = CurrentDealSerializer(deals, many=True)
        return Response(serializer.data)

    def post(self, request, fund_id):
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = CurrentDealSerializer(data=request.data)
        if serializer.is_valid():
            deal_service.create_current_deal(
                fund=fund,
                actor=request.user,
                data=serializer.validated_data,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentDealDetailView(APIView):
    """
    Handles updating and deleting specific current deals.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, fund_id, deal_id):
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = CurrentDealSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            try:
                deal_service.update_current_deal(
                    deal_id=deal_id,
                    actor=request.user,
                    data=serializer.validated_data,
                    ip_address=request.META.get("REMOTE_ADDR")
                )
                return Response(serializer.data)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, fund_id, deal_id):
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if fund.status == "DEACTIVATED" and not PermissionService.is_super_admin(request.user):
             return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            deal_service.delete_current_deal(
                deal_id=deal_id,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response({"message": "Current deal deleted."}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class InvestmentRoundListView(APIView):
    """
    Handles listing and creating investment rounds for a company.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        company_name = request.query_params.get("company_name")
        if not company_name:
            # If no company name provided, return all rounds for the fund
            rounds = deal_selectors.get_rounds_for_fund(fund)
        else:
            rounds = deal_selectors.get_rounds_for_fund(fund).filter(company_name=company_name)

        serializer = InvestmentRoundSerializer(rounds, many=True)
        return Response(serializer.data)

    def post(self, request, fund_id):
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        serializer = InvestmentRoundSerializer(data=request.data)
        if serializer.is_valid():
            try:
                deal_service.create_investment_round(
                    fund=fund,
                    actor=request.user,
                    data=serializer.validated_data,
                    ip_address=request.META.get("REMOTE_ADDR")
                )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class InvestmentRoundDetailView(APIView):
    """
    Handles updating and deleting specific investment rounds.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, fund_id, round_id):
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = InvestmentRoundSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            try:
                deal_service.update_investment_round(
                    round_id=round_id,
                    actor=request.user,
                    data=serializer.validated_data,
                    ip_address=request.META.get("REMOTE_ADDR")
                )
                return Response(serializer.data)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, fund_id, round_id):
        fund = fund_selectors.get_fund_by_id(fund_id)
        if not fund:
            return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            deal_service.delete_investment_round(
                round_id=round_id,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response({"message": "Round deleted."}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class RiskAssessmentListView(APIView):
    """
    Handles listing and upserting risk assessments for a specific fund.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        assessments = risk_assessment_selectors.get_risk_assessments_for_fund(fund)
        serializer = RiskAssessmentSerializer(assessments, many=True)
        return Response(serializer.data)

    def post(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        try:
            results = RiskAssessmentService.batch_upsert_risk_assessments(fund=fund, data=request.data)
            serializer = RiskAssessmentSerializer(results, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FundListView(APIView):


    """
    Lists funds accessible to the user or creates new funds (Super Admin only).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """ List all funds for admins, or funds where the user has a role. """
        funds = fund_selectors.get_funds_for_user(request.user)
        serializer = FundSerializer(funds, many=True)
        return Response(serializer.data)

    def post(self, request):
        """ Create a new fund. Only Super Admins. """
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Only super admins can create funds."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            fund = FundService.create_fund(actor=request.user, data=request.data)
            return Response(FundSerializer(fund).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            fund = FundService.update_fund(actor=request.user, fund=fund, data=request.data)
            return Response(FundSerializer(fund).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, fund_id):
        """ Deactivate fund. Only Super Admin or SC. """
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        FundService.deactivate_fund(actor=request.user, fund=fund)
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

def get_fund_performance_data(fund):
    """
    Common logic to calculate fund performance metrics and tables.
    Returns a dictionary of all performance data or None if model inputs are missing.
    """
    deals = fund.deals.all()
    current_deals = fund.current_deals.all()
    model_inputs = getattr(fund, "model_inputs", None)
    
    if not model_inputs:
        return None

    inception_year = int(model_inputs.inception_year)
    fund_life = int(model_inputs.fund_life)
    fund_end_year = inception_year + fund_life
    current_year = datetime.now().year
    historical_final_year = current_year - 1

    # 1. Deal Prognosis Metrics
    p_injections_by_year = deal_selectors.get_prognosis_injections(fund)
    
    total_expected_pro_rata = sum(float(deal_selectors.calculate_investment_deal_expected_pro_rata_investments(deal)) for deal in deals)
    total_invested_float = float(sum(deal.amount_invested for deal in deals)) + total_expected_pro_rata
    
    gross_exit_value = sum(float(deal_selectors.calculate_investment_deal_exit_value(deal)) for deal in deals)
    gross_exit_value_future = sum(float(deal_selectors.calculate_investment_deal_exit_value(deal)) for deal in deals if deal.entry_year >= current_year)
    
    p_injections_future = {yr: amt for yr, amt in p_injections_by_year.items() if yr >= current_year}
    p_solver_injections = p_injections_future if p_injections_future else p_injections_by_year
    irr = calculators.solve_implied_return_rate(p_solver_injections, fund_end_year, gross_exit_value_future)

    # 2. Current Deals Metrics
    c_injections_by_year = deal_selectors.get_current_injections(fund)
    
    c_total_invested_float = float(sum(d.amount_invested for d in current_deals))
    c_gross_exit_value = sum(deal_selectors.calculate_current_deal_final_exit_amount(d) for d in current_deals)
    c_irr = calculators.solve_implied_return_rate(c_injections_by_year, historical_final_year, c_gross_exit_value)

    # MOIC and Carry Logic
    p_tier1_moic = float(model_inputs.least_expected_moic_tier_1)
    p_tier2_moic = float(model_inputs.least_expected_moic_tier_2)
    
    def calculate_metrics(gev, total_inv, tier1, tier2, model_inputs):
        moic = gev / total_inv if total_inv > 0 else 0
        if moic < tier1: cp = 0.0
        elif moic < tier2: cp = float(model_inputs.tier_1_carry)
        else: cp = float(model_inputs.tier_2_carry)
        profit = gev - total_inv
        ca = profit * (cp / 100.0) if profit > 0 else 0
        fe = total_inv * (float(model_inputs.management_fee) / 100.0)
        net = gev - (fe + ca)
        real_moic = net / total_inv if total_inv > 0 else 0
        return moic, cp, ca, fe, net, real_moic

    moic, _, _, _, _, p_real_moic = calculate_metrics(gross_exit_value, total_invested_float, p_tier1_moic, p_tier2_moic, model_inputs)
    c_moic, c_carry_pct, c_carry_amount, c_total_fees, c_net_to_investors, c_real_moic = calculate_metrics(c_gross_exit_value, c_total_invested_float, p_tier1_moic, p_tier2_moic, model_inputs)

    # 3. Performance Table
    all_entry_years = [d.entry_year for d in deals] + [d.entry_year for d in current_deals]
    start_year = min(inception_year, min(all_entry_years)) if all_entry_years else inception_year
    end_year = fund_end_year - 1

    safe_c_irr = c_irr if c_irr and c_irr > -1 else 0.0
    safe_p_irr = irr if irr and irr > -1 else 0.0

    trajectory = calculators.calculate_nav_trajectory(
        start_year, end_year, current_year, fund_end_year,
        c_injections_by_year, p_injections_by_year,
        safe_c_irr, safe_p_irr,
        is_future=(fund.status == "FUTURE"),
        target_appreciation=fund.target_appreciation
    )

    current_deals_by_year = {}
    for d in current_deals: current_deals_by_year.setdefault(d.entry_year, []).append(d)
    prognosis_deals_by_year = {}
    for d in deals: prognosis_deals_by_year.setdefault(d.entry_year, []).append(d)
    
    performance_table = []
    cum_inj_no_p = 0.0
    cum_inj_with_p = 0.0
    cum_deals_c = 0
    cum_deals_total = 0

    for point in trajectory:
        year = point["year"]
        year_c_deals = current_deals_by_year.get(year, [])
        year_p_deals = prognosis_deals_by_year.get(year, [])
        
        cum_inj_no_p += point["c_inj"] if year <= current_year else 0
        cum_inj_with_p += point["c_inj"] + point["p_inj"]
        cum_deals_c += len(year_c_deals) if year <= current_year else 0
        cum_deals_total += len(year_c_deals) + len(year_p_deals)
        
        performance_table.append({
            "year": year,
            "total_portfolio_value_with_prognosis": point["c_pv"] + point["p_pv"],
            "total_portfolio_value_no_prognosis": point["c_pv"],
            "injection_current": point["c_inj"],
            "injection_prognosis": point["p_inj"],
            "appreciation_current": point["c_appr"],
            "appreciation_prognosis": point["p_appr"],
            "deals_count_current": len(year_c_deals),
            "deals_count_prognosis": len(year_p_deals),
            "current_year": current_year,
            "is_future": year > current_year,
            "cumulative_injection_no_prognosis": cum_inj_no_p,
            "cumulative_injection_with_prognosis": cum_inj_with_p,
            "cumulative_deals_count_current": cum_deals_c,
            "cumulative_deals_count_prognosis": cum_deals_total,
            "irr": point.get("irr", 0.0)
        })

    # Aggregated Exits (Current Deals)
    cases = [{"name": "Base Case", "m": 1.0}, {"name": "Upside Case", "m": 1.2}, {"name": "High Growth Case", "m": 1.5}]
    aggregated_exits = []
    for case in cases:
        case_gev = c_gross_exit_value * case["m"]
        m, cp, ca, fe, net, rm = calculate_metrics(case_gev, c_total_invested_float, p_tier1_moic, p_tier2_moic, model_inputs)
        aggregated_exits.append({
            "case": case["name"], "gev": case_gev, "profit_before_carry": case_gev - c_total_invested_float, 
            "gross_moic": m, "carry_pct": cp, "carry_amount": ca, "total_fees": fe, "net_to_investors": net,
            "real_moic": rm,
            "irr": calculators.solve_implied_return_rate(c_injections_by_year, historical_final_year, case_gev)
        })

    # End of Life Exits (Full Fund: Current + Prognosis)
    # GEV base at EOL is the total portfolio value at fund_end_year from the trajectory
    eol_point = next((p for p in trajectory if p["year"] == fund_end_year), trajectory[-1] if trajectory else None)
    total_expected_gev_at_eol = (eol_point["c_pv"] + eol_point["p_pv"]) if eol_point else 0.0
    total_invested_all = c_total_invested_float + total_invested_float
    
    # Combined injections for IRR
    all_injections = c_injections_by_year.copy()
    for yr, amt in p_injections_by_year.items():
        all_injections[yr] = all_injections.get(yr, 0.0) + amt

    end_of_life_exits = []
    for case in cases:
        case_gev = total_expected_gev_at_eol * case["m"]
        m, cp, ca, fe, net, rm = calculate_metrics(case_gev, total_invested_all, p_tier1_moic, p_tier2_moic, model_inputs)
        end_of_life_exits.append({
            "case": case["name"], "gev": case_gev, "profit_before_carry": case_gev - total_invested_all, 
            "gross_moic": m, "carry_pct": cp, "carry_amount": ca, "total_fees": fe, "net_to_investors": net,
            "real_moic": rm,
            "irr": calculators.solve_implied_return_rate(all_injections, fund_end_year, case_gev)
        })

    deals_data = InvestmentDealSerializer(deals, many=True).data
    c_deals_data = CurrentDealSerializer(current_deals, many=True).data

    return {
        "dashboard": {
            "total_invested": total_invested_float, "gross_exit_value": gross_exit_value,
            "moic": moic, "irr": irr, "real_moic": p_real_moic,
            "total_deals": fund.deals.count(), "performance_table": performance_table,
            "current_year": current_year
        },
        "current_deals_metrics": {
            "total_invested": c_total_invested_float, "gross_exit_value": c_gross_exit_value,
            "moic": c_moic, "irr": c_irr, "real_moic": c_real_moic,
            "total_deals": fund.current_deals.count(),
            "total_companies": fund.current_deals.values('company_name').distinct().count()
        },
        "aggregated_exits": aggregated_exits,
        "end_of_life_exits": end_of_life_exits,
        "admin_fee": {
            "total_admin_cost": (float(model_inputs.admin_cost) / 100.0) * float(model_inputs.target_fund_size),
            "operations_fee": (float(model_inputs.management_fee) / 100.0) * float(model_inputs.target_fund_size),
            "management_fees": (float(model_inputs.management_fee) / 100.0) * float(model_inputs.target_fund_size) * fund_life,
            "total_costs": 0, "inception_year": inception_year, "fund_life": fund_life,
            "investment_period": model_inputs.investment_period,
            "lock_up_period": model_inputs.lock_up_period,
            "failure_rate": float(model_inputs.failure_rate),
            "break_even_rate": float(model_inputs.break_even_rate),
            "high_growth_rate": float(model_inputs.high_growth_rate),
            "dilution_rate": float(model_inputs.dilution_rate),
        },
        "fund_details": {
            "name": fund.name,
            "tag": fund.tag,
            "sharia_compliant": fund.sharia_compliant,
            "region": fund.region,
            "focus": fund.focus,
            "strategy": fund.strategy,
            "structure": fund.structure,
            "risk_measures": fund.risk_measures,
        },
        "investment_deals": deals_data,
        "current_deals": c_deals_data
    }

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
        
        data = get_fund_performance_data(fund)
        if data is None:
            return Response({"error": "Model inputs not found for this fund."}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate total costs for admin fee
        data["admin_fee"]["total_costs"] = (
            data["admin_fee"]["total_admin_cost"] + 
            data["admin_fee"]["operations_fee"] + 
            data["admin_fee"]["management_fees"]
        )
        return Response(data)

class InvestorLogView(APIView):
    """
    Provides data for the Investor Log tab:
    - Table of investors with their total investment and ownership percentage.
    - Graph comparing cumulative capital invested vs. capital required over the fund's life.
    Only accessible by Super Admins and Steering Committee (SC) members.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        
        # Access control: Super Admin or SC Member
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, fund)):
            return Response({"error": "Access denied. Only Super Admins and SC members can view this data."}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        model_inputs = getattr(fund, "model_inputs", None)
        if not model_inputs:
            return Response({"error": "Model inputs not found for this fund."}, status=status.HTTP_400_BAD_REQUEST)

        inception_year = int(model_inputs.inception_year)
        fund_life = int(model_inputs.fund_life)
        end_year = inception_year + fund_life - 1
        
        # 1. Investor Table Data
        investor_actions = InvestorAction.objects.filter(fund=fund).select_related('investor')
        investor_data = {}

        total_fund_units = float(fund.total_units)

        for action in investor_actions:
            investor_id = str(action.investor.id)
            if investor_id not in investor_data:
                investor_data[investor_id] = {
                    "first_name": action.investor.first_name,
                    "last_name": action.investor.last_name,
                    "email": action.investor.email,
                    "units": 0.0
                }

            if action.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
                investor_data[investor_id]["units"] += float(action.units)
            elif action.type == "SECONDARY_EXIT":
                investor_data[investor_id]["units"] -= float(action.units)

        investors_list = []
        for inv_id, data in investor_data.items():
            ownership_pct = (data["units"] / total_fund_units * 100.0) if total_fund_units > 0 else 0.0
            investors_list.append({
                **data,
                "ownership_percentage": ownership_pct
            })

        # 2. Graph Data
        # X-axis: Years of fund life
        graph_data = []

        # Pre-calculate required capital by year (Deals)
        required_by_year = {}

        # Past Deals (CurrentDeal)
        current_deals = fund.current_deals.all()
        for deal in current_deals:
            yr = deal.entry_year
            required_by_year[yr] = required_by_year.get(yr, 0.0) + float(deal.amount_invested)

        # Future Deals (InvestmentDeal)
        future_deals = fund.deals.all()
        # We need the serializer to get expected_pro_rata_investments
        future_deals_serialized = InvestmentDealSerializer(future_deals, many=True).data
        future_deals_lookup = {d["id"]: d for d in future_deals_serialized}

        for deal in future_deals:
            yr = deal.entry_year
            required_by_year[yr] = required_by_year.get(yr, 0.0) + float(deal.amount_invested)

            # Distribute future pro-rata expectations
            if deal.pro_rata_rights and deal.expected_number_of_rounds > 0:
                d_data = future_deals_lookup.get(str(deal.id))
                if d_data:
                    total_pro_rata = float(d_data.get("expected_pro_rata_investments", 0))
                    round_amt = total_pro_rata / deal.expected_number_of_rounds
                    for i in range(1, deal.expected_number_of_rounds + 1):
                        pro_rata_yr = deal.entry_year + i
                        required_by_year[pro_rata_yr] = required_by_year.get(pro_rata_yr, 0.0) + round_amt

        # Pre-calculate invested capital by year (Investor Actions)
        invested_by_year = {}
        for action in investor_actions:
            yr = action.year
            # Only count primary investments for "Capital Invested" in the fund
            if action.type == "PRIMARY_INVESTMENT":
                amount = float(action.amount) if action.amount else 0.0
                invested_by_year[yr] = invested_by_year.get(yr, 0.0) + amount

        # Pre-calculate possible capital sources by year
        possible_sources = PossibleCapitalSource.objects.filter(fund=fund)
        possible_by_year = {}
        for source in possible_sources:
            yr = source.year
            amount = float(source.amount)
            possible_by_year[yr] = possible_by_year.get(yr, 0.0) + amount

        # Pre-calculate units by year (only primary investments increase fund total units)
        primary_units_by_year = {}
        for action in investor_actions:
            if action.type == "PRIMARY_INVESTMENT":
                yr = action.year
                primary_units_by_year[yr] = primary_units_by_year.get(yr, 0.0) + float(action.units)

        cumulative_invested = 0.0
        cumulative_required = 0.0
        cumulative_possible = 0.0
        cumulative_units = 0.0

        for yr in range(inception_year, end_year + 1):
            cumulative_invested += invested_by_year.get(yr, 0.0)
            cumulative_required += required_by_year.get(yr, 0.0)
            cumulative_possible += possible_by_year.get(yr, 0.0)
            cumulative_units += primary_units_by_year.get(yr, 0.0)
            
            # Get actual portfolio value for this year
            portfolio_val = fund_selectors.get_total_fund_portfolio(fund, yr)

            graph_data.append({
                "year": yr,
                "total_capital_invested": cumulative_invested,
                "total_capital_required": cumulative_required,
                "total_capital_with_possible": cumulative_invested + cumulative_possible,
                "portfolio_value": portfolio_val,
                "units_at_year": cumulative_units,
                "price_per_unit": (portfolio_val / cumulative_units) if cumulative_units > 0 else 0
            })

        # 3. Company Stage Data (for Equity Cap Table)
        stage_data = {}
        # Current deals
        for deal in current_deals:
            stage = deal.company_type or "Unknown"
            stage_data[stage] = stage_data.get(stage, 0.0) + float(deal.amount_invested)
        # Future deals
        for deal in future_deals:
            stage = deal.company_type or "Unknown"
            stage_data[stage] = stage_data.get(stage, 0.0) + float(deal.amount_invested)
            
        stage_list = [{"name": name, "value": val} for name, val in stage_data.items()]

        return Response({
            "investors": investors_list,
            "graph_data": graph_data,
            "actions": InvestorActionSerializer(investor_actions, many=True).data,
            "possible_capital_sources": PossibleCapitalSourceSerializer(possible_sources, many=True).data,
            "total_units": total_fund_units,
            "stage_data": stage_list
        })

class ReportListView(APIView):
    """
    Handles listing and creating dynamic reports.
    Access restricted to Super Admins and SC Members.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reports = report_selectors.get_reports_by_type(request.user, report_type="DYNAMIC")
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Default to DYNAMIC if not specified
        data = request.data.copy()
        if "report_type" not in data:
            data["report_type"] = "DYNAMIC"
            
        try:
            # We don't use serializer.save here, we use ReportService
            # But we still need to validate fund permissions
            from funds.api.serializers import ReportSerializer
            temp_serializer = ReportSerializer(data=data)
            temp_serializer.is_valid(raise_exception=True)
            fund = temp_serializer.validated_data["fund"]
            
            if not (PermissionService.is_super_admin(request.user) or 
                    PermissionService.is_sc_member(request.user, fund)):
                return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            
            report = ReportService.create_report(
                actor=request.user,
                data=data,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            
            # Trigger initial generation
            ReportService.regenerate_report(actor=request.user, report=report)
            
            return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CapitalCallReportListView(APIView):
    """
    Specialized view for Capital Call Reports.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reports = report_selectors.get_reports_by_type(request.user, report_type="CAPITAL_CALL")
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        data["report_type"] = "CAPITAL_CALL"
        
        try:
            from funds.api.serializers import ReportSerializer
            temp_serializer = ReportSerializer(data=data)
            temp_serializer.is_valid(raise_exception=True)
            fund = temp_serializer.validated_data["fund"]
            
            if not (PermissionService.is_super_admin(request.user) or 
                    PermissionService.is_sc_member(request.user, fund)):
                return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
                
            report = ReportService.create_report(
                actor=request.user,
                data=data,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            ReportService.regenerate_report(actor=request.user, report=report)
            return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ReportDetailView(APIView):
    """
    Handles updating and deleting specific reports.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, report_id):
        report = report_selectors.get_report_by_id(report_id)
        if not report:
             return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
             
        if not PermissionService.can_view_fund(request.user, report.fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        return Response(ReportSerializer(report).data)

    def patch(self, request, report_id):
        report = report_selectors.get_report_by_id(report_id)
        if not report:
             return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
             
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, report.fund)):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            report = ReportService.update_report(
                actor=request.user,
                report=report,
                data=request.data,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response(ReportSerializer(report).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, report_id):
        report = report_selectors.get_report_by_id(report_id)
        if not report:
             return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
             
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, report.fund)):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        ReportService.delete_report(
            actor=request.user,
            report=report,
            ip_address=request.META.get("REMOTE_ADDR")
        )
        return Response({"message": "Report deleted."}, status=status.HTTP_200_OK)

class ReportRegenerateView(APIView):
    """
    Manually trigger report regeneration.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, report_id):
        report = report_selectors.get_report_by_id(report_id)
        if not report:
             return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
             
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, report.fund)):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        report = ReportService.regenerate_report(
            actor=request.user,
            report=report,
            ip_address=request.META.get("REMOTE_ADDR")
        )
        return Response(ReportSerializer(report).data)

from django.http import HttpResponse
from funds.security import SecurityScanner
from funds.ingestion import ExcelIngestService

class ExcelTemplateView(APIView):
    """
    Generates and returns a downloadable Excel template for a specific fund.
    Only Super Admins and SC members of the fund can access.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, fund)):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        template_output = ExcelIngestService.generate_template(fund)
        
        response = HttpResponse(
            template_output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="fund_{fund.name}_template.xlsx"'
        return response

class ExcelIngestView(APIView):
    """
    Handles Excel file upload, security scanning, and data ingestion.
    Only Super Admins and SC members of the fund can access.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, fund)):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 1. Security Scan
        is_safe, error_msg, threat_type = SecurityScanner.scan_file(uploaded_file, request.user)
        if not is_safe:
            # Audit the threat
            AuditService.log(
                actor=request.user,
                action="SECURITY_THREAT_DETECTED",
                fund=fund,
                metadata={"threat_type": threat_type, "error": error_msg},
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response({"error": error_msg, "threat_type": threat_type}, status=status.HTTP_403_FORBIDDEN)
        
        # 2. Ingest Data
        success, result = ExcelIngestService.ingest_data(fund, uploaded_file, request.user)
        
        if success:
            AuditService.log(
                actor=request.user,
                action="EXCEL_INGESTION_SUCCESS",
                fund=fund,
                metadata=result,
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response({
                "message": "Data ingested successfully.",
                "details": result
            }, status=status.HTTP_200_OK)
        else:
            # result contains errors (list or string)
            AuditService.log(
                actor=request.user,
                action="EXCEL_INGESTION_FAILED",
                fund=fund,
                metadata={"errors": result},
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response({
                "error": "Ingestion failed.",
                "details": result
            }, status=status.HTTP_400_BAD_REQUEST)

class PublicReportView(APIView):

    """
    Endpoint for public access to reports via slug.
    Validates that report is ACTIVE.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        report = get_object_or_404(Report, slug=slug)
        
        if report.status != "ACTIVE":
            from rest_framework_simplejwt.authentication import JWTAuthentication
            auth = JWTAuthentication().authenticate(request)
            if not auth or not (PermissionService.is_super_admin(auth[0]) or 
                                PermissionService.is_sc_member(auth[0], report.fund)):
                return Response({"error": "Report is not active or available."}, status=status.HTTP_403_FORBIDDEN)
        
        # Include performance data in the response
        performance_data = get_fund_performance_data(report.fund)
        
        data = ReportSerializer(report).data
        data["performance_data"] = performance_data
        
        return Response(data)

class InvestorRequestListView(APIView):
    """
    Investors can view their own requests and submit new ones.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requests = InvestorRequest.objects.filter(user=request.user)
        serializer = InvestorRequestSerializer(requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = InvestorRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class InvestorHoldingsView(APIView):
    """
    Returns funds where the user has active holdings, 
    including metrics needed for the liquidation UI.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Find all funds where this investor has actions
        fund_ids = InvestorAction.objects.filter(investor=request.user).values_list('fund_id', flat=True).distinct()
        funds = Fund.objects.filter(id__in=fund_ids)
        
        current_year = datetime.now().year
        holdings_data = []

        for fund in funds:
            # Get stats for this investor in this fund
            stats = CurrentInvestorStats.objects.filter(investor=request.user, fund=fund).first()
            if not stats or stats.units <= 0:
                continue

            model_inputs = getattr(fund, "model_inputs", None)
            if not model_inputs:
                continue

            total_fund_units = fund_selectors.get_total_units_at_year(fund, current_year)
            total_portfolio_value = fund_selectors.get_total_fund_portfolio(fund, current_year)
            
            price_per_unit = float(total_portfolio_value / total_fund_units) if total_fund_units > 0 else 1.0
            
            # Liquidity Index (simplified lookup from performance data or calculated)
            current_deals = fund.current_deals.all()
            li_data = calculateLiquidityIndex(current_deals, model_inputs.inception_year, model_inputs.fund_life)
            li_index = li_data['finalLI'] if li_data else 0

            # Lockup Logic
            inception_year = model_inputs.inception_year
            lockup_period = model_inputs.lock_up_period
            is_locked_for_liquidation = current_year < (inception_year + lockup_period)
            is_locked_for_investment = False # Lockup period does not matter for investment

            # Calculate ownership percentage
            ownership_percentage = (float(stats.units) / total_fund_units * 100) if total_fund_units > 0 else 0.0

            holdings_data.append({
                "fund_id": fund.id,
                "fund_name": fund.name,
                "units_owned": float(stats.units),
                "ownership_percentage": ownership_percentage,
                "price_per_unit": price_per_unit,
                "total_value": float(stats.units) * price_per_unit,
                "liquidity_index": li_index,
                "is_locked": is_locked_for_liquidation,
                "is_locked_for_liquidation": is_locked_for_liquidation,
                "is_locked_for_investment": is_locked_for_investment,
                "lockup_until": inception_year + lockup_period,
                "min_ticket": float(model_inputs.min_investor_ticket)
            })

        return Response(holdings_data)
