from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from real_estate.models import RealEstatePortfolio, Property, FinancingEntry, RealEstateAssumptions
from users.models import Role, UserRoleAssignment

User = get_user_model()

class FinancingE2ETests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@test.com",
            password="password123",
            is_active=True,
            status="ACTIVE"
        )
        self.client.force_authenticate(user=self.admin_user)
        
        # Assign SUPER_ADMIN role
        super_admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", is_system_role=True)
        UserRoleAssignment.objects.create(user=self.admin_user, role=super_admin_role)

    def test_full_financing_lifecycle(self):
        # 1. Create Portfolio
        portfolio_data = {
            "name": "E2E Portfolio",
            "region": "Global"
        }
        portfolio_url = reverse('real-estate-portfolio-list')
        response = self.client.post(portfolio_url, portfolio_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        portfolio = RealEstatePortfolio.objects.get(name="E2E Portfolio")
        portfolio_id = str(portfolio.id)

        # 2. Add Property
        property_url = reverse('real-estate-portfolio-properties', kwargs={'pk': portfolio_id})
        property_data = {
            "name": "E2E Property",
            "city": "London",
            "country": "UK",
            "property_type": "COMMERCIAL",
            "financing_type": "MORTGAGED",
            "status": "HELD",
            "purchase_date": "2024-01-01",
            "purchase_price": "2000000.00",
            "monthly_rent": "10000.00",
            "other_operational_expenses": "1000.00",
            "acq_fee_percentage": "1.00",
            "appreciation_rate_percentage": "2.00",
            "vacancy_rate_percentage": "5.00"
        }
        response = self.client.post(property_url, property_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        property_id = response.data['id']

        # 3. Create Financing Entry
        financing_url = f"/api/real-estate/{portfolio_id}/financing/"
        financing_data = {
            "property": property_id,
            "loan_amount": "1500000.00",
            "base_interest_rate": "4.50",
            "tenor": 20,
            "payments_per_year": 12,
            "loan_start_date": "2024-02-01"
        }
        response = self.client.post(financing_url, financing_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry_id = response.data['id']

        # Verify Metrics and Scenario Adjustment
        # Default scenario is BASE (0% adjustment)
        response = self.client.get(financing_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = response.data['mortgages'][0]['metrics']
        self.assertEqual(metrics['ltv'], 75.00) # 1.5M / 2M
        self.assertEqual(metrics['effective_rate'], 4.50)

        # Change scenario to BEAR (+1.00% interest rate adjustment)
        assumptions_url = f"/api/real-estate/{portfolio_id}/assumptions/"
        self.client.patch(assumptions_url, {"active_scenario": "BEAR"}, format='json')

        response = self.client.get(financing_url)
        metrics = response.data['mortgages'][0]['metrics']
        self.assertEqual(metrics['effective_rate'], 5.50) # 4.5 + 1.0


        # 5. Check Amortization Schedule
        amort_url = f"/api/real-estate/{portfolio_id}/financing/{entry_id}/amortization/"
        response = self.client.get(amort_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 240) # 20 years * 12 months
        
        # 6. Check Portfolio Total Amortization
        total_amort_url = f"/api/real-estate/{portfolio_id}/financing/amortization-total/"
        response = self.client.get(total_amort_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
