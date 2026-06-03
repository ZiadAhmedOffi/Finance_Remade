from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api.views import (
    RealEstatePortfolioViewSet,
    JurisdictionViewSet,
    TaxRuleViewSet
)

router = DefaultRouter()
router.register(r'jurisdictions', JurisdictionViewSet, basename='jurisdiction')
router.register(r'tax-rules', TaxRuleViewSet, basename='tax-rule')
router.register(r'', RealEstatePortfolioViewSet, basename='real-estate-portfolio')

urlpatterns = [
    # Explicit patterns for complex nested actions to avoid router issues
    path('<uuid:pk>/off-plan/<uuid:property_id>/schedule/', RealEstatePortfolioViewSet.as_view({'get': 'off_plan_schedule', 'post': 'off_plan_schedule'}), name='portfolio-off-plan-schedule'),
    path('<uuid:pk>/off-plan/milestones/<uuid:milestone_id>/', RealEstatePortfolioViewSet.as_view({'patch': 'manage_milestone', 'delete': 'manage_milestone'}), name='portfolio-manage-milestone'),
    
    # Bookkeeping Explicit Paths
    path('<uuid:pk>/ledgers/', RealEstatePortfolioViewSet.as_view({'get': 'ledgers'}), name='portfolio-ledgers'),
    path('<uuid:pk>/ledgers/initialize/', RealEstatePortfolioViewSet.as_view({'post': 'initialize_ledger'}), name='portfolio-ledgers-initialize'),
    path('<uuid:pk>/ledgers/templates/', RealEstatePortfolioViewSet.as_view({'get': 'transaction_templates'}), name='portfolio-ledgers-templates'),
    path('<uuid:pk>/ledgers/<uuid:year_id>/trial-balance/', RealEstatePortfolioViewSet.as_view({'get': 'trial_balance'}), name='portfolio-ledgers-trial-balance'),
    path('<uuid:pk>/ledgers/<uuid:year_id>/accounts/<uuid:account_id>/t-account/', RealEstatePortfolioViewSet.as_view({'get': 't_account'}), name='portfolio-ledgers-t-account'),
    path('<uuid:pk>/ledgers/<uuid:year_id>/transactions/', RealEstatePortfolioViewSet.as_view({'post': 'manual_transaction'}), name='portfolio-ledgers-transactions'),
    path('<uuid:pk>/ledgers/<uuid:year_id>/sync-cash-flow/', RealEstatePortfolioViewSet.as_view({'post': 'sync_cash_flow'}), name='portfolio-ledgers-sync-cash-flow'),
    path('<uuid:pk>/ledgers/<uuid:year_id>/close/', RealEstatePortfolioViewSet.as_view({'post': 'close_ledger'}), name='portfolio-ledgers-close'),
    path('<uuid:pk>/ledgers/<uuid:year_id>/delete/', RealEstatePortfolioViewSet.as_view({'delete': 'delete_ledger'}), name='portfolio-ledgers-delete'),

    path('', include(router.urls)),
]
