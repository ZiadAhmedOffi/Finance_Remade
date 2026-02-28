from rest_framework import serializers
from .models import Fund, FundLog
from django.contrib.auth import get_user_model

User = get_user_model()

class FundSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    steering_committee = serializers.SerializerMethodField()

    class Meta:
        model = Fund
        fields = [
            "id",
            "name",
            "description",
            "created_by",
            "created_by_email",
            "created_at",
            "is_active",
            "steering_committee",
        ]
        read_only_fields = ["created_by", "created_at"]

    def get_steering_committee(self, obj):
        from users.models import UserRoleAssignment
        assignments = UserRoleAssignment.objects.filter(
            fund=obj, 
            role__name="STEERING_COMMITTEE"
        ).select_related("user")
        return [assignment.user.email for assignment in assignments]

class FundLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)
    target_fund_name = serializers.EmailField(source="target_fund.name", read_only=True)

    class Meta:
        model = FundLog
        fields = [
            "id",
            "actor",
            "actor_email",
            "target_fund",
            "target_fund_name",
            "action",
            "success",
            "metadata",
            "timestamp",
        ]
