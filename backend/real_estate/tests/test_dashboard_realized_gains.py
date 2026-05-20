from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from real_estate.models import RealEstatePortfolio, RealEstateAssumptions, Property, InstallmentEntry
from users.models import Role, UserRoleAssignment
from decimal import Decimal
import datetime

User = get_user_model()

class RealizedGainsDashboardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            email="admin@example.com", 
            password="password123",
            is_active=True
        )
        self.admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", is_system_role=True)
        UserRoleAssignment.objects.create(user=self.admin_user, role=self.admin_role)
        
        self.portfolio = RealEstatePortfolio.objects.create(name="Test Portfolio", created_by=self.admin_user)
        self.assumptions = RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date="2024-01-01",
            acquisition_fee_percentage=Decimal('0.00'),
            default_appreciation_rate=Decimal('0.00'),
            default_vacancy_rate=Decimal('0.00'),
            property_mgmt_fee_percentage=Decimal('0.00'),
            maintenance_percentage_of_value=Decimal('0.00'),
            default_rental_growth_rate=Decimal('0.00'),
            forecast_horizon=5
        )
        
        # Prop 1: HELD, earns 120k/year.
        self.prop1 = Property.objects.create(
            portfolio=self.portfolio,
            name="Positive CF Property",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="HELD",
            purchase_date="2024-01-01",
            purchase_price=Decimal('1000000.00'),
            monthly_rent=Decimal('10000.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00')
        )

    def test_realized_gains_calculation(self):
        """
        Verify that realized gains include operational cash flow for both portfolio and properties.
        """
        # Prop 2: HELD, with installments that make annual CF negative
        prop2 = Property.objects.create(
            portfolio=self.portfolio,
            name="Installment Property",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="PRIMARY_INSTALLMENTS",
            status="HELD",
            purchase_date="2024-01-01",
            purchase_price=Decimal('1000000.00'),
            monthly_rent=Decimal('8333.33'), # ~100k per year
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00')
        )
        InstallmentEntry.objects.create(
            property=prop2,
            down_payment=Decimal('200000.00'),
            tenor=5,
            payments_per_year=12,
            start_date="2024-01-01"
        )

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('real-estate-portfolio-dashboard', kwargs={'pk': self.portfolio.id})
        
        # 2025: 
        # Prop 1: CF = 120k (Positive). NOI-DS = 120k.
        # Prop 2: CF = 100k - 160k = -60k (Negative). NOI-DS = 100k.
        # Portfolio CF: 120k - 60k = 60k (Positive).
        
        response = self.client.get(f"{url}?reference_date=2025-12-31")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        metrics = response.data['metrics']
        # Portfolio realized gains = 60k (Portfolio CF)
        self.assertAlmostEqual(float(metrics['realized_gains']), 60000.0, places=1)
        
        # Property Table
        prop1_row = next(r for r in response.data['value_gain_table'] if r['name'] == "Positive CF Property")
        prop2_row = next(r for r in response.data['value_gain_table'] if r['name'] == "Installment Property")
        
        # Prop 1 Realized Gain = 120k (NOI-DS from its positive year)
        self.assertAlmostEqual(float(prop1_row['realized_gain']), 120000.0, places=1)
        # Prop 2 Realized Gain = 0 (No positive CF years)
        self.assertAlmostEqual(float(prop2_row['realized_gain']), 0.0, places=1)
