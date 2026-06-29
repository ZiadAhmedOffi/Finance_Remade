from django.urls import path
from users.api.views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    ApplyForAccessView,
    CurrentUserView,
    PendingUsersView,
    ActiveUsersView,
    ApproveUserView,
    RejectUserView,
    DeactivateUserView,
    ResetPasswordView,
    AssignRoleView,
    RemoveRoleView,
    AuditLogView,
    ListRolesView,
    UserDetailView,
    UpdateDividendTreatmentView,
)

urlpatterns = [
    # --- Authentication ---
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("apply/", ApplyForAccessView.as_view(), name="apply-for-access"),

    # --- User Management (Admin/Manager) ---
    path("pending/", PendingUsersView.as_view(), name="pending-users"),
    path("active/", ActiveUsersView.as_view(), name="active-users"),
    path("approve/<uuid:user_id>/", ApproveUserView.as_view(), name="approve-user"),
    path("reject/<uuid:user_id>/", RejectUserView.as_view(), name="reject-user"),
    path("deactivate/<uuid:user_id>/", DeactivateUserView.as_view(), name="deactivate-user"),
    path("reset-password/<uuid:user_id>/", ResetPasswordView.as_view(), name="reset-password"),
    path("assign-role/<uuid:user_id>/", AssignRoleView.as_view(), name="assign-role"),
    path("remove-role/<uuid:user_id>/", RemoveRoleView.as_view(), name="remove-role"),
    path("logs/", AuditLogView.as_view(), name="audit-logs"),
    path("roles/", ListRolesView.as_view(), name="list-roles"),
    path("roles/<uuid:assignment_id>/dividend-treatment/", UpdateDividendTreatmentView.as_view(), name="update-dividend-treatment"),

    # --- User Profile ---
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),
]
