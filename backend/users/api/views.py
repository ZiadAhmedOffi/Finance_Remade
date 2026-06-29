from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from users.models import User, Role, UserRoleAssignment
from funds.models import Fund
from users.api.serializers import ApplyAccessSerializer, UserSerializer, RoleSerializer, AuditLogSerializer
from users.permissions import IsAccessManager, IsSuperAdmin
from users.services.permission_service import PermissionService
from users.services.audit_service import AuditService
from users.models import AuditLog
from users.services.user_service import UserService
from users.interfaces.fund_service_adapter import FundServiceAdapter
from users.dpop import validate_dpop_proof
from users.throttles import LoginRateThrottle, TokenRefreshRateThrottle, ApplyAccessRateThrottle

fund_adapter = FundServiceAdapter()
user_service = UserService(fund_adapter)

# -----------------------------
# JWT Custom Token Serializer
# -----------------------------
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT Token Serializer that adds extra claims to the token
    such as email, staff status, superuser status, and assigned roles.
    Includes DPoP binding (cnf claim) if proof is provided.
    """
    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)
        token["email"] = user.email
        token["is_staff"] = user.is_staff
        token["is_superuser"] = user.is_superuser
        roles = user.role_assignments.select_related("role", "fund", "real_estate_portfolio").all()
        token["roles"] = [
            {
                "role": role.role.name,
                "fund": role.fund.name if role.fund else None,
                "fund_id": str(role.fund.id) if role.fund else None,
                "portfolio_id": str(role.real_estate_portfolio.id) if role.real_estate_portfolio else None,
            }
            for role in roles
        ]
        return token

    def validate(self, attrs):
        email = (attrs.get("email") or attrs.get("username") or "").strip().lower()
        password = attrs.get("password")
        request = self.context.get("request")
        ip = request.META.get("REMOTE_ADDR") if request else None

        if not email or not password:
            raise ValidationError("Email and password are required.")

        dpop_data = validate_dpop_proof(request, request.headers.get("DPoP") if request else None)

        user = User.objects.filter(email__iexact=email).first()
        authenticated_user = authenticate(request=request, email=email, password=password)

        if authenticated_user is None:
            if user:
                user.failed_login_attempts += 1
                user.save(update_fields=["failed_login_attempts"])
            AuditService.log_event(
                actor=user,
                action="LOGIN_FAILED",
                description=f"Failed login attempt for email: {email}",
                ip_address=ip
            )
            raise ValidationError("Invalid credentials.")

        if authenticated_user.status != "ACTIVE" or authenticated_user.is_deleted:
            AuditService.log_event(
                actor=authenticated_user,
                action="LOGIN_FAILED",
                description=f"Failed login attempt for inactive or deleted account: {email}",
                ip_address=ip
            )
            raise ValidationError("Invalid credentials.")

        if authenticated_user.failed_login_attempts:
            authenticated_user.failed_login_attempts = 0
        authenticated_user.last_login = timezone.now()
        if request:
            authenticated_user.last_login_ip = ip
        authenticated_user.save(update_fields=["failed_login_attempts", "last_login", "last_login_ip"])

        AuditService.log_event(
            actor=authenticated_user,
            action="LOGIN_SUCCESS",
            description=f"User {email} logged in successfully.",
            ip_address=ip
        )

        refresh = self.get_token(authenticated_user)
        refresh["cnf"] = {"jkt": dpop_data["jkt"]}

        data = {}
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT Token view that returns access and refresh tokens
    after validating user credentials and logging the event.
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        request = self.context.get("request")
        if request is None:
            raise ValidationError("Request context is required.")

        refresh = RefreshToken(attrs["refresh"])
        cnf = refresh.get("cnf") or {}
        expected_jkt = cnf.get("jkt")
        if not expected_jkt:
            raise ValidationError("DPoP-bound refresh token is required.")

        validate_dpop_proof(
            request,
            request.headers.get("DPoP"),
            expected_jkt=expected_jkt,
        )
        return super().validate(attrs)


class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer
    permission_classes = [AllowAny]
    throttle_classes = [TokenRefreshRateThrottle]

from users.selectors import user_selectors, audit_selectors

# -----------------------------
# User Listing & Management
# -----------------------------
class ActiveUsersPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class ActiveUsersView(APIView):
    """
    API view to list all active users in the system.
    Requires Access Manager permissions.
    """
    permission_classes = [IsAccessManager]

    def get(self, request):
        active_users = user_selectors.get_active_users()
        paginator = ActiveUsersPagination()
        result_page = paginator.paginate_queryset(active_users, request)
        serializer = UserSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

class PendingUsersView(APIView):
    """
    API view to list all users awaiting approval.
    Requires Access Manager permissions.
    """
    permission_classes = [IsAccessManager]

    def get(self, request):
        pending_users = user_selectors.get_pending_users()
        serializer = UserSerializer(pending_users, many=True)
        return Response(serializer.data)

# -----------------------------
# User Actions
# -----------------------------
class ApplyForAccessView(APIView):
    """
    Public API view for new users to submit an application for access.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ApplyAccessRateThrottle]

    def post(self, request):
        serializer = ApplyAccessSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        AuditService.log(
            actor=None,
            action="USER_APPLICATION_SUBMITTED",
            target_user=user,
            metadata={"description": f"User {user.email} applied for access."},
            ip=request.META.get("REMOTE_ADDR"),
        )

        return Response(
            {"message": "Application submitted successfully. Please await approval."},
            status=status.HTTP_201_CREATED,
        )

