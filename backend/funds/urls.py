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
    FundPerformanceView,
    InvestmentRoundListView,
    InvestmentRoundDetailView,
    InvestorListView,
    InvestorActionListView,
    InvestorActionDetailView,
    InvestorDashboardView
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
    path("<uuid:fund_id>/investment-rounds/", InvestmentRoundListView.as_view(), name="fund-investment-rounds"),
    path("<uuid:fund_id>/investment-rounds/<uuid:round_id>/", InvestmentRoundDetailView.as_view(), name="fund-investment-round-detail"),
    path("<uuid:fund_id>/performance/", FundPerformanceView.as_view(), name="fund-performance"),
    
    # Investor Actions & Dashboard
    path("investors/", InvestorListView.as_view(), name="investor-list"),
    path("investor-actions/", InvestorActionListView.as_view(), name="investor-action-list"),
    path("investor-actions/<uuid:action_id>/", InvestorActionDetailView.as_view(), name="investor-action-detail"),
    path("investor-dashboard/", InvestorDashboardView.as_view(), name="investor-dashboard"),
]
