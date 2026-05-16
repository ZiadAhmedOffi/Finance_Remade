from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api.views import RealEstatePortfolioViewSet

router = DefaultRouter()
router.register(r'', RealEstatePortfolioViewSet, basename='real-estate-portfolio')

urlpatterns = [
    # Explicit patterns for complex nested actions to avoid router issues
    path('<uuid:pk>/off-plan/<uuid:property_id>/schedule/', RealEstatePortfolioViewSet.as_view({'get': 'off_plan_schedule', 'post': 'off_plan_schedule'}), name='portfolio-off-plan-schedule'),
    path('<uuid:pk>/off-plan/milestones/<uuid:milestone_id>/', RealEstatePortfolioViewSet.as_view({'patch': 'manage_milestone', 'delete': 'manage_milestone'}), name='portfolio-manage-milestone'),
    path('', include(router.urls)),
]
