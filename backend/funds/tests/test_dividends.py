from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from funds.models import Fund, InvestorAction, CurrentInvestorStats, Distribution, ModelInput
from users.models import User, Role, UserRoleAssignment
from decimal import Decimal
from datetime import date
import json

class TestDividends(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(email="admin@example.com", password="password")
        self.superuser.is_active = True
        self.superuser.save()
        
        self.admin_role, _ = Role.objects.get_or_create(name="SUPER_ADMIN", is_system_role=True)
        UserRoleAssignment.objects.create(user=self.superuser, role=self.admin_role)
        
        self.investor_role, _ = Role.objects.get_or_create(name="INVESTOR")
        
        self.fund = Fund.objects.create(name="Yield Fund", status="ESTABLISHED", default_dividend_treatment="CASH")
        ModelInput.objects.filter(fund=self.fund).update(inception_year=2024, fund_life=10)
        
        # Create Investors
        self.investors = []
        for i in range(2):
            u = User.objects.create(email=f"investor{i}@example.com", first_name=f"I{i}", last_name="Test")
            u.is_active = True
            u.save()
            UserRoleAssignment.objects.create(user=u, role=self.investor_role, fund=self.fund)
            
            # Primary Investment
            InvestorAction.objects.create(
                investor=u,
                fund=self.fund,
                type="PRIMARY_INVESTMENT",
                year=2024,
                amount=Decimal("100000.00"),
                units=Decimal("100.0000")
            )
            self.investors.append(u)
        
        self.client = APIClient()

    def test_cash_dividend_allocation(self):
        self.client.force_authenticate(user=self.superuser)
        # 1. Create Distribution
        dist_data = {
            "amount": "10000.00",
            "date": "2024-06-15",
            "type": "DIVIDEND",
            "fund": str(self.fund.id)
        }
        url = reverse("distribution-list", kwargs={"fund_id": self.fund.id})
        response = self.client.post(url, data=dist_data) # APIClient handles dict as JSON by default if configured, but let's be safe
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        dist_id = response.data["id"]
        
        # 2. Allocate Distribution
        alloc_url = reverse("distribution-allocate", kwargs={"distribution_id": dist_id})
        response = self.client.post(alloc_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["investor_count"], 2)
        
        # 3. Verify InvestorActions
        for inv in self.investors:
            actions = InvestorAction.objects.filter(investor=inv, type="DIVIDEND_PAYOUT")
            self.assertEqual(actions.count(), 1)
            # Pro-rata: 100/200 * 10000 = 5000
            self.assertEqual(actions[0].amount, Decimal("5000.00"))
            
            # Verify Stats
            stats = CurrentInvestorStats.objects.get(investor=inv, fund=self.fund)
            self.assertEqual(stats.realized_gain, Decimal("5000.00"))
            self.assertEqual(stats.units, Decimal("100.0000"))

    def test_reinvestment_dividend_allocation(self):
        self.client.force_authenticate(user=self.superuser)
        self.fund.default_dividend_treatment = "REINVEST"
        self.fund.save()
        
        # Distribution
        dist = Distribution.objects.create(
            fund=self.fund,
            amount=Decimal("20000.00"),
            date=date(2024, 6, 15),
            type="DIVIDEND"
        )
        
        # Allocate
        alloc_url = reverse("distribution-allocate", kwargs={"distribution_id": dist.id})
        response = self.client.post(alloc_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify InvestorActions
        for inv in self.investors:
            actions = InvestorAction.objects.filter(investor=inv, type="DIVIDEND_REINVESTMENT")
            self.assertEqual(actions.count(), 1)
            # Share = 10000
            self.assertEqual(actions[0].amount, Decimal("10000.00"))
            self.assertTrue(actions[0].units > 0)
            
            stats = CurrentInvestorStats.objects.get(investor=inv, fund=self.fund)
            self.assertTrue(stats.units > Decimal("100.0000"))
            self.assertTrue(stats.amount_invested > Decimal("100000.00"))
            # Realized Gain should be exactly the share (10000)
            self.assertEqual(stats.realized_gain, Decimal("10000.00"))

    def test_investor_yield_history(self):
        inv = self.investors[0]
        
        # Create Payout Action
        InvestorAction.objects.create(
            investor=inv,
            fund=self.fund,
            type="DIVIDEND_PAYOUT",
            year=2024,
            amount=Decimal("5000.00")
        )
        
        self.client.force_authenticate(user=inv)
        url = reverse("investor-dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        yield_history = response.data["yield_history"]
        year_2024 = next(y for y in yield_history if y["year"] == 2024)
        self.assertEqual(year_2024[self.fund.name], 5000.0)
