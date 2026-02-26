from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from users.views import (
    CustomTokenObtainPairView,
    ApplyForAccessView,
    CurrentUserView,
    PendingUsersView,
    ApproveUserView,
    RejectUserView,
    UserDetailView,
)

urlpatterns = [
    # --- Authentication ---
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("apply/", ApplyForAccessView.as_view(), name="apply-for-access"),

    # --- User Management (Admin/Manager) ---
    path("pending/", PendingUsersView.as_view(), name="pending-users"),
    path("approve/<uuid:user_id>/", ApproveUserView.as_view(), name="approve-user"),
    path("reject/<uuid:user_id>/", RejectUserView.as_view(), name="reject-user"),

    # --- User Profile ---
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),
]