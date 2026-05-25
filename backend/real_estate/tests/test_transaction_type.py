from django.test import TestCase
from decimal import Decimal
from datetime import date
from ..models import RealEstatePortfolio, RealEstateAssumptions, Property
from ..services.property_service import PropertyService

class TransactionTypeLogicTest(TestCase):
    def setUp(self):
        self.portfolio = RealEstatePortfolio.objects.create(name="Test Portfolio")
        self.assumptions = RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date=date(2023, 1, 1),
            acquisition_fee_percentage=Decimal('1.00'),
            default_appreciation_rate=Decimal('5.00'),
            default_vacancy_rate=Decimal('2.00')
        )

    def test_off_plan_forces_primary_and_zero_fees(self):
        """Verify that OFF_PLAN status forces transaction_type=PRIMARY and acq_fee=0."""
        data = {
            "name": "Off-Plan Property",
            "city": "Dubai",
            "country": "UAE",
            "property_type": "RESIDENTIAL",
            "financing_type": "ALL_CASH",
            "status": "OFF_PLAN",
            "purchase_date": "2024-01-01",
            "purchase_price": "1000000.00",
            "size": "100",
            "transaction_type": "SECONDARY", # Attempt to set as secondary
            "acq_fee_percentage": "2.00"      # Attempt to set fee
        }
        prop = PropertyService.create_property(self.portfolio, data)
        
        self.assertEqual(prop.transaction_type, "PRIMARY")
        self.assertEqual(prop.acq_fee_percentage, Decimal('0.00'))

    def test_primary_forces_zero_fees(self):
        """Verify that PRIMARY transaction type forces acq_fee=0 regardless of status."""
        data = {
            "name": "Held Primary Property",
            "city": "Dubai",
            "country": "UAE",
            "property_type": "RESIDENTIAL",
            "financing_type": "ALL_CASH",
            "status": "HELD",
            "purchase_date": "2024-01-01",
            "purchase_price": "1000000.00",
            "size": "100",
            "transaction_type": "PRIMARY",
            "acq_fee_percentage": "2.00"      # Attempt to set fee
        }
        prop = PropertyService.create_property(self.portfolio, data)
        
        self.assertEqual(prop.transaction_type, "PRIMARY")
        self.assertEqual(prop.acq_fee_percentage, Decimal('0.00'))

    def test_secondary_allows_fees(self):
        """Verify that SECONDARY transaction type allows acq_fee from input or assumptions."""
        data = {
            "name": "Secondary Property",
            "city": "Dubai",
            "country": "UAE",
            "property_type": "RESIDENTIAL",
            "financing_type": "ALL_CASH",
            "status": "HELD",
            "purchase_date": "2024-01-01",
            "purchase_price": "1000000.00",
            "size": "100",
            "transaction_type": "SECONDARY",
            "acq_fee_percentage": "2.50"
        }
        prop = PropertyService.create_property(self.portfolio, data)
        
        self.assertEqual(prop.transaction_type, "SECONDARY")
        self.assertEqual(prop.acq_fee_percentage, Decimal('2.50'))

    def test_update_enforcement(self):
        """Verify enforcement logic works during updates."""
        data = {
            "name": "Initial Property",
            "city": "Dubai",
            "country": "UAE",
            "property_type": "RESIDENTIAL",
            "financing_type": "ALL_CASH",
            "status": "HELD",
            "purchase_date": "2024-01-01",
            "purchase_price": "1000000.00",
            "size": "100",
            "transaction_type": "SECONDARY",
            "acq_fee_percentage": "1.00"
        }
        prop = PropertyService.create_property(self.portfolio, data)
        
        # Update to OFF_PLAN
        PropertyService.update_property(prop, {"status": "OFF_PLAN", "acq_fee_percentage": "2.00"})
        self.assertEqual(prop.transaction_type, "PRIMARY")
        self.assertEqual(prop.acq_fee_percentage, Decimal('0.00'))
        
        # Reset to HELD/SECONDARY
        PropertyService.update_property(prop, {"status": "HELD", "transaction_type": "SECONDARY", "acq_fee_percentage": "1.50"})
        self.assertEqual(prop.transaction_type, "SECONDARY")
        self.assertEqual(Decimal(str(prop.acq_fee_percentage)), Decimal('1.50'))
        
        # Update to PRIMARY manually
        PropertyService.update_property(prop, {"transaction_type": "PRIMARY"})
        self.assertEqual(prop.acq_fee_percentage, Decimal('0.00'))
