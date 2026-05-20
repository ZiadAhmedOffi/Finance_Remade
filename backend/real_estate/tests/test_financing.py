from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from real_estate.models import RealEstatePortfolio, Property, FinancingEntry, RealEstateAssumptions
from real_estate.utils.financing import calculate_pmt
from users.models import Role, UserRoleAssignment

User = get_user_model()

class FinancingModelTests(APITestCase):
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
            name="Test Portfolio",
            created_by=self.admin_user
        )
        RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date="2024-01-01",
            active_scenario="BASE"
        )
        
        self.property_obj = Property.objects.create(
            portfolio=self.portfolio,
            name="Test Property",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="MORTGAGED",
            purchase_date="2024-01-01",
            purchase_price=Decimal("1000000.00"),
            monthly_rent=Decimal("5000.00"),
            acq_fee_percentage=Decimal("1.00"),
            appreciation_rate_percentage=Decimal("3.00"),
            vacancy_rate_percentage=Decimal("5.00")
        )

    def test_calculate_pmt(self):
        # Test with known values
        # Loan: 100,000, Rate: 5% annual, 10 years, monthly
        loan_amount = Decimal("100000")
        annual_rate = Decimal("0.05")
        payments_per_year = 12
        tenor_years = 10
        
        rate_per_period = annual_rate / payments_per_year
        total_periods = tenor_years * payments_per_year
        
        pmt = calculate_pmt(rate_per_period, total_periods, loan_amount)
        # Expected monthly payment for 100k @ 5% for 10yrs is approx 1060.66
        self.assertEqual(float(pmt), 1060.66)

    def test_create_financing_entry_api(self):
        url = reverse('real-estate-portfolio-financing', kwargs={'pk': self.portfolio.id})
        data = {
            "property": str(self.property_obj.id),
            "loan_amount": "800000.00",
            "base_interest_rate": "5.00",
            "tenor": 10,
            "payments_per_year": 12,
            "loan_start_date": "2024-02-01"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FinancingEntry.objects.count(), 1)
        
    def test_loan_amount_validation(self):
        url = reverse('real-estate-portfolio-financing', kwargs={'pk': self.portfolio.id})
        data = {
            "property": str(self.property_obj.id),
            "loan_amount": "1200000.00", # Higher than purchase price (1M)
            "base_interest_rate": "5.00",
            "tenor": 10,
            "payments_per_year": 12,
            "loan_start_date": "2024-02-01"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("must be lower than the purchase price", response.data['error'])

    def test_financing_metrics_api(self):
        FinancingEntry.objects.create(
            property=self.property_obj,
            loan_amount=Decimal("500000.00"),
            base_interest_rate=Decimal("5.00"),
            tenor=10,
            payments_per_year=12,
            loan_start_date="2024-01-01"
        )
        
        url = reverse('real-estate-portfolio-financing', kwargs={'pk': self.portfolio.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['mortgages']), 1)
        metrics = response.data['mortgages'][0]['metrics']
        self.assertEqual(metrics['ltv'], 50.00) # 500k / 1M
        self.assertEqual(metrics['effective_rate'], 5.00) # Base 5% + 0% adjustment

    def test_amortization_schedule_api(self):
        entry = FinancingEntry.objects.create(
            property=self.property_obj,
            loan_amount=Decimal("100000.00"),
            base_interest_rate=Decimal("5.00"),
            tenor=1, # 1 year
            payments_per_year=12,
            loan_start_date="2024-01-01"
        )
        
        url = reverse('real-estate-portfolio-entry-amortization', kwargs={
            'pk': self.portfolio.id,
            'entry_id': entry.id
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 12) # 12 months
        
        # Check last payment zeros out balance
        self.assertEqual(float(response.data[-1]['ending_balance']), 0.00)
