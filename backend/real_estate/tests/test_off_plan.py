from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from real_estate.models import RealEstatePortfolio, Property, RealEstateAssumptions, OffPlanDetails, OffPlanMilestone
from users.models import Role, UserRoleAssignment

User = get_user_model()

class OffPlanModelTests(APITestCase):
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
        
        self.portfolio = RealEstatePortfolio.objects.create(
            name="Off-Plan Portfolio",
            created_by=self.admin_user
        )
        RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date="2024-01-01",
            active_scenario="BASE",
            selling_fee_percentage=Decimal("2.00")
        )
        
        self.property_obj = Property.objects.create(
            portfolio=self.portfolio,
            name="Off-Plan Property",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="OFF_PLAN",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal("1000000.00"),
            monthly_rent=Decimal("0.00"),
            acq_fee_percentage=Decimal("0.00"),
            appreciation_rate_percentage=Decimal("0.00"),
            vacancy_rate_percentage=Decimal("0.00")
        )

    def test_off_plan_details_creation(self):
        # Accessing the off-plan model should trigger creation of details
        url = f"/api/real-estate/{self.portfolio.id}/off-plan/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['property_name'], "Off-Plan Property")
        
        # Verify details in DB
        self.assertTrue(OffPlanDetails.objects.filter(property=self.property_obj).exists())
        self.assertEqual(OffPlanMilestone.objects.filter(property=self.property_obj).count(), 4)

    def test_update_off_plan_details(self):
        # Trigger creation first
        self.client.get(f"/api/real-estate/{self.portfolio.id}/off-plan/")
        
        url = f"/api/real-estate/{self.portfolio.id}/off-plan/{self.property_obj.id}/details/"
        data = {
            "appreciation_rate_at_completion": "30.00",
            "expected_completion_date": "2026-06-01"
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        details = OffPlanDetails.objects.get(property=self.property_obj)
        self.assertEqual(float(details.appreciation_rate_at_completion), 30.00)

    def test_payment_schedule_and_xirr(self):
        # Trigger creation first
        self.client.get(f"/api/real-estate/{self.portfolio.id}/off-plan/")
        
        # Pay everything in Down Payment (20%) + another milestone (80%)
        OffPlanMilestone.objects.filter(property=self.property_obj, milestone_name="Down Payment").update(
            date=date(2024, 1, 1), percentage_of_price=Decimal("100.00")
        )
        OffPlanMilestone.objects.filter(property=self.property_obj).exclude(
            milestone_name__in=["Down Payment", "Sale at Completion"]
        ).update(percentage_of_price=Decimal("0.00"))
        
        # Update details for 1 year completion and 10% appreciation
        details = OffPlanDetails.objects.get(property=self.property_obj)
        details.expected_completion_date = date(2025, 1, 1)
        details.appreciation_rate_at_completion = Decimal("10.00")
        details.sale_at_completion = True
        details.save()
        
        url = f"/api/real-estate/{self.portfolio.id}/off-plan/{self.property_obj.id}/schedule/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        metrics = response.data['metrics']
        # Purchase 1M, Completion Value 1.1M, Selling Fee 2% -> 1.1M * 0.98 = 1.078M
        # Profit = 1.078M - 1M = 78k
        self.assertEqual(float(metrics['total_expected_profit']), 78000.00)
        # XIRR should be around 7.8% (since it's exactly 1 year)
        self.assertAlmostEqual(float(metrics['xirr']), 7.8, delta=0.5)
