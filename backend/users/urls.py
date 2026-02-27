from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from users.views import (
    CustomTokenObtainPairView,
    ApplyForAccessView,
    CurrentUserView,
    PendingUsersView,
    ActiveUsersView,
    ApproveUserView,
    RejectUserView,
    DeactivateUserView,
    AssignRoleView,
    RemoveRoleView,
    AuditLogView,
    ListFundsView,
    ListRolesView,
    UserDetailView,
)

urlpatterns = [
    # --- Authentication ---
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("apply/", ApplyForAccessView.as_view(), name="apply-for-access"),

    # --- User Management (Admin/Manager) ---
    path("pending/", PendingUsersView.as_view(), name="pending-users"),
    path("active/", ActiveUsersView.as_view(), name="active-users"),
    path("approve/<uuid:user_id>/", ApproveUserView.as_view(), name="approve-user"),
    path("reject/<uuid:user_id>/", RejectUserView.as_view(), name="reject-user"),
    path("deactivate/<uuid:user_id>/", DeactivateUserView.as_view(), name="deactivate-user"),
    path("assign-role/<uuid:user_id>/", AssignRoleView.as_view(), name="assign-role"),
    path("remove-role/<uuid:user_id>/", RemoveRoleView.as_view(), name="remove-role"),
    path("logs/", AuditLogView.as_view(), name="audit-logs"),
    path("funds/", ListFundsView.as_view(), name="list-funds"),
    path("roles/", ListRolesView.as_view(), name="list-roles"),

    # --- User Profile ---
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),
]
