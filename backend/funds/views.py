from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from .logic import (
    get_total_fund_portfolio, 
    get_total_units_at_year, 
    solve_implied_return_rate, 
    get_prognosis_injections, 
    get_current_injections, 
    calculate_nav_trajectory
)
from .utils.liquidityUtils import calculateLiquidityIndex
from .models import Fund, FundLog, ModelInput, InvestmentDeal, CurrentDeal, InvestmentRound, InvestorAction, RiskAssessment, CurrentInvestorStats, PossibleCapitalSource, Report, InvestorRequest
from .serializers import (
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
from users.services.permission_service import PermissionService
from users.services.audit_service import AuditService

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
        
        with transaction.atomic():
            serializer = InvestorActionSerializer(data=request.data)
            if serializer.is_valid():
                fund = serializer.validated_data["fund"]
                action_type = serializer.validated_data["type"]
                year = serializer.validated_data["year"]
                amount = float(serializer.validated_data.get("amount", 0.0) or 0.0)
                
                if action_type == "PRIMARY_INVESTMENT":
                    # Check if this is the first primary investment for this fund
                    is_first = not InvestorAction.objects.filter(fund=fund, type="PRIMARY_INVESTMENT").exists()
                    if is_first:
                        units = amount
                    else:
                        # end of previous year
                        prev_year_portfolio = get_total_fund_portfolio(fund, year - 1)
                        prev_year_units = get_total_units_at_year(fund, year - 1)
                        if prev_year_units > 0 and prev_year_portfolio > 0:
                            units = amount / (prev_year_portfolio / prev_year_units)
                        else:
                            # Fallback if no units/portfolio exist (shouldn't happen if is_first is False, but good for safety)
                            units = amount 
                    
                    action = serializer.save(units=units)
                    # Update fund total units
                    fund.total_units = float(fund.total_units) + units
                    fund.save()

                elif action_type == "SECONDARY_EXIT":
                    seller = serializer.validated_data["investor_selling"]
                    buyer = serializer.validated_data["investor_sold_to"]
                    pct_sold = float(serializer.validated_data["percentage_sold"])
                    discount = float(serializer.validated_data.get("discount_percentage", 0.0) or 0.0)
                    
                    # Calculate seller's current units to verify ownership
                    seller_actions = InvestorAction.objects.filter(fund=fund, investor=seller)
                    seller_units = 0.0
                    for a in seller_actions:
                        if a.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
                            seller_units += float(a.units)
                        elif a.type == "SECONDARY_EXIT":
                            seller_units -= float(a.units)
                    
                    # Use units from year - 1 as basis for exit
                    total_units_at_basis_year = get_total_units_at_year(fund, year - 1)
                    if total_units_at_basis_year == 0:
                         total_units_at_basis_year = float(fund.total_units)

                    # Calculate units transferred
                    units_transferred = (pct_sold / 100.0) * total_units_at_basis_year
                    
                    if units_transferred > seller_units + 0.0001: # Add small epsilon for float precision
                         return Response({"error": f"Units to sell ({units_transferred:.4f}) exceed seller units ({seller_units:.4f})."}, status=status.HTTP_400_BAD_REQUEST)

                    # Use amount from request (which may be calculated or manually entered)
                    # Amount is already in serializer.validated_data["amount"]
                    
                    # Save the secondary exit action (seller)
                    action = serializer.save(units=units_transferred)
                    price = float(action.amount)
                    
                    # Also create a SECONDARY_INVESTMENT for the buyer (if buyer is specified)
                    if buyer:
                        InvestorAction.objects.create(
                            investor=buyer,
                            fund=fund,
                            type="SECONDARY_INVESTMENT",
                            year=year,
                            amount=price,
                            percentage_sold=pct_sold,
                            discount_percentage=discount,
                            investor_selling=seller,
                            units=units_transferred
                        )

                else: # SECONDARY_INVESTMENT or others
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
    Restricted to Super Admins and SC members of the fund.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, action_id):
        action = get_object_or_404(InvestorAction, id=action_id)
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, action.fund)):
            return Response({"error": "Only super admins and SC members can update investor actions."}, status=status.HTTP_403_FORBIDDEN)
        
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
        action = get_object_or_404(InvestorAction, id=action_id)
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, action.fund)):
            return Response({"error": "Only super admins and SC members can delete investor actions."}, status=status.HTTP_403_FORBIDDEN)
        
        action_id_str = str(action.id)
        action_type = action.type
        investor_email = action.investor.email
        fund = action.fund
        target_user = action.investor
        
        # If primary investment, reduce fund total units
        if action.type == "PRIMARY_INVESTMENT":
            fund.total_units = float(fund.total_units) - float(action.units)
            fund.save()
            
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

        actions = InvestorAction.objects.filter(investor=investor).select_related('fund')
        
        # Group actions by fund
        fund_data = {}
        for action in actions:
            fund_id = str(action.fund.id)
            if fund_id not in fund_data:
                fund_data[fund_id] = {
                    "fund": action.fund,
                    "investments": [],
                    "exits": [],
                    "units": 0.0,
                    "net_deployed": 0.0
                }
            if action.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
                fund_data[fund_id]["investments"].append(action)
                fund_data[fund_id]["units"] += float(action.units)
                fund_data[fund_id]["net_deployed"] += float(action.amount or 0)
            elif action.type == "SECONDARY_EXIT":
                fund_data[fund_id]["exits"].append(action)
                fund_data[fund_id]["units"] -= float(action.units)
                fund_data[fund_id]["net_deployed"] -= float(action.amount or 0)

        total_current_portfolio_value = 0.0
        
        portfolio_table = []
        pie_chart_data = []

        # We need fund performance to get current values
        for fund_id, data in fund_data.items():
            fund = data["fund"]
            
            # Calculate ownership in the fund
            total_fund_units = float(fund.total_units)
            ownership_pct = (data["units"] / total_fund_units * 100.0) if total_fund_units > 0 else 0.0
            
            # Get current fund portfolio value
            current_fund_val = get_total_fund_portfolio(fund, datetime.now().year)
            
            current_val_in_fund = (ownership_pct / 100.0) * current_fund_val
            total_current_portfolio_value += current_val_in_fund
            
            portfolio_table.append({
                "fund_name": fund.name,
                "ownership_pct": ownership_pct,
                "current_value": current_val_in_fund,
                "net_deployed": data["net_deployed"]
            })
            
            pie_chart_data.append({
                "name": fund.name,
                "value": current_val_in_fund
            })

        relations = CurrentInvestorStats.objects.filter(investor = investor)
        realized_gains = 0
        total_capital_deployed = 0

        realized_gains = sum(float(relation.realized_gain or 0) for relation in relations)
        total_capital_deployed = sum(float(relation.amount_invested or 0) for relation in relations)
        total_capital_injected = sum(float(relation.capital_deployed or 0) for relation in relations)

        unrealized_gains = total_current_portfolio_value - total_capital_deployed
        
        unrealized_multiple = 0.0
        if total_capital_deployed > 0:
            unrealized_multiple = total_current_portfolio_value / total_capital_deployed

        realized_multiple = 0.0
        investor_investments = InvestorAction.objects.filter(investor=investor, type__in=["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"])
        investor_exits = InvestorAction.objects.filter(investor=investor, type="SECONDARY_EXIT")
        total_exits_amount = sum(float(action.amount or 0) for action in investor_exits)
        total_invested_amount = sum(float(action.amount or 0) for action in investor_investments)
        if total_capital_deployed > 0 and total_capital_deployed != total_invested_amount:
            realized_multiple = total_exits_amount / (total_invested_amount - total_capital_deployed) # the subtraction to get the cost basis for total units sold
        elif total_capital_deployed == total_invested_amount:
            realized_multiple = 0.0

        # Line Graph Logic & Historical Breakdown
        years = sorted(list(set(a.year for a in actions)))
        if not years:
            line_graph_data = []
        else:
            start_year = min(years)
            current_year = datetime.now().year
            end_year = max(current_year, max(years))
            
            line_graph_data = []
            
            for yr in range(start_year, end_year + 1):
                yr_total_value = 0.0
                yr_total_injection = 0.0
                
                for fid, f_data in fund_data.items():
                    fund = f_data["fund"]
                    
                    # Investor units in this fund at the end of yr
                    actions_up_to_yr = InvestorAction.objects.filter(investor=investor, fund=fund, year__lte=yr)
                    f_units_at_yr = 0.0
                    for a in actions_up_to_yr:
                        if a.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
                            f_units_at_yr += float(a.units)
                        elif a.type == "SECONDARY_EXIT":
                            f_units_at_yr -= float(a.units)
                    
                    total_fund_units_at_yr = get_total_units_at_year(fund, yr)
                    
                    f_ownership_pct_at_yr = (f_units_at_yr / total_fund_units_at_yr * 100.0) if total_fund_units_at_yr > 0 else 0.0
                    
                    fund_val_at_yr = get_total_fund_portfolio(fund, yr)
                    yr_total_value += (f_ownership_pct_at_yr / 100.0) * fund_val_at_yr
                    
                    # Tracking injections for this year specifically
                    actions_this_yr = InvestorAction.objects.filter(investor=investor, fund=fund, year=yr)
                    for a in actions_this_yr:
                        if a.type in ["PRIMARY_INVESTMENT", "SECONDARY_INVESTMENT"]:
                            yr_total_injection += float(a.amount or 0)
                        elif a.type == "SECONDARY_EXIT":
                            yr_total_injection -= float(a.amount or 0)

                prev_val = line_graph_data[-1]["value"] if line_graph_data else 0
                yoy_gain = 0.0
                if prev_val > 0:
                    yoy_gain = ((yr_total_value / prev_val) - 1) * 100

                line_graph_data.append({
                    "year": yr,
                    "value": yr_total_value,
                    "injection": yr_total_injection,
                    "yoy_gain": yoy_gain if line_graph_data else None
                })

        return Response({
            "metrics": {
                "total_capital_deployed": total_capital_injected,
                "realized_gains": realized_gains,
                "unrealized_gains": unrealized_gains,
                "realized_multiple": realized_multiple ,
                "unrealized_multiple": unrealized_multiple,
            },
            "portfolio": portfolio_table,
            "pie_chart": pie_chart_data,
            "line_graph": line_graph_data
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
    historical_final_year = current_year

    # 1. Deal Prognosis Metrics
    deal_serializer = InvestmentDealSerializer(deals, many=True)
    deals_data = deal_serializer.data
    
    p_injections_by_year = get_prognosis_injections(deals_data, deals)
    
    total_expected_pro_rata = sum(float(d.get("expected_pro_rata_investments", 0)) for d in deals_data)
    total_invested_float = float(sum(deal.amount_invested for deal in deals)) + total_expected_pro_rata
    
    gross_exit_value = sum(float(d["exit_value"]) for d in deals_data)
    gross_exit_value_future = sum(float(d["exit_value"]) for d in deals_data if d["entry_year"] >= current_year)
    
    p_injections_future = {yr: amt for yr, amt in p_injections_by_year.items() if yr >= current_year}
    p_solver_injections = p_injections_future if p_injections_future else p_injections_by_year
    irr = solve_implied_return_rate(p_solver_injections, fund_end_year, gross_exit_value_future)

    # 2. Current Deals Metrics
    c_deal_serializer = CurrentDealSerializer(current_deals, many=True)
    c_deals_data = c_deal_serializer.data
    c_injections_by_year = get_current_injections(c_deals_data)
    
    c_total_invested_float = float(sum(d.amount_invested for d in current_deals))
    c_gross_exit_value = sum(float(d["final_exit_amount"]) for d in c_deals_data)
    c_irr = solve_implied_return_rate(c_injections_by_year, historical_final_year, c_gross_exit_value)

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
    all_entry_years = [d["entry_year"] for d in deals_data] + [d["entry_year"] for d in c_deals_data]
    all_exit_years = [d["exit_year"] for d in deals_data] + [d["latest_valuation_year"] for d in c_deals_data]
    start_year = min(inception_year, min(all_entry_years)) if all_entry_years else inception_year
    end_year = max(fund_end_year, max(all_exit_years)) if all_exit_years else fund_end_year

    safe_c_irr = c_irr if c_irr and c_irr > -1 else 0.0
    safe_p_irr = irr if irr and irr > -1 else 0.0

    trajectory = calculate_nav_trajectory(
        start_year, end_year, current_year, fund_end_year,
        c_injections_by_year, p_injections_by_year,
        safe_c_irr, safe_p_irr
    )

    current_deals_by_year = {}
    for d in c_deals_data: current_deals_by_year.setdefault(d["entry_year"], []).append(d)
    prognosis_deals_by_year = {}
    for d in deals_data: prognosis_deals_by_year.setdefault(d["entry_year"], []).append(d)
    
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
            "irr": solve_implied_return_rate(c_injections_by_year, historical_final_year, case_gev)
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
            "irr": solve_implied_return_rate(all_injections, fund_end_year, case_gev)
        })

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
            portfolio_val = get_total_fund_portfolio(fund, yr)

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

    def get_queryset(self, user, report_type="DYNAMIC"):
        if PermissionService.is_super_admin(user):
            return Report.objects.filter(report_type=report_type)
        else:
            from users.models import UserRoleAssignment
            managed_funds = UserRoleAssignment.objects.filter(
                user=user, role__name="STEERING_COMMITTEE"
            ).values_list("fund_id", flat=True)
            return Report.objects.filter(fund_id__in=managed_funds, report_type=report_type)

    def get(self, request):
        reports = self.get_queryset(request.user, report_type="DYNAMIC")
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Default to DYNAMIC if not specified
        if "report_type" not in request.data:
            request.data["report_type"] = "DYNAMIC"
            
        serializer = ReportSerializer(data=request.data)
        if serializer.is_valid():
            fund = serializer.validated_data["fund"]
            if not (PermissionService.is_super_admin(request.user) or 
                    PermissionService.is_sc_member(request.user, fund)):
                return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            
            report = serializer.save(created_by=request.user)
            
            # Log creation
            AuditService.log(
                actor=request.user,
                action="REPORT_CREATED",
                fund=report.fund,
                metadata={"report_id": str(report.id), "name": report.name, "type": report.report_type},
                ip=request.META.get("REMOTE_ADDR")
            )
            
            # Trigger mock generation
            self.trigger_generation(report, request.user)
            
            return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def trigger_generation(self, report, user):
        report.status = "GENERATING"
        report.save()
        report.status = "ACTIVE"
        report.static_url = f"/reports/{report.slug}/index.html"
        report.save()
        
        AuditService.log(
            actor=user,
            action="REPORT_GENERATED",
            fund=report.fund,
            metadata={"report_id": str(report.id), "slug": report.slug},
            ip=None
        )

