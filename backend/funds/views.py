from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Fund, FundLog, ModelInput, InvestmentDeal, CurrentDeal, InvestmentRound, InvestorAction, RiskAssessment
from .serializers import (
    FundSerializer, 
    FundLogSerializer, 
    ModelInputSerializer, 
    InvestmentDealSerializer,
    CurrentDealSerializer,
    InvestmentRoundSerializer,
    InvestorActionSerializer,
    RiskAssessmentSerializer
)
import math # Import math module
from django.contrib.auth import get_user_model

from django.contrib.auth import get_user_model

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
        
        from users.models import UserRoleAssignment, Role
        investor_role = Role.objects.get(name="INVESTOR")
        investor_ids = UserRoleAssignment.objects.filter(role=investor_role).values_list("user_id", flat=True).distinct()
        investors = User.objects.filter(id__in=investor_ids)
        
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
            actions = InvestorAction.objects.filter(investor=request.user)
        
        serializer = InvestorActionSerializer(actions, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Only super admins can create investor actions."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = InvestorActionSerializer(data=request.data)
        if serializer.is_valid():
            action = serializer.save()
            
            # Log the change
            FundLog.objects.create(
                actor=request.user,
                target_fund=action.fund,
                action="INVESTOR_ACTION_CREATED",
                metadata={"action_id": str(action.id), "type": action.type, "investor": action.investor.email}
            )
            AuditService.log(
                actor=request.user,
                action="INVESTOR_ACTION_CREATED",
                fund=action.fund,
                target_user=action.investor,
                metadata={"action_id": str(action.id), "type": action.type},
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class InvestorActionDetailView(APIView):
    """
    Handles updating and deleting specific investor actions.
    Restricted to Super Admins.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, action_id):
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Only super admins can update investor actions."}, status=status.HTTP_403_FORBIDDEN)
        
        action = get_object_or_404(InvestorAction, id=action_id)
        serializer = InvestorActionSerializer(action, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Log the change
            FundLog.objects.create(
                actor=request.user,
                target_fund=action.fund,
                action="INVESTOR_ACTION_UPDATED",
                metadata={"action_id": str(action.id), "type": action.type, "investor": action.investor.email}
            )
            AuditService.log(
                actor=request.user,
                action="INVESTOR_ACTION_UPDATED",
                fund=action.fund,
                target_user=action.investor,
                metadata={"action_id": str(action.id), "type": action.type},
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, action_id):
        if not PermissionService.is_super_admin(request.user):
            return Response({"error": "Only super admins can delete investor actions."}, status=status.HTTP_403_FORBIDDEN)
        
        action = get_object_or_404(InvestorAction, id=action_id)
        action_id_str = str(action.id)
        action_type = action.type
        investor_email = action.investor.email
        fund = action.fund
        target_user = action.investor
        action.delete()
        
        # Log the change
        FundLog.objects.create(
            actor=request.user,
            target_fund=fund,
            action="INVESTOR_ACTION_DELETED",
            metadata={"action_id": action_id_str, "type": action_type, "investor": investor_email}
        )
        AuditService.log(
            actor=request.user,
            action="INVESTOR_ACTION_DELETED",
            fund=fund,
            target_user=target_user,
            metadata={"action_id": action_id_str, "type": action_type},
            ip=request.META.get("REMOTE_ADDR")
        )
        return Response({"message": "Investor action deleted."}, status=status.HTTP_200_OK)

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

        actions = InvestorAction.objects.filter(investor=investor).select_related('fund')
        
        # Group actions by fund
        fund_data = {}
        for action in actions:
            fund_id = str(action.fund.id)
            if fund_id not in fund_data:
                fund_data[fund_id] = {
                    "fund": action.fund,
                    "investments": [],
                    "exits": []
                }
            if action.type == "CAPITAL_INVESTMENT":
                fund_data[fund_id]["investments"].append(action)
            else:
                fund_data[fund_id]["exits"].append(action)

        total_capital_deployed = 0.0
        total_realized_gains = 0.0
        total_original_value_exited = 0.0
        total_exit_value = 0.0
        total_current_portfolio_value = 0.0
        
        portfolio_table = []
        pie_chart_data = []

        # We need fund performance to get IRRs and current values
        for fund_id, data in fund_data.items():
            fund = data["fund"]
            investments = data["investments"]
            exits = data["exits"]
            
            fund_invested = sum(float(i.amount) for i in investments)
            fund_exits_original = sum(float(e.original_value) for e in exits)
            fund_exits_value = sum(float(e.exit_value) for e in exits)
            
            net_fund_deployed = fund_invested - fund_exits_value
            total_capital_deployed += net_fund_deployed
            
            fund_realized_gain = fund_exits_value - fund_exits_original
            total_realized_gains += fund_realized_gain
            total_original_value_exited += fund_exits_original
            total_exit_value += fund_exits_value
            
            # Remaining cost basis for this investor in this fund
            remaining_cost_basis = fund_invested - fund_exits_original
            
            # Calculate ownership in the fund
            fund_total_invested = sum(d.amount_invested for d in fund.current_deals.all())
            fund_total_current_val = 0.0
            
            c_deal_serializer = CurrentDealSerializer(fund.current_deals.all(), many=True)
            for d in c_deal_serializer.data:
                fund_total_current_val += float(d["final_exit_amount"])
            
            ownership_pct = 0.0
            if fund_total_invested > 0:
                ownership_pct = (remaining_cost_basis / float(fund_total_invested)) * 100.0
            
            current_val_in_fund = (ownership_pct / 100.0) * fund_total_current_val
            total_current_portfolio_value += current_val_in_fund
            
            portfolio_table.append({
                "fund_name": fund.name,
                "ownership_pct": ownership_pct,
                "current_value": current_val_in_fund,
                "net_deployed": net_fund_deployed
            })
            
            pie_chart_data.append({
                "name": fund.name,
                "value": current_val_in_fund
            })

        unrealized_gains = total_current_portfolio_value - total_capital_deployed
        
        realized_multiple = 0.0
        if total_original_value_exited > 0:
            realized_multiple = total_exit_value / total_original_value_exited
            
        unrealized_multiple = 0.0
        if total_capital_deployed > 0:
            unrealized_multiple = total_current_portfolio_value / total_capital_deployed

        # Line Graph Logic & Historical Breakdown
        years = sorted(list(set(a.year for a in actions)))
        if not years:
            line_graph_data = []
        else:
            start_year = min(years)
            current_year = datetime.now().year
            end_year = max(current_year, max(years))
            
            line_graph_data = []
            
            # For each year, we need to calculate the portfolio value
            # by summing the investor's ownership value in each fund at that point.
            # Pre-calculate fund performance tables
            fund_performance_tables = {}
            for fid, f_data in fund_data.items():
                perf_table, _ = FundPerformanceView.get_performance_table(f_data["fund"])
                if perf_table:
                    # Map by year for easy access
                    fund_performance_tables[fid] = {row["year"]: row for row in perf_table}

            for yr in range(start_year, end_year + 1):
                yr_total_value = 0.0
                yr_total_injection = 0.0
                
                for fid, f_data in fund_data.items():
                    fund = f_data["fund"]
                    # 1. Total capital invested by investor in this fund UP TO yr (cost basis)
                    f_invested_up_to_yr = sum(float(i.amount) for i in f_data["investments"] if i.year <= yr)
                    f_exits_orig_up_to_yr = sum(float(e.original_value) for e in f_data["exits"] if e.year <= yr)
                    
                    remaining_basis = f_invested_up_to_yr - f_exits_orig_up_to_yr
                    if remaining_basis < 0: remaining_basis = 0
                    
                    # 2. Fund state at yr from pre-calculated performance table
                    fund_perf = fund_performance_tables.get(fid, {}).get(yr)
                    if fund_perf:
                        fund_total_val_at_yr = float(fund_perf["total_portfolio_value_with_prognosis"])
                        
                        # Calculate total fund invested (cost basis) up to that year to determine ownership
                        # We need to sum up all injections in the fund performance table up to that year
                        fund_perf_table = fund_performance_tables.get(fid, {})
                        fund_total_invested_at_yr = sum(
                            float(fund_perf_table[y]["injection_current"] + fund_perf_table[y]["injection_prognosis"])
                            for y in range(min(fund_perf_table.keys()), yr + 1)
                        )
                        
                        f_ownership_pct_at_yr = 0.0
                        if fund_total_invested_at_yr > 0:
                            f_ownership_pct_at_yr = (remaining_basis / fund_total_invested_at_yr) * 100.0
                        
                        yr_total_value += (f_ownership_pct_at_yr / 100.0) * fund_total_val_at_yr
                    
                    # Tracking injections for this year specifically for the table
                    yr_total_injection += sum(float(i.amount) for i in f_data["investments"] if i.year == yr)
                    yr_total_injection -= sum(float(e.exit_value) for e in f_data["exits"] if e.year == yr)

                prev_val = line_graph_data[-1]["value"] if line_graph_data else 0
                yoy_gain = 0.0
                if prev_val > 0:
                    yoy_gain = ((yr_total_value / prev_val) - 1) * 100

                line_graph_data.append({
                    "year": yr,
                    "value": yr_total_value,
                    "injection": yr_total_injection,
                    "yoy_gain": yoy_gain if line_graph_data else None # N/A for first year
                })

        return Response({
            "metrics": {
                "total_capital_deployed": total_capital_deployed,
                "realized_gains": total_realized_gains,
                "unrealized_gains": unrealized_gains,
                "realized_multiple": realized_multiple,
                "unrealized_multiple": unrealized_multiple,
            },
            "portfolio": portfolio_table,
            "pie_chart": pie_chart_data,
            "line_graph": line_graph_data
        })
from users.services.permission_service import PermissionService
from users.services.audit_service import AuditService
from datetime import datetime


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


class RiskAssessmentListView(APIView):
    """
    Handles listing and upserting risk assessments for a specific fund.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        assessments = fund.risk_assessments.all()
        serializer = RiskAssessmentSerializer(assessments, many=True)
        return Response(serializer.data)

    def post(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_edit_fund(request.user, fund):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        if not isinstance(data, list):
            data = [data]

        results = []
        for item in data:
            company_name = item.get("company_name")
            if not company_name:
                continue

            assessment, created = RiskAssessment.objects.update_or_create(
                fund=fund,
                company_name=company_name,
                defaults={
                    "execution_capacity_score": item.get("execution_capacity_score", 5.0),
                    "market_validation_score": item.get("market_validation_score", 5.0),
                    "status": item.get("status", "ON_TRACK")
                }
            )
            serializer = RiskAssessmentSerializer(assessment)
            results.append(serializer.data)

        return Response(results, status=status.HTTP_200_OK)


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

def calculate_irr(real_moic, wait_time):
    """
    Calculates IRR based on the formula: [(Real MOIC to Investors)^(1/wait_time) - 1]
    """
    if real_moic <= 0 or wait_time <= 0:
        return 0.0
    return (float(real_moic) ** (1.0 / float(wait_time))) - 1.0

def calculate_wait_time(inception_year, current_year, total_invested, injections_by_year):
    """
    Calculates weighted average investment time based on:
    [summation_{yr=inception}^{current_year-1} (invested_capital_yr * (current_year - 1 - inception_year)) / total_invested]
    """
    if total_invested <= 0:
        return 0.0
    
    wait_base = float(current_year - 1 - inception_year)
    numerator = 0.0
    for yr in range(inception_year, current_year):
        numerator += float(injections_by_year.get(yr, 0.0)) * wait_base
    
    return numerator / float(total_invested)

class FundPerformanceView(APIView):
    """
    Calculates performance metrics for the three dashboard tabs:
    1. Dashboard Tab
    2. Aggregated Exits Tab
    3. Admin Fee Tab
    """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get_performance_table(fund):
        deals = fund.deals.all()
        current_deals = fund.current_deals.all()
        model_inputs = getattr(fund, "model_inputs", None)
        
        if not model_inputs:
            return None, None

        exit_horizon = float(model_inputs.exit_horizon)
        management_fee_pct = float(model_inputs.management_fee)
        current_year = datetime.now().year
        inception_year = int(model_inputs.inception_year)

        # 1. Deal Prognosis Metrics (Future Only)
        total_invested = sum(deal.amount_invested for deal in deals)
        deal_serializer = InvestmentDealSerializer(deals, many=True)
        deals_data = deal_serializer.data
        deals_data_lookup = {d["id"]: d for d in deals_data}

        # Calculate expected pro-rata total and track injections by year
        total_expected_pro_rata = 0.0
        p_injections_by_year = {}
        for d_data in deals_data:
            yr = d_data["entry_year"]
            p_injections_by_year[yr] = p_injections_by_year.get(yr, 0.0) + float(d_data.get("amount_invested", 0))
            total_expected_pro_rata += float(d_data.get("expected_pro_rata_investments", 0))
            
        # Distribute pro-rata across years for weighted time calculation
        for deal_obj in deals:
            if deal_obj.pro_rata_rights and deal_obj.expected_number_of_rounds > 0:
                d_data = deals_data_lookup.get(str(deal_obj.id))
                if d_data:
                    total_pro_rata_deal = float(d_data.get("expected_pro_rata_investments", 0))
                    round_amt = total_pro_rata_deal / deal_obj.expected_number_of_rounds
                    for i in range(1, deal_obj.expected_number_of_rounds + 1):
                        yr = deal_obj.entry_year + i
                        p_injections_by_year[yr] = p_injections_by_year.get(yr, 0.0) + round_amt
        
        total_invested_float = float(total_invested) + total_expected_pro_rata
        gross_exit_value = sum(float(d["exit_value"]) for d in deals_data)
        
        moic = gross_exit_value / total_invested_float if total_invested_float > 0 else 0
        
        p_tier1_moic = float(model_inputs.least_expected_moic_tier_1)
        p_tier2_moic = float(model_inputs.least_expected_moic_tier_2)
        
        if moic < p_tier1_moic:
            p_carry_pct = 0.0
        elif moic < p_tier2_moic:
            p_carry_pct = float(model_inputs.tier_1_carry)
        else:
            p_carry_pct = float(model_inputs.tier_2_carry)
        
        p_profit = gross_exit_value - total_invested_float
        p_carry_amount = p_profit * (p_carry_pct / 100.0) if p_profit > 0 else 0
        p_total_fees = total_invested_float * (management_fee_pct / 100.0)
        p_net_to_investors = gross_exit_value - (p_total_fees + p_carry_amount)
        p_real_moic = p_net_to_investors / total_invested_float if total_invested_float > 0 else 0
        
        p_wait = calculate_wait_time(inception_year, current_year, total_invested_float, p_injections_by_year)
        irr = calculate_irr(moic, p_wait)

        # 2. Current Deals Metrics (Past Only)
        c_total_invested = sum(d.amount_invested for d in current_deals)
        c_deal_serializer = CurrentDealSerializer(current_deals, many=True)
        c_deals_data = c_deal_serializer.data
        c_gross_exit_value = sum(float(d["final_exit_amount"]) for d in c_deals_data)
        
        c_total_invested_float = float(c_total_invested)
        c_injections_by_year = {}
        for d in c_deals_data:
            yr = d["entry_year"]
            c_injections_by_year[yr] = c_injections_by_year.get(yr, 0.0) + float(d["amount_invested"])
            
        c_moic = c_gross_exit_value / c_total_invested_float if c_total_invested_float > 0 else 0
        
        if c_moic < p_tier1_moic:
            c_carry_pct = 0.0
        elif c_moic < p_tier2_moic:
            c_carry_pct = float(model_inputs.tier_1_carry)
        else:
            c_carry_pct = float(model_inputs.tier_2_carry)
        
        c_profit = c_gross_exit_value - c_total_invested_float
        c_carry_amount = c_profit * (c_carry_pct / 100.0) if c_profit > 0 else 0
        c_total_fees = c_total_invested_float * (management_fee_pct / 100.0)
        c_net_to_investors = c_gross_exit_value - (c_total_fees + c_carry_amount)
        c_real_moic = c_net_to_investors / c_total_invested_float if c_total_invested_float > 0 else 0
        
        c_wait = calculate_wait_time(inception_year, current_year, c_total_invested_float, c_injections_by_year)
        c_irr = calculate_irr(c_moic, c_wait)

        # 3. Performance Table
        current_year = datetime.now().year
        start_year = int(model_inputs.inception_year)
        fund_life = int(model_inputs.fund_life)
        end_year = start_year + fund_life - 1
        
        all_entry_years = [d["entry_year"] for d in deals_data] + [d["entry_year"] for d in c_deals_data]
        all_exit_years = [d["exit_year"] for d in deals_data] + [d["latest_valuation_year"] for d in c_deals_data]
        
        if all_entry_years:
            start_year = min(start_year, min(all_entry_years))
        if all_exit_years:
            end_year = max(end_year, max(all_exit_years))

        current_deals_by_year = {}
        for d in c_deals_data:
            yr = d["entry_year"]
            current_deals_by_year.setdefault(yr, []).append(d)
            
        prognosis_deals_by_year = {}
        deals_data_lookup = {d["id"]: d for d in deals_data}
        
        for d in deals_data:
            yr = d["entry_year"]
            prognosis_deals_by_year.setdefault(yr, []).append(d)
        
        performance_table = []
        current_portfolio_value = 0.0
        prognosis_portfolio_value = 0.0
        
        safe_c_irr = c_irr if c_irr and c_irr > -1 else 0.0
        safe_p_irr = irr if irr and irr > -1 else 0.0
        
        for year in range(start_year, end_year + 1):
            year_current_deals = current_deals_by_year.get(year, [])
            c_injection = sum(float(d["amount_invested"]) for d in year_current_deals)
            
            year_prognosis_deals = prognosis_deals_by_year.get(year, [])
            p_injection = sum(float(d["amount_invested"]) for d in year_prognosis_deals)
            
            for deal_obj in deals:
                if deal_obj.pro_rata_rights and deal_obj.expected_number_of_rounds > 0:
                    d_data = deals_data_lookup.get(str(deal_obj.id))
                    if d_data:
                        total_pro_rata = float(d_data.get("expected_pro_rata_investments", 0))
                        round_amt = total_pro_rata / deal_obj.expected_number_of_rounds
                        if deal_obj.entry_year < year <= deal_obj.entry_year + deal_obj.expected_number_of_rounds:
                            p_injection += round_amt
            
            c_appreciation = (current_portfolio_value or 0.0) * safe_c_irr
            p_appreciation = (prognosis_portfolio_value or 0.0) * safe_p_irr
            
            current_portfolio_value = max(0.0, current_portfolio_value) + (c_injection or 0.0) + (c_appreciation or 0.0)
            prognosis_portfolio_value = max(0.0, prognosis_portfolio_value) + (p_injection or 0.0) + (p_appreciation or 0.0)
            
            total_portfolio_value_with_prognosis = current_portfolio_value + prognosis_portfolio_value
            
            performance_table.append({
                "year": year,
                "total_portfolio_value_with_prognosis": total_portfolio_value_with_prognosis,
                "injection_current": c_injection,
                "injection_prognosis": p_injection,
                "appreciation_current": c_appreciation,
                "appreciation_prognosis": p_appreciation
            })
        
        return performance_table, {
            "p_real_moic": p_real_moic, "irr": irr, "moic": moic, "total_invested": total_invested_float, "gross_exit_value": gross_exit_value,
            "c_real_moic": c_real_moic, "c_irr": c_irr, "c_moic": c_moic, "c_total_invested": c_total_invested_float, "c_gross_exit_value": c_gross_exit_value,
            "p_wait": p_wait, "c_wait": c_wait
        }

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        performance_table_raw, metrics = self.get_performance_table(fund)
        if performance_table_raw is None:
            return Response({"error": "Model inputs not found for this fund."}, status=status.HTTP_400_BAD_REQUEST)

        model_inputs = fund.model_inputs
        current_year = datetime.now().year
        
        # Build the full performance table for the response
        performance_table = []
        cum_inj_no_p = 0.0
        cum_inj_with_p = 0.0
        
        for row in performance_table_raw:
            year = row["year"]
            c_inj = row["injection_current"]
            p_inj = row["injection_prognosis"]
            
            cum_inj_no_p += c_inj if year <= current_year else 0
            cum_inj_with_p += c_inj + p_inj
            
            performance_table.append({
                **row,
                "current_year": current_year,
                "is_future": year > current_year,
                "injection_of_current_after_cutoff": c_inj if year > current_year else 0,
                # "appreciation_of_current_after_cutoff": row["appreciation_current"] if year > current_year else 0, # Removed as per user request
                "cumulative_injection_no_prognosis": cum_inj_no_p,
                "cumulative_injection_with_prognosis": cum_inj_with_p,
                "total_portfolio_value_no_prognosis": row["total_portfolio_value_with_prognosis"] - row["injection_prognosis"] - row["appreciation_prognosis"], # Portfolio Value (No Future Deals) calculation
            })

        # Exits Cases
        cases = [
            {"name": "Base Case", "multiplier": 1.0},
            {"name": "Upside Case", "multiplier": 1.2},
            {"name": "High Growth Case", "multiplier": 1.5},
        ]
        aggregated_exits = []
        p_tier1_moic = float(model_inputs.least_expected_moic_tier_1)
        p_tier2_moic = float(model_inputs.least_expected_moic_tier_2)
        management_fee_pct = float(model_inputs.management_fee)

        for case in cases:
            case_gev = metrics["c_gross_exit_value"] * case["multiplier"]
            profit = case_gev - metrics["c_total_invested"]
            case_moic = case_gev / metrics["c_total_invested"] if metrics["c_total_invested"] > 0 else 0
            
            if case_moic < p_tier1_moic:
                carry_pct = 0.0
            elif case_moic < p_tier2_moic:
                carry_pct = float(model_inputs.tier_1_carry)
            else:
                carry_pct = float(model_inputs.tier_2_carry)
            
            carry_amt = profit * (carry_pct / 100.0) if profit > 0 else 0
            fees = metrics["c_total_invested"] * (management_fee_pct / 100.0)
            net = case_gev - (fees + carry_amt)
            real_moic = net / metrics["c_total_invested"] if metrics["c_total_invested"] > 0 else 0
            
            aggregated_exits.append({
                "case": case["name"], "gev": case_gev, "profit_before_carry": profit, "gross_moic": case_moic,
                "carry_pct": carry_pct, "carry_amount": carry_amt, "total_fees": fees, "net_to_investors": net,
                "real_moic": real_moic, "irr": calculate_irr(case_moic, metrics["c_wait"])
            })

        admin_fee_data = {
            "total_admin_cost": (float(model_inputs.admin_cost) / 100.0) * float(model_inputs.target_fund_size),
            "operations_fee": (management_fee_pct / 100.0) * float(model_inputs.target_fund_size),
            "management_fees": (management_fee_pct / 100.0) * float(model_inputs.target_fund_size) * float(model_inputs.fund_life),
            "total_costs": 0, # sum above
            "inception_year": int(model_inputs.inception_year),
            "fund_life": int(model_inputs.fund_life)
        }
        admin_fee_data["total_costs"] = admin_fee_data["total_admin_cost"] + admin_fee_data["operations_fee"] + admin_fee_data["management_fees"]

        return Response({
            "dashboard": {
                "total_invested": metrics["total_invested"], "gross_exit_value": metrics["gross_exit_value"],
                "moic": metrics["moic"], "irr": metrics["irr"], "real_moic": metrics["p_real_moic"],
                "total_deals": fund.deals.count(), "performance_table": performance_table
            },
            "current_deals_metrics": {
                "total_invested": metrics["c_total_invested"], "gross_exit_value": metrics["c_gross_exit_value"],
                "moic": metrics["c_moic"], "irr": metrics["c_irr"], "real_moic": metrics["c_real_moic"],
                "total_deals": fund.current_deals.count()
            },
            "aggregated_exits": aggregated_exits,
            "admin_fee": admin_fee_data
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
        
        total_fund_invested = 0.0
        
        for action in investor_actions:
            investor_id = str(action.investor.id)
            if investor_id not in investor_data:
                investor_data[investor_id] = {
                    "first_name": action.investor.first_name,
                    "last_name": action.investor.last_name,
                    "email": action.investor.email,
                    "total_invested": 0.0
                }
            
            amount = float(action.amount) if action.type == "CAPITAL_INVESTMENT" and action.amount else 0.0
            original_val = float(action.original_value) if action.type == "SECONDARY_EXIT" and action.original_value else 0.0
            
            net_action = amount - original_val
            investor_data[investor_id]["total_invested"] += net_action
            total_fund_invested += net_action

        investors_list = []
        for inv_id, data in investor_data.items():
            ownership_pct = (data["total_invested"] / total_fund_invested * 100.0) if total_fund_invested > 0 else 0.0
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
            amount = float(action.amount) if action.type == "CAPITAL_INVESTMENT" and action.amount else 0.0
            original_val = float(action.original_value) if action.type == "SECONDARY_EXIT" and action.original_value else 0.0
            net_action = amount - original_val
            invested_by_year[yr] = invested_by_year.get(yr, 0.0) + net_action
            
        cumulative_invested = 0.0
        cumulative_required = 0.0
        
        for yr in range(inception_year, end_year + 1):
            cumulative_invested += invested_by_year.get(yr, 0.0)
            cumulative_required += required_by_year.get(yr, 0.0)
            
            graph_data.append({
                "year": yr,
                "total_capital_invested": cumulative_invested,
                "total_capital_required": cumulative_required
            })
            
        return Response({
            "investors": investors_list,
            "graph_data": graph_data
        })
