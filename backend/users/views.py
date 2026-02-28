from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError

from users.models import User, Role, Fund, UserRoleAssignment
from users.serializers import (
    LoginSerializer,
    ApplyAccessSerializer,
    UserSerializer,
    RoleSerializer,
    AuditLogSerializer,
)
from users.permissions import IsAccessManager
from users.services.permission_service import PermissionService
from users.services.audit_service import AuditService
from users.models import AuditLog

# -----------------------------
# JWT Custom Token Serializer
# -----------------------------
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT Token Serializer that adds extra claims to the token
    such as email, staff status, superuser status, and assigned roles.
    """
    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)
        token["email"] = user.email
        token["is_staff"] = user.is_staff
        token["is_superuser"] = user.is_superuser
        roles = user.role_assignments.select_related("role", "fund").all()
        token["roles"] = [
            {
                "role": role.role.name,
                "fund": role.fund.name if role.fund else None,
            }
            for role in roles
        ]
        return token

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        request = self.context.get("request")
        ip = request.META.get("REMOTE_ADDR") if request else None

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            AuditService.log_event(
                actor=None,
                action="LOGIN_FAILED",
                description=f"Failed login attempt for email: {email}",
                ip_address=ip
            )
            raise ValidationError("Invalid credentials.")

        if not user.check_password(password):
            AuditService.log_event(
                actor=user,
                action="LOGIN_FAILED",
                description=f"Failed login attempt (invalid password) for user: {email}",
                ip_address=ip
            )
            raise ValidationError("Invalid credentials.")

        if not user.is_active:
            AuditService.log_event(
                actor=user,
                action="LOGIN_FAILED",
                description=f"Failed login attempt (inactive account) for user: {email}",
                ip_address=ip
            )
            raise ValidationError("User account is not active.")

        # Log success
        AuditService.log_event(
            actor=user,
            action="LOGIN_SUCCESS",
            description=f"User {email} logged in successfully.",
            ip_address=ip
        )

        # Update the last_login_ip field
        if request:
            user.last_login_ip = ip
            user.save(update_fields=["last_login_ip"])

        # Manually create the token
        refresh = self.get_token(user)

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
        active_users = User.objects.filter(status="ACTIVE", is_deleted=False).order_by("email")
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
        pending_users = User.objects.filter(status="PENDING", is_deleted=False).order_by("-date_joined")
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
            user = User.objects.get(id=user_id, status="PENDING")
        except User.DoesNotExist:
            return Response(
                {"error": "User not found or has already been processed."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.status = "ACTIVE"
        user.is_active = True
        user.save(update_fields=["status", "is_active"])

        AuditService.log(
            actor=request.user,
            action="USER_APPROVED",
            target_user=user,
            metadata={"description": f"User {user.email} was approved."},
            ip=request.META.get("REMOTE_ADDR"),
        )

        return Response({"message": "User approved successfully."})

class RejectUserView(APIView):
    """
    API view to reject a pending user application.
    Updates user status to REJECTED.
    """
    permission_classes = [IsAccessManager]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, status="PENDING")
        except User.DoesNotExist:
            return Response(
                {"error": "User not found or has already been processed."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.status = "REJECTED"
        user.is_active = False
        user.save(update_fields=["status", "is_active"])

        AuditService.log(
            actor=request.user,
            action="USER_REJECTED",
            target_user=user,
            metadata={"description": f"User {user.email} was rejected."},
            ip=request.META.get("REMOTE_ADDR"),
        )

        return Response({"message": "User rejected successfully."})

class DeactivateUserView(APIView):
    """
    API view to deactivate an existing user.
    Sets is_active to False and status to REJECTED.
    """
    permission_classes = [IsAccessManager]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        user.is_active = False
        user.status = "REJECTED"
        user.save()

        AuditService.log(
            actor=request.user,
            action="USER_SOFT_DELETED",
            target_user=user,
            metadata={"description": f"User {user.email} was deactivated."},
            ip=request.META.get("REMOTE_ADDR")
        )

        return Response({"message": "User deactivated successfully."})

class AssignRoleView(APIView):
    """
    API view to assign a role (and optionally a fund) to a user.
    Enforces hierarchical restrictions for Super Admin and Access Manager roles.
    """
    permission_classes = [IsAccessManager]

    def post(self, request, user_id):
        role_id = request.data.get("role_id")
        fund_id = request.data.get("fund_id")

        try:
            target_user = User.objects.get(id=user_id)
            role = Role.objects.get(id=role_id)
        except (User.DoesNotExist, Role.DoesNotExist):
            return Response({"error": "User or Role not found."}, status=status.HTTP_404_NOT_FOUND)

        is_super_admin = PermissionService.is_super_admin(request.user)
        
        if role.name in ["SUPER_ADMIN", "ACCESS_MANAGER"] and not is_super_admin:
            return Response(
                {"error": "Only Super Admins can assign Admin/Manager roles."},
                status=status.HTTP_403_FORBIDDEN
            )

        fund = None
        if role.name in ["INVESTOR", "STEERING_COMMITTEE"]:
            if not fund_id:
                return Response(
                    {"error": f"Role {role.name} requires a fund."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                fund = Fund.objects.get(id=fund_id)
            except Fund.DoesNotExist:
                return Response({"error": "Fund not found."}, status=status.HTTP_404_NOT_FOUND)

        assignment, created = UserRoleAssignment.objects.get_or_create(
            user=target_user,
            role=role,
            fund=fund,
            defaults={"assigned_by": request.user}
        )

        if not created:
            return Response({"message": "Role already assigned."})

        if not target_user.is_active or target_user.status != "ACTIVE":
            target_user.is_active = True
            target_user.status = "ACTIVE"
            target_user.save(update_fields=["is_active", "status"])

        return Response({"message": "Role assigned successfully."})

class RemoveRoleView(APIView):
    """
    API view to remove a specific role assignment from a user.
    """
    permission_classes = [IsAccessManager]

    def post(self, request, user_id):
        role_id = request.data.get("role_id")
        fund_id = request.data.get("fund_id")

        try:
            target_user = User.objects.get(id=user_id)
            role = Role.objects.get(id=role_id)
        except (User.DoesNotExist, Role.DoesNotExist):
            return Response({"error": "User or Role not found."}, status=status.HTTP_404_NOT_FOUND)

        is_super_admin = PermissionService.is_super_admin(request.user)
        
        if role.name in ["SUPER_ADMIN", "ACCESS_MANAGER"] and not is_super_admin:
            return Response(
                {"error": "Only Super Admins can remove Admin/Manager roles."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            assignment = UserRoleAssignment.objects.get(
                user=target_user,
                role=role,
                fund=fund_id if fund_id else None
            )
            assignment.delete()
            
            AuditService.log(
                actor=request.user,
                action="ROLE_REMOVED",
                target_user=target_user,
                metadata={"description": f"Role {role.name} was removed from {target_user.email}."},
                ip=request.META.get("REMOTE_ADDR")
            )
            
            return Response({"message": "Role removed successfully."})
        except UserRoleAssignment.DoesNotExist:
            return Response({"error": "Role assignment not found."}, status=status.HTTP_404_NOT_FOUND)

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
        logs = AuditLog.objects.all().select_related("actor", "target_user", "fund").order_by("-timestamp")
        paginator = AuditLogPagination()
        result_page = paginator.paginate_queryset(logs, request)
        serializer = AuditLogSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

# -----------------------------
# Metadata Lists
# -----------------------------
class FundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fund
        fields = ["id", "name"]

class ListFundsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        funds = Fund.objects.all()
        serializer = FundSerializer(funds, many=True)
        return Response(serializer.data)

class ListRolesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roles = Role.objects.all()
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
        try:
            user = User.objects.get(id=user_id)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
