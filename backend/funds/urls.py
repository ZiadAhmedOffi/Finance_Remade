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
    InvestorDashboardView,
    RiskAssessmentListView,
    InvestorLogView,
    PossibleCapitalSourceListView,
    PossibleCapitalSourceDetailView,
    ReportListView,
    ReportDetailView,
    ReportRegenerateView,
    PublicReportView,
    ExcelTemplateView,
    ExcelIngestView
)

urlpatterns = [
    path("", FundListView.as_view(), name="fund-list"),
    path("<uuid:fund_id>/", FundDetailView.as_view(), name="fund-detail"),
    path("<uuid:fund_id>/logs/", FundLogListView.as_view(), name="fund-logs"),
    path("<uuid:fund_id>/model-inputs/", ModelInputDetailView.as_view(), name="fund-model-inputs"),
    path("<uuid:fund_id>/excel-template/", ExcelTemplateView.as_view(), name="fund-excel-template"),
    path("<uuid:fund_id>/excel-ingest/", ExcelIngestView.as_view(), name="fund-excel-ingest"),

    path("<uuid:fund_id>/deals/", InvestmentDealListView.as_view(), name="fund-deals"),
    path("<uuid:fund_id>/deals/<uuid:deal_id>/", InvestmentDealDetailView.as_view(), name="fund-deal-detail"),
    path("<uuid:fund_id>/current-deals/", CurrentDealListView.as_view(), name="fund-current-deals"),
    path("<uuid:fund_id>/current-deals/<uuid:deal_id>/", CurrentDealDetailView.as_view(), name="current-deal-detail"),
    path("<uuid:fund_id>/risk-assessments/", RiskAssessmentListView.as_view(), name="risk-assessment-list"),
    path("<uuid:fund_id>/investor-log/", InvestorLogView.as_view(), name="fund-investor-log"),

    path("<uuid:fund_id>/investment-rounds/", InvestmentRoundListView.as_view(), name="fund-investment-rounds"),
    path("<uuid:fund_id>/investment-rounds/<uuid:round_id>/", InvestmentRoundDetailView.as_view(), name="fund-investment-round-detail"),
    path("<uuid:fund_id>/performance/", FundPerformanceView.as_view(), name="fund-performance"),
    
    # Reports
    path("reports/", ReportListView.as_view(), name="report-list"),
    path("reports/<uuid:report_id>/", ReportDetailView.as_view(), name="report-detail"),
    path("reports/<uuid:report_id>/regenerate/", ReportRegenerateView.as_view(), name="report-regenerate"),
    path("reports/public/<slug:slug>/", PublicReportView.as_view(), name="public-report-view"),

    # Investor Actions & Dashboard
    path("investors/", InvestorListView.as_view(), name="investor-list"),
    path("investor-actions/", InvestorActionListView.as_view(), name="investor-action-list"),
    path("investor-actions/<uuid:action_id>/", InvestorActionDetailView.as_view(), name="investor-action-detail"),
    path("investor-dashboard/", InvestorDashboardView.as_view(), name="investor-dashboard"),

    # Capital Sources
    path("<uuid:fund_id>/capital-sources/", PossibleCapitalSourceListView.as_view(), name="capital-source-list"),
    path("capital-sources/<uuid:source_id>/", PossibleCapitalSourceDetailView.as_view(), name="capital-source-detail"),
]
