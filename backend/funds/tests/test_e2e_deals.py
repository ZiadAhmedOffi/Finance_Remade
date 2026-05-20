from django.test import TestCase
from django.contrib.auth import get_user_model
from funds.models import Fund, InvestmentDeal, CurrentDeal, InvestmentRound
from rest_framework.test import APIClient
from decimal import Decimal
import uuid

User = get_user_model()

class DealE2ETest(TestCase):
    """
    End-to-End tests for creating and updating deals to ensure no AttributeErrors
    occur during serialization.
    """
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="e2e_test@example.com", password="password", is_active=True)
        from users.models import Role, UserRoleAssignment
        self.admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", defaults={"is_system_role": True})
        UserRoleAssignment.objects.get_or_create(user=self.user, role=self.admin_role)
        self.client.force_authenticate(user=self.user)
        self.fund = Fund.objects.create(name="E2E Fund", created_by=self.user)

    def test_investment_deal_lifecycle(self):
        # 1. Create Investment Deal
        data = {
            "company_name": "Future Tech",
            "company_type": "SaaS",
            "industry": "Technology",
            "investment_type": "EQUITY",
            "entry_year": 2026,
            "exit_year": 2031,
            "amount_invested": "2000000",
            "entry_valuation": "8000000",
            "base_factor": "3.0",
            "downside_factor": "1.0",
            "upside_factor": "5.0",
            "selected_scenario": "BASE",
            "expected_number_of_rounds": 2,
            "pro_rata_rights": True
        }
        response = self.client.post(f'/api/funds/{self.fund.id}/deals/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["company_name"], "Future Tech")
        self.assertEqual(response.data["post_money_ownership"], 20.0)
        deal_id = response.data["id"]

        # 2. Update Investment Deal
        update_data = {"amount_invested": "3000000"}
        response = self.client.put(f'/api/funds/{self.fund.id}/deals/{deal_id}/', update_data, format='json')
        self.assertEqual(response.status_code, 200)
        # 3M / (3M + 8M) = 3/11 approx 27.27
        self.assertAlmostEqual(response.data["post_money_ownership"], 27.2727, places=3)

    def test_current_deal_lifecycle(self):
        # 1. Create Current Deal
        data = {
            "company_name": "Current SaaS",
            "company_type": "SaaS",
            "industry": "Tech",
            "entry_year": 2024,
            "latest_valuation_year": 2024,
            "amount_invested": "1000000",
            "entry_valuation": "4000000",
            "latest_valuation": "6000000",
            "expected_exit_multiple": "4.0"
        }
        response = self.client.post(f'/api/funds/{self.fund.id}/current-deals/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["company_name"], "Current SaaS")
        self.assertEqual(response.data["post_money_ownership"], 20.0)
        self.assertEqual(response.data["moic"], 1.2) # 6M / (1M + 4M) = 6/5 = 1.2
        deal_id = response.data["id"]

        # 2. Update Current Deal
        update_data = {"latest_valuation": "10000000"}
        response = self.client.put(f'/api/funds/{self.fund.id}/current-deals/{deal_id}/', update_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["moic"], 2.0) # 10M / 5M = 2.0

    def test_investment_round_lifecycle(self):
        # 1. Setup a current deal first
        deal = CurrentDeal.objects.create(
            fund=self.fund,
            company_name="Round Co",
            entry_year=2023,
            amount_invested=Decimal("1000000"),
            entry_valuation=Decimal("4000000"),
            latest_valuation=Decimal("5000000")
        )

        # 2. Create Investment Round
        data = {
            "company_name": "Round Co",
            "year": 2024,
            "pre_money_valuation": "10000000",
            "new_money_raised": "2000000",
            "target_valuation": "12000000",
            "exercise_pro_rata": False,
            "new_ownership_percentage": "15.0"
        }
        response = self.client.post(f'/api/funds/{self.fund.id}/investment-rounds/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["company_name"], "Round Co")
        round_id = response.data["id"]

        # 3. Update Investment Round
        update_data = {"new_money_raised": "3000000", "target_valuation": "13000000"}
        response = self.client.put(f'/api/funds/{self.fund.id}/investment-rounds/{round_id}/', update_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["new_money_raised"], "3000000.00")