class ApproveUserView(APIView):
    """
    API view to approve a pending user application.
    Updates user status to ACTIVE and enables login.
    """
    permission_classes = [IsAccessManager]

    def post(self, request, user_id):
        try:
            user_service.approve_user(
                user_id=user_id,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response({"message": "User approved successfully."})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

class RejectUserView(APIView):
    """
    API view to reject a pending user application.
    Updates user status to REJECTED.
    """
    permission_classes = [IsAccessManager]

    def post(self, request, user_id):
        try:
            user_service.reject_user(
                user_id=user_id,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response({"message": "User rejected successfully."})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

class DeactivateUserView(APIView):
    """
    API view to deactivate an existing user.
    Sets is_active to False and status to REJECTED.
    """
    permission_classes = [IsAccessManager]

    def post(self, request, user_id):
        try:
            user_service.deactivate_user(
                user_id=user_id,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response({"message": "User deactivated successfully."})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

class ResetPasswordView(APIView):
    """
    API view for Super Admins to reset a user's password.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, user_id):
        new_password = request.data.get("new_password")
        if not new_password:
            return Response({"error": "New password is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_service.reset_password(
                user_id=user_id,
                new_password=new_password,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response({"message": f"Password for user reset successfully."})
        except DjangoValidationError as e:
            return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

class AssignRoleView(APIView):
    """
    API view to assign a role (and optionally a fund or portfolio) to a user.
    Enforces hierarchical restrictions for Super Admin and Access Manager roles.
    """
    permission_classes = [IsAccessManager]

    def post(self, request, user_id):
        role_id = request.data.get("role_id")
        fund_id = request.data.get("fund_id")
        portfolio_id = request.data.get("portfolio_id")

        try:
            assignment, created = user_service.assign_role(
                user_id=user_id,
                role_id=role_id,
                fund_id=fund_id,
                portfolio_id=portfolio_id,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            if not created:
                return Response({"message": "Role already assigned."})

            return Response({"message": "Role assigned successfully."})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

class RemoveRoleView(APIView):
    """
    API view to remove a specific role assignment from a user.
    """
    permission_classes = [IsAccessManager]

    def post(self, request, user_id):
        role_id = request.data.get("role_id")
        fund_id = request.data.get("fund_id")
        portfolio_id = request.data.get("portfolio_id")

        try:
            user_service.remove_role(
                user_id=user_id,
                role_id=role_id,
                fund_id=fund_id,
                portfolio_id=portfolio_id,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            return Response({"message": "Role removed successfully."})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

# -----------------------------
# Audit Log Listing
# -----------------------------
class AuditLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

class AuditLogView(APIView):
    """
    API view to retrieve system-wide audit logs.
    Requires Access Manager permissions.
    """
    permission_classes = [IsAccessManager]

    def get(self, request):
        logs = audit_selectors.get_all_audit_logs()
        paginator = AuditLogPagination()
        result_page = paginator.paginate_queryset(logs, request)
        serializer = AuditLogSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

from users.models import User, Role, UserRoleAssignment
...
class UpdateDividendTreatmentView(APIView):
    """
    API view to update dividend treatment for a specific role assignment.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, assignment_id):
        assignment = get_object_or_404(UserRoleAssignment, id=assignment_id)
        
        # Check permissions: Super Admin or SC Member of the fund
        if not (PermissionService.is_super_admin(request.user) or 
                PermissionService.is_sc_member(request.user, assignment.fund)):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        treatment = request.data.get("dividend_treatment")
        if treatment not in ["CASH", "REINVEST", "DEFAULT"]:
            return Response({"error": "Invalid treatment."}, status=status.HTTP_400_BAD_REQUEST)
        
        assignment.dividend_treatment = treatment
        assignment.save()
        
        return Response({"message": "Dividend treatment updated successfully."})

# -----------------------------
# Metadata Lists
# -----------------------------
class ListRolesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roles = user_selectors.get_all_roles()
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data)

# -----------------------------
# Misc
# -----------------------------
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class UserDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        user = user_selectors.get_user_by_id(user_id)
        if user:
            serializer = UserSerializer(user)
            return Response(serializer.data)
        return Response(
            {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND
        )

    def put(self, request, user_id):
        user = user_selectors.get_user_by_id(user_id)
        if not user:
            return Response(
                {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
