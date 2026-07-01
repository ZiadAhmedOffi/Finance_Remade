from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from compliance.models import ComplianceState
from compliance.services.profile_service import ComplianceProfileService
from ..models import RealEstatePortfolio, RealEstateAssumptions, Property, RealEstateInvestorAction, RealEstateInvestorStats
from users.models import Role, UserRoleAssignment
from decimal import Decimal
import datetime

User = get_user_model()

class InvestorLogAPITests(TestCase):
    def _approve_investor(self, user):
        profile = ComplianceProfileService.ensure_individual_profile_for_user(user, create_case=True)
        profile.current_state = ComplianceState.APPROVED
        profile.operability_blocked = False
        profile.save(update_fields=["current_state", "operability_blocked", "updated_at"])
        case = profile.cases.order_by("-opened_at").first()
        case.state = ComplianceState.APPROVED
        case.save(update_fields=["state"])

    def test_investor_log_with_usufruct(self):
        """Verify that usufruct properties don't crash the investor log due to null purchase_price."""
        from ..models import UsufructDetails
        
        # Add Usufruct property
        u_prop = Property.objects.create(
            portfolio=self.portfolio,
            name="Usufruct Prop",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="USUFRUCT",
            purchase_date="2024-01-01",
            purchase_price=None,
            monthly_rent=None,
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00'),
        )
        UsufructDetails.objects.create(
            property=u_prop,
            prep_cost=Decimal('50000.00')
        )
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('real-estate-portfolio-investor-log', kwargs={'pk': self.portfolio.id})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify Usufruct prep cost is in capital required
        graph_data = response.data.get('graph_data', [])
        y2024 = next((item for item in graph_data if item['year'] == 2024), None)
        self.assertIsNotNone(y2024)
        # Should include the 50k prep cost in total_capital_required
        self.assertGreaterEqual(y2024['total_capital_required'], 50000.0)
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            email="admin@example.com", 
            password="password123",
            is_active=True
        )
        self.admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", is_system_role=True)
        UserRoleAssignment.objects.create(user=self.admin_user, role=self.admin_role)
        
        self.investor_user = User.objects.create_user(
            email="investor@example.com", 
            password="password123",
            is_active=True
        )
        self.investor_role, _ = Role.objects.get_or_create(name="INVESTOR", is_system_role=True)

        self.portfolio = RealEstatePortfolio.objects.create(name="RE Portfolio", created_by=self.admin_user)
        self.assumptions = RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date="2024-01-01",
            acquisition_fee_percentage=Decimal('0.00'),
            default_appreciation_rate=Decimal('0.00'),
            default_vacancy_rate=Decimal('0.00'),
            maintenance_percentage_of_value=Decimal('0.00'),
        )
        
        UserRoleAssignment.objects.create(user=self.investor_user, role=self.investor_role, real_estate_portfolio=self.portfolio)
        self._approve_investor(self.investor_user)
        self._approve_investor(self.admin_user)

    def test_primary_investment_units_and_stats(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('real-estate-portfolio-investor-actions', kwargs={'pk': self.portfolio.id})
        
        # 1. First investment: 100k
        data = {
            "investor": str(self.investor_user.id),
            "type": "PRIMARY_INVESTMENT",
            "year": 2024,
            "amount": "100000.00"
        }
        response = self.client.post(url, data)
        if response.status_code != status.HTTP_201_CREATED:
            print(f"DEBUG Error: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.portfolio.refresh_from_db()
        self.assertEqual(float(self.portfolio.total_units), 100000.0)
        
        stats = RealEstateInvestorStats.objects.get(investor=self.investor_user, portfolio=self.portfolio)
        self.assertEqual(float(stats.units), 100000.0)
        self.assertEqual(float(stats.amount_invested), 100000.0)

        # 2. Add a property to change NAV
        # NAV = Cash (100k) + Property (0) = 100k
        # Buy property for 50k
        # Setting purchase date to today to keep CMV = PP
        today = datetime.date.today()
        Property.objects.create(
            portfolio=self.portfolio,
            name="Prop 1",
            city="C", country="CO",
            property_type="RESIDENTIAL", financing_type="ALL_CASH",
            purchase_date=today,
            purchase_price=Decimal('50000.00'),
            monthly_rent=Decimal('0.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('100.00'),
            vacancy_rate_percentage=Decimal('0.00')
        )
        
        # 3. Wait 1 year (via reference_date in metrics)
        # NAV at end of 2024 (roughly):
        # Cash = 100k - 50k = 50k
        # Property Value (after 0.5 year held at 100% app rate)
        # years_held = 0.5 roughly
        # MV = 50k * (1 + 1.0)^0.5 = 50k * 1.414 = 70.7k
        # Total NAV = 50k + 70.7k = 120.7k
        # Price per unit = 120.7k / 100k = 1.207
        
        # 4. Second investment: 60350 (should give roughly 50k units)
        # But we need to make sure the service uses the correct current NAV.
        # The service currently uses timezone.now() for NAV metrics in create_investor_action.
        
        data2 = {
            "investor": str(self.investor_user.id),
            "type": "PRIMARY_INVESTMENT",
            "year": 2025,
            "amount": "120700.00" 
        }
        # We'll mock the NAV or just accept whatever it is.
        # Given we are at "now", and property was bought "now", CMV = PP.
        # NAV = 50k cash + 50k property = 100k.
        # Units = 120700 / (100k / 100k) = 120700 units.
        
        response = self.client.post(url, data2)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.portfolio.refresh_from_db()
        self.assertEqual(float(self.portfolio.total_units), 220700.0)

    def test_secondary_exit_logic(self):
        # 1. Setup initial investment
        RealEstateInvestorAction.objects.create(
            portfolio=self.portfolio,
            investor=self.investor_user,
            type="PRIMARY_INVESTMENT",
            year=2024,
            amount=Decimal('100000.00'),
            units=Decimal('100000.00')
        )
        self.portfolio.total_units = Decimal('100000.00')
        self.portfolio.save()
        
        # 2. Sell 50%
        # Seller: investor_user
        # Buyer: admin_user (why not)
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('real-estate-portfolio-investor-actions', kwargs={'pk': self.portfolio.id})
        
        data = {
            "investor": str(self.investor_user.id),
            "investor_selling": str(self.investor_user.id),
            "investor_sold_to": str(self.admin_user.id),
            "type": "SECONDARY_EXIT",
            "year": 2024,
            "percentage_sold": "50.00",
            "amount": "60000.00", # Sold for 60k (gain of 10k since basis is 50k)
            "discount_percentage": "0.00"
        }
        
        response = self.client.post(url, data)
        if response.status_code != status.HTTP_201_CREATED:
            print(f"DEBUG Error: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 3. Verify Stats
        seller_stats = RealEstateInvestorStats.objects.get(investor=self.investor_user, portfolio=self.portfolio)
        self.assertEqual(float(seller_stats.units), 50000.0)
        self.assertEqual(float(seller_stats.amount_invested), 50000.0) # 100k - 50k basis
        self.assertEqual(float(seller_stats.realized_gain), 10000.0) # 60k - 50k basis
        
        buyer_stats = RealEstateInvestorStats.objects.get(investor=self.admin_user, portfolio=self.portfolio)
        self.assertEqual(float(buyer_stats.units), 50000.0)
        self.assertEqual(float(buyer_stats.amount_invested), 60000.0)

    def test_investor_log_view(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('real-estate-portfolio-investor-log', kwargs={'pk': self.portfolio.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("graph_data", response.data)
        self.assertIn("nav_metrics", response.data)
        self.assertIn("investors", response.data)

    def test_capital_required_logic(self):
        # 1. ALL_CASH Property
        Property.objects.create(
            portfolio=self.portfolio,
            name="Cash Prop",
            city="C", country="CO",
            property_type="RESIDENTIAL", financing_type="ALL_CASH",
            purchase_date="2024-01-01",
            purchase_price=Decimal('100000.00'),
            monthly_rent=Decimal('0.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00')
        )
        
        # 2. OFF_PLAN Property with Milestones
        off_plan = Property.objects.create(
            portfolio=self.portfolio,
            name="Off-Plan Prop",
            city="C", country="CO",
            property_type="RESIDENTIAL", financing_type="ALL_CASH",
            status="OFF_PLAN",
            purchase_date="2024-01-01",
            purchase_price=Decimal('200000.00'),
            monthly_rent=Decimal('0.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00')
        )
        from ..models import OffPlanDetails, OffPlanMilestone
        OffPlanDetails.objects.create(
            property=off_plan,
            construction_start_date="2024-01-01",
            expected_completion_date="2026-01-01",
            appreciation_rate_at_completion=Decimal('0.00')
        )
        OffPlanMilestone.objects.create(property=off_plan, milestone_name="Initial", date="2024-06-01", percentage_of_price=Decimal('20.00'))
        OffPlanMilestone.objects.create(property=off_plan, milestone_name="Mid", date="2025-01-01", percentage_of_price=Decimal('30.00'))
        OffPlanMilestone.objects.create(property=off_plan, milestone_name="Final", date="2026-01-01", percentage_of_price=Decimal('50.00'))
        
        # 3. MORTGAGED Property
        mortgaged = Property.objects.create(
            portfolio=self.portfolio,
            name="Mortgaged Prop",
            city="C", country="CO",
            property_type="RESIDENTIAL", financing_type="MORTGAGED",
            purchase_date="2024-01-01",
            purchase_price=Decimal('300000.00'),
            monthly_rent=Decimal('0.00'),
            acq_fee_percentage=Decimal('0.00'),
            appreciation_rate_percentage=Decimal('0.00'),
            vacancy_rate_percentage=Decimal('0.00')
        )
        from ..models import FinancingEntry
        FinancingEntry.objects.create(
            property=mortgaged,
            loan_amount=Decimal('200000.00'),
            base_interest_rate=Decimal('5.00'),
            tenor=5,
            payments_per_year=1, # Simplify to annual for test
            loan_start_date="2024-01-01"
        )
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('real-estate-portfolio-investor-log', kwargs={'pk': self.portfolio.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        graph_data = response.data["graph_data"]
        data_2024 = next(item for item in graph_data if item["year"] == 2024)
        
        # Cash: 100k
        # Off-plan: 40k
        # Mortgaged DP: 100k
        # Mortgaged PMT 2024: 46217.47 (approx)
        # Total 2024 = 286217.47
        
        self.assertGreater(data_2024["total_capital_required"], 286000)
        self.assertLess(data_2024["total_capital_required"], 287000)
