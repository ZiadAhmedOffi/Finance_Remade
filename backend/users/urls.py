from django.urls import path
from users.views import (
    CustomTokenObtainPairView,
    ApplyForAccessView,
    ApproveUserView,
)

urlpatterns = [
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("apply/", ApplyForAccessView.as_view(), name="apply-access"),
    path("approve/<uuid:user_id>/", ApproveUserView.as_view(), name="approve-user"),
]