class CapitalCallReportListView(ReportListView):
    """
    Specialized view for Capital Call Reports.
    """
    def get(self, request):
        reports = self.get_queryset(request.user, report_type="CAPITAL_CALL")
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)

    def post(self, request):
        request.data["report_type"] = "CAPITAL_CALL"
        return super().post(request)

class ReportDetailView(APIView):
    """
    Handles updating and deleting specific reports.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, report_id):
        report = get_object_or_404(Report, id=report_id)
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, report.fund)):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ReportSerializer(report, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            AuditService.log(
                actor=request.user,
                action="REPORT_UPDATED",
                fund=report.fund,
                metadata={"report_id": str(report.id), "name": report.name},
                ip=request.META.get("REMOTE_ADDR")
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, report_id):
        report = get_object_or_404(Report, id=report_id)
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, report.fund)):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        AuditService.log(
            actor=request.user,
            action="REPORT_DELETED",
            fund=report.fund,
            metadata={"report_id": str(report.id), "name": report.name},
            ip=request.META.get("REMOTE_ADDR")
        )
        report.delete()
        return Response({"message": "Report deleted."}, status=status.HTTP_200_OK)

class ReportRegenerateView(APIView):
    """
    Manually trigger report regeneration.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, report_id):
        report = get_object_or_404(Report, id=report_id)
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, report.fund)):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        report.status = "GENERATING"
        report.save()
        # Mock logic
        report.status = "ACTIVE"
        report.save()
        
        AuditService.log(
            actor=request.user,
            action="REPORT_GENERATED",
            fund=report.fund,
            metadata={"report_id": str(report.id), "slug": report.slug},
            ip=request.META.get("REMOTE_ADDR")
        )
        return Response(ReportSerializer(report).data)

from django.http import HttpResponse
from .security import SecurityScanner
from .ingestion import ExcelIngestService

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

            total_fund_units = get_total_units_at_year(fund, current_year)
            total_portfolio_value = get_total_fund_portfolio(fund, current_year)
            
            price_per_unit = float(total_portfolio_value / total_fund_units) if total_fund_units > 0 else 1.0
            
            # Liquidity Index (simplified lookup from performance data or calculated)
            current_deals = fund.current_deals.all()
            li_data = calculateLiquidityIndex(current_deals, model_inputs.inception_year)
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
