from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from ..models import RealEstatePortfolio, RealEstateAssumptions, Property
from users.models import Role, UserRoleAssignment
from decimal import Decimal
import datetime

User = get_user_model()

class PropertyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create a superadmin
        self.admin_user = User.objects.create_user(
            email="admin@example.com", 
            password="password123",
            is_active=True
        )
        self.admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", is_system_role=True)
        UserRoleAssignment.objects.create(user=self.admin_user, role=self.admin_role)
        
        # Create a portfolio manager
        self.pm_user = User.objects.create_user(
            email="pm@example.com", 
            password="password123",
            is_active=True
        )
        self.pm_role, _ = Role.objects.get_or_create(name="PORTFOLIO_MANAGER", is_system_role=True)
        
        # Create an investor
        self.investor_user = User.objects.create_user(
            email="investor@example.com", 
            password="password123",
            is_active=True
        )
        self.investor_role, _ = Role.objects.get_or_create(name="INVESTOR", is_system_role=True)

        self.portfolio = RealEstatePortfolio.objects.create(name="Real Estate Portfolio", created_by=self.admin_user)
        self.assumptions = RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date="2024-01-01",
            acquisition_fee_percentage=Decimal('1.00'),
            default_appreciation_rate=Decimal('3.00'),
            default_vacancy_rate=Decimal('5.00'),
            property_mgmt_fee_percentage=Decimal('2.00'),
            maintenance_percentage_of_value=Decimal('1.00')
        )
        
        # Assign roles to portfolio
        UserRoleAssignment.objects.create(user=self.pm_user, role=self.pm_role, real_estate_portfolio=self.portfolio)
        UserRoleAssignment.objects.create(user=self.investor_user, role=self.investor_role, real_estate_portfolio=self.portfolio)

    def test_pm_can_add_property(self):
        self.client.force_authenticate(user=self.pm_user)
        url = reverse('real-estate-portfolio-properties', kwargs={'pk': self.portfolio.id})
        data = {
            "name": "Test Property",
            "city": "London",
            "country": "UK",
            "property_type": "RESIDENTIAL",
            "financing_type": "ALL_CASH",
            "purchase_date": "2024-01-01",
            "purchase_price": "1000000.00",
            "size": "100.00",
            "monthly_rent": "5000.00"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Property.objects.count(), 1)
        
        prop = Property.objects.first()
        # Verify snapshotted rates
        self.assertEqual(prop.acq_fee_percentage, Decimal('1.00'))
        self.assertEqual(prop.appreciation_rate_percentage, Decimal('3.00'))
        self.assertEqual(prop.vacancy_rate_percentage, Decimal('5.00'))
        self.assertEqual(prop.size, Decimal('100.00'))

    def test_cost_per_sqm_calculation(self):
        prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Size Property",
            city="London",
            country="UK",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="HELD",
            purchase_date="2024-01-01",
            purchase_price=Decimal('1000000.00'),
            size=Decimal('200.00'),
            monthly_rent=Decimal('5000.00'),
            acq_fee_percentage=Decimal('1.00'),
            appreciation_rate_percentage=Decimal('3.00'),
            vacancy_rate_percentage=Decimal('5.00')
        )
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('real-estate-portfolio-properties', kwargs={'pk': self.portfolio.id})
        response = self.client.get(url)
        
        metrics = response.data[0]['metrics']
        # Cost/Sqm = 1,000,000 / 200 = 5,000
        self.assertEqual(Decimal(str(metrics['cost_per_sqm'])), Decimal('5000.00'))

    def test_investor_cannot_add_property(self):
        self.client.force_authenticate(user=self.investor_user)
        url = reverse('real-estate-portfolio-properties', kwargs={'pk': self.portfolio.id})
        data = {"name": "Test"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_property_calculations(self):
        # Use fixed dates for stable math
        purchase_date = datetime.date(2023, 1, 1)
        reference_date = datetime.date(2024, 1, 1) # Exactly 365 days later
        
        prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Calcs Property",
            city="London",
            country="UK",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="HELD",
            purchase_date=purchase_date,
            purchase_price=Decimal('1000000.00'),
            monthly_rent=Decimal('5000.00'),
            acq_fee_percentage=Decimal('2.00'), # override
            appreciation_rate_percentage=Decimal('10.00'), # override
            vacancy_rate_percentage=Decimal('0.00'), # override
            other_operational_expenses=Decimal('5000.00')
        )
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('real-estate-portfolio-properties', kwargs={'pk': self.portfolio.id})
        # Pass reference_date in query params
        response = self.client.get(f"{url}?reference_date=2024-01-01")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        metrics = response.data[0]['metrics']
        
        # Acq Fee: 1M * 2% = 20k
        self.assertEqual(Decimal(str(metrics['acq_fee_amount'])), Decimal('20000.00'))
        
        # Total Cost Basis: 1M + 20k = 1.02M
        self.assertEqual(Decimal(str(metrics['total_cost_basis'])), Decimal('1020000.00'))
        
        # Years Held: 365 / 365.25 = 0.9993... -> rounded to 1.00 in selector logic?
        # Actually in the selector: round(years_held, 2)
        # 365 / 365.25 = 0.99931... rounded to 1.00
        self.assertEqual(float(metrics['years_held']), 1.00)
        
        # Current Market Value: 1M * (1.1 ^ (365/365.25))
        # Growth factor = 1.1 ^ (365/365.25) = 1.09992824...
        # CMV = 1,099,928.24
        self.assertEqual(float(metrics['current_market_value']), 1099928.24)
        
        # Unrealized Gain: 1,099,928.24 - 1,020,000 = 79,928.24
        self.assertAlmostEqual(float(metrics['unrealized_gain']), 79928.24, places=2)
        
        # Effective Rent: (5000 * 12) * (1 - 0) = 60k
        self.assertEqual(Decimal(str(metrics['effective_rent'])), Decimal('60000.00'))
        
        # Mgmt Fees: 2% of 60k = 1.2k
        self.assertAlmostEqual(float(metrics['management_fees']), 1200.00, places=2)
        
        # Maintenance: 1% of 1,099,928.24 = 10,999.2824
        self.assertAlmostEqual(float(metrics['maintenance_fees']), 10999.28, places=2)
        
        # Total Ops: 1.2k + 10,999.28 + 5k = 17,199.28
        self.assertAlmostEqual(float(metrics['total_operational_expenses']), 17199.28, places=2)
        
        # NOI: 60k - 17,199.28 = 42,800.72
        self.assertAlmostEqual(float(metrics['noi']), 42800.72, places=2)

    def test_off_plan_property_calculations(self):
        prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Off Plan Property",
            city="London",
            country="UK",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="OFF_PLAN",
            purchase_date="2024-01-01",
            purchase_price=Decimal('1000000.00'),
            monthly_rent=Decimal('5000.00'),
            acq_fee_percentage=Decimal('1.00'),
            appreciation_rate_percentage=Decimal('3.00'),
            vacancy_rate_percentage=Decimal('5.00')
        )
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('real-estate-portfolio-properties', kwargs={'pk': self.portfolio.id})
        response = self.client.get(url)
        
        metrics = response.data[0]['metrics']
        
        # Effective Rent and NOI should be 0 for OFF_PLAN
        self.assertEqual(Decimal(str(metrics['effective_rent'])), Decimal('0'))
        self.assertEqual(Decimal(str(metrics['noi'])), Decimal('0'))
