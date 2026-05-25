from django.test import TestCase
from decimal import Decimal
from datetime import date
from ..models import RealEstatePortfolio, RealEstateAssumptions, Jurisdiction, TaxRule, Property
from ..selectors.taxation_selectors import TaxationAnalysisSelector

class TaxationAnalysisSelectorTests(TestCase):
    def setUp(self):
        self.portfolio = RealEstatePortfolio.objects.create(name="Tax Analysis Portfolio")
        self.assumptions = RealEstateAssumptions.objects.create(
            portfolio=self.portfolio,
            inception_date=date(2024, 1, 1),
            forecast_horizon=5,
            acquisition_fee_percentage=Decimal('2.00'),
            default_appreciation_rate=Decimal('5.00'),
            default_rental_growth_rate=Decimal('3.00'),
            default_vacancy_rate=Decimal('5.00')
        )
        self.jurisdiction = Jurisdiction.objects.create(name="Test Jur", currency="USD")
        self.portfolio.jurisdiction = self.jurisdiction
        self.portfolio.save()

        # Rules
        self.rule1 = TaxRule.objects.create(
            jurisdiction=self.jurisdiction,
            name="Property Tax",
            event_type="OWNERSHIP",
            trigger="ANNUAL",
            tax_base="MARKET_VALUE",
            rate=Decimal('0.01'),
            is_active=True
        )
        self.rule2 = TaxRule.objects.create(
            jurisdiction=self.jurisdiction,
            name="Income Tax",
            event_type="INCOME",
            trigger="ANNUAL",
            tax_base="NET_INCOME",
            rate=Decimal('0.05'),
            is_active=True
        )

        # Property
        self.property = Property.objects.create(
            portfolio=self.portfolio,
            name="Test Villa",
            city="Dubai",
            country="UAE",
            property_type="RESIDENTIAL",
            financing_type="ALL_CASH",
            status="HELD",
            purchase_date=date(2024, 1, 1),
            purchase_price=Decimal('1000000.00'),
            monthly_rent=Decimal('5000.00'),
            size=Decimal('200.00'),
            acq_fee_percentage=Decimal('2.00'),
            appreciation_rate_percentage=Decimal('5.00'),
            vacancy_rate_percentage=Decimal('5.00')
        )

    def test_analysis_aggregation(self):
        analysis = TaxationAnalysisSelector.get_taxation_analysis(self.portfolio)
        
        self.assertIn('annual_totals', analysis)
        self.assertIn('detailed_breakdown', analysis)
        self.assertIn('summary_metrics', analysis)
        
        # 5 years of forecast
        self.assertEqual(len(analysis['annual_totals']), 5)
        
        # Check first year totals
        # Market value Y1 (2024) = 1,000,000
        # Property Tax (1%) = 10,000
        # NOI (approx) = 5000 * 12 * (1-0.05) = 57,000
        # Income Tax (5%) = 57,000 * 0.05 = 2,850
        # Total Y1 tax approx 12,850
        
        y1_data = analysis['annual_totals'][0]
        self.assertEqual(y1_data['year'], 2024)
        self.assertGreater(y1_data['total'], 11000)
        
        # Check breakdown
        breakdown_2024 = analysis['detailed_breakdown']["2024"] if "2024" in analysis['detailed_breakdown'] else analysis['detailed_breakdown'][2024]
        self.assertIn('Property Tax', breakdown_2024)
        self.assertIn('Income Tax', breakdown_2024)
        
        self.assertEqual(breakdown_2024['Property Tax']['total'], 10000.0)
        
        # Summary metrics
        self.assertEqual(analysis['summary_metrics']['forecast_years'], 5)
        self.assertGreater(analysis['summary_metrics']['total_cumulative'], 60000)
