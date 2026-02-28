from django.urls import path
from .views import FundListView, FundDetailView, FundLogListView

urlpatterns = [
    path("", FundListView.as_view(), name="fund-list"),
    path("<uuid:fund_id>/", FundDetailView.as_view(), name="fund-detail"),
    path("<uuid:fund_id>/logs/", FundLogListView.as_view(), name="fund-logs"),
]
