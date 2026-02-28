import uuid
from django.db import models
from django.conf import settings

class Fund(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="funds_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name

class FundLog(models.Model):
    ACTION_CHOICES = [
        ("FUND_CREATED", "Fund Created"),
        ("FUND_DEACTIVATED", "Fund Deactivated"),
        ("FUND_INFO_UPDATED", "Fund Information Updated"),
        ("FUND_INFO_UPDATE_FAILED", "Fund Information Update Failed"),
        ("SC_MEMBER_ASSIGNED", "SC Member Assigned"),
        ("INVESTOR_ASSIGNED", "Investor Assigned"),
        ("ROLE_REMOVED", "Role Removed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fund_actions"
    )
    
    target_fund = models.ForeignKey(
        Fund,
        on_delete=models.CASCADE,
        related_name="logs"
    )
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    success = models.BooleanField(default=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.target_fund.name} by {self.actor}"
