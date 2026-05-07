from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api.views import RealEstatePortfolioViewSet

router = DefaultRouter()
router.register(r'', RealEstatePortfolioViewSet, basename='real-estate-portfolio')

urlpatterns = [
    path('', include(router.urls)),
]
