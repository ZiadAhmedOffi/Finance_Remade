from django.contrib.auth import authenticate
from rest_framework import serializers
from users.models import User


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
        fields = ["email", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = User(
            email=validated_data["email"],
            username=validated_data["email"],
            status="PENDING",
            is_active=False,
        )
        user.set_password(password)
        user.save()
        return user