from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from users.models import User, Role, UserRoleAssignment, AuditLog


# -----------------------------
# JWT Login Serializer
# -----------------------------
class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login. Validates credentials, checks if user is active
    and not deleted.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = (data.get("email") or "").strip()
        password = data.get("password")

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")

        if user.status != "ACTIVE":
            raise serializers.ValidationError("User is not approved.")

        if user.is_deleted:
            raise serializers.ValidationError("User account is deactivated.")

        data["user"] = user
        return data


# -----------------------------
# Apply For Access Serializer
# -----------------------------
class ApplyAccessSerializer(serializers.ModelSerializer):
    """
    Serializer for new user applications. Captures user details and 
    sets initial status to PENDING.
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "company",
            "job_title",
            "phone_number",
        ]

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized_email

    def validate(self, attrs):
        candidate_user = User(
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(
            password=password,
            status="PENDING",
            is_active=False,
            **validated_data,
        )


# -----------------------------
# Role Serializer
# -----------------------------
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "description"]


# -----------------------------
# User Role Assignment Serializer
# -----------------------------
class UserRoleAssignmentSerializer(serializers.ModelSerializer):
    role = RoleSerializer()
    fund_name = serializers.CharField(source="fund.name", read_only=True)
    portfolio_name = serializers.CharField(source="real_estate_portfolio.name", read_only=True)

    class Meta:
        model = UserRoleAssignment
        fields = ["id", "role", "fund", "fund_name", "real_estate_portfolio", "portfolio_name", "dividend_treatment"]


# -----------------------------
# User Serializer (for safe data exposure)
# -----------------------------
class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "company",
            "job_title",
            "phone_number",
            "status",
            "is_active",
            "is_staff",
            "roles",
        ]

    def get_roles(self, obj):
        # Use the related_name 'role_assignments' from the User model
        assignments = obj.role_assignments.all()
        return UserRoleAssignmentSerializer(assignments, many=True).data


# -----------------------------
# Audit Log Serializer
# -----------------------------
class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for system audit logs. Includes actor email, target email,
    and fund name for easier readability.
    """
    actor_email = serializers.EmailField(source="actor.email", read_only=True)
    target_user_email = serializers.EmailField(source="target_user.email", read_only=True)
    fund_name = serializers.CharField(source="fund.name", read_only=True)
    portfolio_name = serializers.CharField(source="real_estate_portfolio.name", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor_email",
            "target_user_email",
            "action",
            "fund_name",
            "portfolio_name",
            "metadata",
            "ip_address",
            "timestamp",
        ]
