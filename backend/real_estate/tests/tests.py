from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from ..models import RealEstatePortfolio, RealEstateAssumptions
from users.models import Role, UserRoleAssignment

User = get_user_model()

class RealEstateAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com", 
            password="password123",
            is_active=True,
            status="ACTIVE"
        )
        self.client.force_authenticate(user=self.user)
        
        # Assign SUPER_ADMIN role
        super_admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", is_system_role=True)
        UserRoleAssignment.objects.create(user=self.user, role=super_admin_role)

    def test_create_portfolio_creates_assumptions(self):
        url = reverse('real-estate-portfolio-list')
        data = {
            "name": "Test Portfolio",
            "description": "A test description",
            "region": "Global"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        portfolio = RealEstatePortfolio.objects.get(name="Test Portfolio")
        self.assertEqual(portfolio.description, "A test description")
        
        # Check if assumptions were created automatically
        self.assertTrue(RealEstateAssumptions.objects.filter(portfolio=portfolio).exists())
        assumptions = portfolio.assumptions
        self.assertEqual(assumptions.active_scenario, "BASE")

    def test_update_assumptions(self):
        portfolio = RealEstatePortfolio.objects.create(name="Update Test", created_by=self.user)
        # In actual service, assumptions are created during portfolio creation. 
        # But for model-level test we can create it.
        assumptions = RealEstateAssumptions.objects.create(
            portfolio=portfolio,
            inception_date="2024-01-01"
        )
        
        url = reverse('real-estate-portfolio-assumptions', kwargs={'pk': portfolio.id})
        data = {
            "active_scenario": "BULL",
            "forecast_horizon": 15
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        assumptions.refresh_from_db()
        self.assertEqual(assumptions.active_scenario, "BULL")
        self.assertEqual(assumptions.forecast_horizon, 15)

    def test_get_portfolios(self):
        RealEstatePortfolio.objects.create(name="Portfolio 1", created_by=self.user)
        RealEstatePortfolio.objects.create(name="Portfolio 2", created_by=self.user)
        
        url = reverse('real-estate-portfolio-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
