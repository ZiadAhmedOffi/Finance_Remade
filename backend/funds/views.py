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
        fund = get_object_or_404(Fund, id=fund_id, is_active=True)
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

def calculate_irr(cash_flows, years, guess=0.1, max_iter=1000, tolerance=1e-6):
    """
    Simple Newton-Raphson implementation for IRR.
    cash_flows: list of amounts (neg for investment, pos for exit)
    years: list of years corresponding to cash_flows
    """
    if not cash_flows or len(cash_flows) < 2:
        return 0.0
    
    # Normalize years to start from 0
    min_year = min(years)
    t = [y - min_year for y in years]
    
    r = guess
    for _ in range(max_iter):
        f_val = sum(cf / ((1 + r) ** time) for cf, time in zip(cash_flows, t))
        f_prime = sum(-time * cf / ((1 + r) ** (time + 1)) for cf, time in zip(cash_flows, t))
        
        if abs(f_prime) < 1e-10: # Avoid division by zero
            break
            
        new_r = r - f_val / f_prime
        if abs(new_r - r) < tolerance:
            return new_r
        r = new_r
        
        if abs(r) > 100: # Sanity check to prevent runaway
            return 0.0
            
    return r

class FundPerformanceView(APIView):
    """
    Calculates performance metrics for the three dashboard tabs:
    1. Dashboard Tab
    2. Aggregated Exits Tab
    3. Admin Fee Tab
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, fund_id):
        fund = get_object_or_404(Fund, id=fund_id, is_active=True)
        if not PermissionService.can_view_fund(request.user, fund):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        deals = fund.deals.all()
        model_inputs = getattr(fund, "model_inputs", None)
        
        if not model_inputs:
            return Response({"error": "Model inputs not found for this fund."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Basic Metrics
        total_invested = sum(deal.amount_invested for deal in deals)
        
        # We need to use the serializer logic for exit_value
        deal_serializer = InvestmentDealSerializer(deals, many=True)
        deals_data = deal_serializer.data
        gross_exit_value = sum(float(d["exit_value"]) for d in deals_data)
        
        total_invested_float = float(total_invested)
        moic = gross_exit_value / total_invested_float if total_invested_float > 0 else 0
        
        # IRR Calculation
        # Construct cash flows: -invested at entry_year, +exit_value at exit_year
        cash_flows_dict = {}
        for d in deals_data:
            entry_yr = d["entry_year"]
            exit_yr = d["exit_year"]
            amount = float(d["amount_invested"])
            exit_val = float(d["exit_value"])
            
            cash_flows_dict[entry_yr] = cash_flows_dict.get(entry_yr, 0) - amount
            cash_flows_dict[exit_yr] = cash_flows_dict.get(exit_yr, 0) + exit_val
            
        years_sorted = sorted(cash_flows_dict.keys())
        cash_flows_list = [cash_flows_dict[y] for y in years_sorted]
        
        irr = calculate_irr(cash_flows_list, years_sorted)
        
        # 2. Performance Table
        from datetime import datetime
        current_year = datetime.now().year
        start_year = min(years_sorted) if years_sorted else current_year
        end_year = current_year
        
        performance_table = []
        portfolio_capital = 0.0
        
        for year in range(start_year, end_year + 1):
            injection = sum(float(d["amount_invested"]) for d in deals_data if d["entry_year"] == year)
            appreciation = portfolio_capital * irr
            portfolio_capital = portfolio_capital + injection + appreciation
            
            performance_table.append({
                "year": year,
                "injection": injection,
                "appreciation": appreciation,
                "total_portfolio_value": portfolio_capital
            })

        # 3. Aggregated Exits
        cases = [
            {"name": "Base Case", "multiplier": 1.0},
            {"name": "Upside Case", "multiplier": 1.2},
            {"name": "High Growth Case", "multiplier": 1.5},
        ]
        
        aggregated_exits = []
        management_fee_pct = float(model_inputs.management_fee)
        
        for case in cases:
            case_gev = gross_exit_value * case["multiplier"]
            profit_before_carry = case_gev - total_invested_float
            case_moic = case_gev / total_invested_float if total_invested_float > 0 else 0
            
            # Carry calculation
            carry_pct = 0.0
            tier1_moic = float(model_inputs.least_expected_moic_tier_1)
            tier2_moic = float(model_inputs.least_expected_moic_tier_2)
            
            if case_moic < tier1_moic:
                carry_pct = 0.0
            elif case_moic < tier2_moic:
                carry_pct = float(model_inputs.tier_1_carry)
            else:
                carry_pct = float(model_inputs.tier_2_carry)
            
            carry_amount = profit_before_carry * (carry_pct / 100.0) if profit_before_carry > 0 else 0
            total_fees = total_invested_float * (management_fee_pct / 100.0)
            net_to_investors = case_gev - (total_fees + carry_amount)
            real_moic = net_to_investors / total_invested_float if total_invested_float > 0 else 0
            
            # IRR for case
            case_cf_dict = {}
            for d in deals_data:
                entry_yr = d["entry_year"]
                exit_yr = d["exit_year"]
                amount = float(d["amount_invested"])
                
                # Pro-rata exit value for the case
                # We need to know how much this deal contributed to original GEV
                orig_deal_exit_val = float(d["exit_value"])
                case_deal_exit_val = orig_deal_exit_val * case["multiplier"]
                
                case_cf_dict[entry_yr] = case_cf_dict.get(entry_yr, 0) - amount
                case_cf_dict[exit_yr] = case_cf_dict.get(exit_yr, 0) + case_deal_exit_val
            
            case_years = sorted(case_cf_dict.keys())
            case_cfs = [case_cf_dict[y] for y in case_years]
            case_irr = calculate_irr(case_cfs, case_years)
            
            aggregated_exits.append({
                "case": case["name"],
                "gev": case_gev,
                "profit_before_carry": profit_before_carry,
                "gross_moic": case_moic,
                "carry_pct": carry_pct,
                "carry_amount": carry_amount,
                "total_fees": total_fees,
                "net_to_investors": net_to_investors,
                "real_moic": real_moic,
                "irr": case_irr
            })

        # 4. Admin Fee Tab
        target_fund_size = float(model_inputs.target_fund_size)
        admin_pct = float(model_inputs.admin_cost)
        investment_period = float(model_inputs.investment_period)
        
        total_admin_cost = (admin_pct / 100.0) * target_fund_size
        operations_fee = (management_fee_pct / 100.0) * target_fund_size
        management_fees_total = total_admin_cost * investment_period
        
        admin_fee_data = {
            "total_admin_cost": total_admin_cost,
            "operations_fee": operations_fee,
            "management_fees": management_fees_total,
            "total_costs": total_admin_cost + operations_fee + management_fees_total
        }

        return Response({
            "dashboard": {
                "total_invested": total_invested_float,
                "gross_exit_value": gross_exit_value,
                "moic": moic,
                "irr": irr,
                "total_deals": deals.count(),
                "performance_table": performance_table
            },
            "aggregated_exits": aggregated_exits,
            "admin_fee": admin_fee_data
        })
