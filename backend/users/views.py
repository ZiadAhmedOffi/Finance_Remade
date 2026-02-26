from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.models import User
from users.serializers import (
    LoginSerializer,
    ApplyAccessSerializer,
    UserSerializer,
)
from users.permissions import IsAccessManager
from users.services.audit_service import AuditService
from rest_framework.exceptions import ValidationError


# -----------------------------
# JWT Custom Token Serializer
# -----------------------------
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
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

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("Invalid credentials.")

        if not user.check_password(password):
            raise ValidationError("Invalid credentials.")

        if not user.is_active:
            raise ValidationError("User account is not active.")

        # Update the last_login_ip field
        request = self.context.get("request")
        if request:
            user.last_login_ip = request.META.get("REMOTE_ADDR")
            user.save(update_fields=["last_login_ip"])

        # Manually create the token
        refresh = self.get_token(user)

        data = {}
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        return data


# -----------------------------
# JWT Token View
# -----------------------------
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# -----------------------------
# Apply for Access
# -----------------------------
class ApplyForAccessView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ApplyAccessSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        # Log the application submission
        AuditService.log(
            actor=None,  # No user is logged in yet
            action="USER_APPLICATION_SUBMITTED",
            target_user=user,
            metadata={"description": f"User {user.email} applied for access."},
            ip=request.META.get("REMOTE_ADDR"),
        )

        return Response(
            {"message": "Application submitted successfully. Please await approval."},
            status=status.HTTP_201_CREATED,
        )


# -----------------------------
# Get Current User
# -----------------------------
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


# -----------------------------
# Pending Users (for Admins)
# -----------------------------
class PendingUsersView(APIView):
    permission_classes = [IsAccessManager]

    def get(self, request):
        pending_users = User.objects.filter(status="PENDING", is_deleted=False)
        serializer = UserSerializer(pending_users, many=True)
        return Response(serializer.data)


# -----------------------------
# Approve User
# -----------------------------
class ApproveUserView(APIView):
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

        # Log the approval
        AuditService.log(
            actor=request.user,
            action="USER_APPROVED",
            target_user=user,
            metadata={"description": f"User {user.email} was approved."},
            ip=request.META.get("REMOTE_ADDR"),
        )

        return Response({"message": "User approved successfully."})


# -----------------------------
# Reject User
# -----------------------------
class RejectUserView(APIView):
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

        # Log the rejection
        AuditService.log(
            actor=request.user,
            action="USER_REJECTED",
            target_user=user,
            metadata={"description": f"User {user.email} was rejected."},
            ip=request.META.get("REMOTE_ADDR"),
        )

        return Response({"message": "User rejected successfully."})


# -----------------------------
# User Detail View (for Admins)
# -----------------------------
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