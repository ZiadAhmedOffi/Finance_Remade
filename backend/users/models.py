import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


# =====================================================
# Custom User Manager
# =====================================================

class CustomUserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must provide an email")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, password, **extra_fields)


# =====================================================
# Custom User Model
# =====================================================

class User(AbstractBaseUser, PermissionsMixin):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True, db_index=True)

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)

    is_active = models.BooleanField(default=False, db_index=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # Soft delete (for compliance & audit retention)
    is_deleted = models.BooleanField(default=False, db_index=True)

    date_joined = models.DateTimeField(default=timezone.now)

    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_deleted"]),
        ]
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email


# =====================================================
# Role Model (Flexible)
# =====================================================

class Role(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)

    is_system_role = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["is_system_role"]),
        ]

    def __str__(self):
        return self.name


# =====================================================
# Fund (minimal reference)
# =====================================================
# to be used for the future funds app
class Fund(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255, unique=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# =====================================================
# User Role Assignment
# =====================================================

class UserRoleAssignment(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
        db_index=True
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="assigned_users",
        db_index=True
    )

    fund = models.ForeignKey(
        Fund,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="role_assignments",
        db_index=True
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="roles_assigned"
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "role", "fund")
        indexes = [
            models.Index(fields=["user", "role"]),
            models.Index(fields=["user", "fund"]),
            models.Index(fields=["role", "fund"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.role.name}"


# =====================================================
# Audit Log (Immutable)
# =====================================================

class AuditLog(models.Model):

    ACTION_CHOICES = [
        ("USER_APPROVED", "User Approved"),
        ("USER_SOFT_DELETED", "User Soft Deleted"),
        ("ROLE_ASSIGNED", "Role Assigned"),
        ("ROLE_REMOVED", "Role Removed"),
        ("FUND_CREATED", "Fund Created"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_actions"
    )

    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_targeted"
    )

    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)

    fund = models.ForeignKey(
        Fund,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    metadata = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["action"]),
            models.Index(fields=["actor"]),
        ]

    def __str__(self):
        return f"{self.action} - {self.timestamp}"