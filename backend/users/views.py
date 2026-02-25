from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.models import User
from users.serializers import LoginSerializer, ApplyAccessSerializer
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
        token["roles"] = [role.name for role in user.roles.all()]
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

        if user.status != "ACTIVE":
            raise ValidationError("User not approved.")

        if user.is_deleted:
            raise ValidationError("User account deactivated.")

        return super().validate({"username": user.email, "password": password})


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

        AuditService.log_event(
            actor=None,
            action="USER_APPLICATION_SUBMITTED",
            target_model="User",
            target_id=str(user.id),
            description=f"User {user.email} applied for access.",
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return Response(
            {"message": "Application submitted. Await approval."},
            status=status.HTTP_201_CREATED,
        )


# -----------------------------
# Approve User (Access Manager / Super Admin)
# -----------------------------
class ApproveUserView(APIView):
    permission_classes = [IsAccessManager]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, status="PENDING")
        except User.DoesNotExist:
            return Response(
                {"error": "User not found or already processed."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.status = "ACTIVE"
        user.is_active = True
        user.save()

        AuditService.log_event(
            actor=request.user,
            action="USER_APPROVED",
            target_model="User",
            target_id=str(user.id),
            description=f"User {user.email} approved.",
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return Response(
            {"message": "User approved successfully."}, status=status.HTTP_200_OK
        )