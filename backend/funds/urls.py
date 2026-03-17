from django.urls import path
from .views import (
    FundListView, 
    FundDetailView, 
    FundLogListView, 
    ModelInputDetailView,
    InvestmentDealListView,
    InvestmentDealDetailView,
    CurrentDealListView,
    CurrentDealDetailView,
    FundPerformanceView
)

urlpatterns = [
    path("", FundListView.as_view(), name="fund-list"),
    path("<uuid:fund_id>/", FundDetailView.as_view(), name="fund-detail"),
    path("<uuid:fund_id>/logs/", FundLogListView.as_view(), name="fund-logs"),
    path("<uuid:fund_id>/model-inputs/", ModelInputDetailView.as_view(), name="fund-model-inputs"),
    path("<uuid:fund_id>/deals/", InvestmentDealListView.as_view(), name="fund-deals"),
    path("<uuid:fund_id>/deals/<uuid:deal_id>/", InvestmentDealDetailView.as_view(), name="fund-deal-detail"),
    path("<uuid:fund_id>/current-deals/", CurrentDealListView.as_view(), name="fund-current-deals"),
    path("<uuid:fund_id>/current-deals/<uuid:deal_id>/", CurrentDealDetailView.as_view(), name="fund-current-deal-detail"),
    path("<uuid:fund_id>/performance/", FundPerformanceView.as_view(), name="fund-performance"),
]
