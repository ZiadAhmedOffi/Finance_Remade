from django.contrib.auth import authenticate
from rest_framework import serializers
from users.models import User, Role, UserRoleAssignment


# -----------------------------
# JWT Login Serializer
# -----------------------------
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = User.objects.get(email=email)
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

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = User(
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            company=validated_data.get("company", ""),
            job_title=validated_data.get("job_title", ""),
            phone_number=validated_data.get("phone_number", ""),
            status="PENDING",
            is_active=False,
        )
        user.set_password(password)
        user.save()
        return user


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

    class Meta:
        model = UserRoleAssignment
        fields = ["id", "role", "fund"]


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