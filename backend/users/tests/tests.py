from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from users.models import User, AuditLog, Role, UserRoleAssignment
import uuid

class AuditLogTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User"
        )
        self.user.is_active = True
        self.user.save()

    def test_permission_denied_logs_audit_event(self):
        """
        Verify that a PermissionDenied error (403) is correctly caught by the 
        custom exception handler and logs an event to AuditLog without crashing (500).
        """
        self.client.force_authenticate(user=self.user)
        
        # Accessing pending users requires IsAccessManager permission
        # This user does not have it, so it should return 403
        url = reverse("pending-users")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Check if AuditLog entry was created
        audit_logs = AuditLog.objects.filter(
            actor=self.user,
            action="ACCESS_DENIED"
        )
        self.assertEqual(audit_logs.count(), 1)
        log = audit_logs.first()
        self.assertEqual(log.metadata.get("target_model"), "PendingUsersView")

    def test_unauthenticated_access_denied_logs_audit_event(self):
        """
        Verify that unauthenticated access also logs an event.
        """
        url = reverse("pending-users")
        response = self.client.get(url)
        
        # DRF returns 401 or 403 depending on authentication schemes
        # By default, if no auth is provided, it might return 401 or 403
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        
        # Check if AuditLog entry was created for unauthenticated access
        audit_logs = AuditLog.objects.filter(
            actor=None,
            action="UNAUTHENTICATED_ACCESS_DENIED"
        )
        self.assertEqual(audit_logs.count(), 1)
