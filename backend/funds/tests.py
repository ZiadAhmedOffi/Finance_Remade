from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Fund, ModelInput

User = get_user_model()

class FundModelTest(TestCase):
    def test_model_input_creation_on_fund_create(self):
        """Test that ModelInput is created when a Fund is created via signals."""
        user = User.objects.create_user(email="test@example.com", password="password")
        fund = Fund.objects.create(name="Test Fund", created_by=user)
        
        self.assertTrue(ModelInput.objects.filter(fund=fund).exists())
        model_input = ModelInput.objects.get(fund=fund)
        self.assertEqual(model_input.target_fund_size, 100000000.00)
