from decimal import Decimal
from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from real_estate.models import RealEstatePortfolio, RealEstateAssumptions, Property, OffPlanDetails, OffPlanMilestone
from users.models import Role, UserRoleAssignment

User = get_user_model()

class OffPlanE2ETests(APITestCase):
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
        
        # 1. Create Portfolio
        url = "/api/real-estate/"
        data = {"name": "E2E Off-Plan Portfolio"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.portfolio_id = response.data['id']
        
        # 2. Setup Assumptions
        url = f"/api/real-estate/{self.portfolio_id}/assumptions/"
        data = {
            "inception_date": "2024-01-01",
            "forecast_horizon": 5,
            "selling_fee_percentage": "2.00"
        }
        self.client.patch(url, data, format='json')

    def test_off_plan_to_sale_e2e(self):
        # 3. Add Off-Plan Property
        url = f"/api/real-estate/{self.portfolio_id}/properties/"
        data = {
            "name": "E2E Property",
            "city": "Dubai",
            "country": "UAE",
            "property_type": "RESIDENTIAL",
            "financing_type": "ALL_CASH",
            "status": "OFF_PLAN",
            "purchase_date": "2024-01-01",
            "purchase_price": "1000000.00",
            "monthly_rent": "0.00",
            "acq_fee_percentage": "0.00",
            "appreciation_rate_percentage": "0.00",
            "vacancy_rate_percentage": "0.00"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        property_id = response.data['id']

        # 4. Update Off-Plan Details: Set Sale at Completion
        # Trigger creation by getting off-plan model
        self.client.get(f"/api/real-estate/{self.portfolio_id}/off-plan/")
        
        url = f"/api/real-estate/{self.portfolio_id}/off-plan/{property_id}/details/"
        data = {
            "expected_completion_date": "2026-01-01",
            "appreciation_rate_at_completion": "20.00",
            "sale_at_completion": True
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['sale_at_completion'])

        # 4b. Set milestones to 100% to isolate sale proceeds in CF
        OffPlanMilestone.objects.filter(property_id=property_id, milestone_name="Down Payment").update(percentage_of_price=Decimal("100.00"))
        OffPlanMilestone.objects.filter(property_id=property_id).exclude(milestone_name="Down Payment").update(percentage_of_price=Decimal("0.00"))

        # 5. Verify Cash Flow
        url = f"/api/real-estate/{self.portfolio_id}/cash-flow/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 2026 should show the sale inflow
        # 1M * 1.20 * (1 - 0.02) = 1,176,000
        # 2027 should show None
        properties_cf = response.data['properties'][property_id]['annual_cf']
        self.assertEqual(float(properties_cf[2026]), 1176000.00)
        self.assertIsNone(properties_cf.get(2027))
