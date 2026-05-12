from decimal import Decimal
from django.db.models import QuerySet
from ..models import FinancingEntry, RealEstatePortfolio
from ..constants import SCENARIO_ADJUSTMENTS
from ..utils.financing import calculate_pmt, generate_amortization_schedule
from collections import defaultdict
from ..calculation import PropertyDataCalc

class FinancingSelectors:
    @staticmethod
    def get_financing_entries_for_portfolio(portfolio: RealEstatePortfolio) -> list:
        """
        Retrieves all financing entries for a portfolio (excluding sold properties)
        with calculated derived metrics.
        """
        entries = FinancingEntry.objects.filter(
            property__portfolio=portfolio
        ).exclude(
            property__status="SOLD"
        ).select_related('property', 'property__portfolio__assumptions')
        
        results = []
        for entry in entries:
            results.append(FinancingSelectors.calculate_entry_metrics(entry))
        
        return results

    @staticmethod
    def calculate_entry_metrics(entry: FinancingEntry) -> dict:
        """
        Calculates derived metrics for a single financing entry.
        """
        assumptions = entry.property.portfolio.assumptions
        active_scenario = assumptions.active_scenario
        
        interest_adjustment = SCENARIO_ADJUSTMENTS.get(active_scenario, {}).get('interest_rate', Decimal('0.00'))
        
        effective_rate_pct = entry.base_interest_rate + interest_adjustment
        effective_rate = effective_rate_pct / Decimal('100')
        
        # LTV = Loan Amount / Purchase Price
        ltv = PropertyDataCalc.ltv(entry.loan_amount, entry.property.purchase_price)
        
        # Periodic Pmt
        rate_per_period = effective_rate / entry.payments_per_year
        total_periods = entry.tenor * entry.payments_per_year
        periodic_payment = calculate_pmt(rate_per_period, total_periods, entry.loan_amount)
        
        # Annual Debt Service
        annual_debt_service = periodic_payment * entry.payments_per_year
        
        # Total Interest
        total_interest = (periodic_payment * total_periods) - entry.loan_amount
        
        return {
            "entry": entry,
            "metrics": {
                "ltv": float(ltv),
                "effective_rate": round(effective_rate_pct, 2),
                "periodic_payment": periodic_payment,
                "annual_debt_service": annual_debt_service,
                "total_interest": total_interest,
            }
        }

    @staticmethod
    def get_amortization_schedule(entry: FinancingEntry):
        """
        Generates the amortization schedule for a single entry.
        """
        assumptions = entry.property.portfolio.assumptions
        interest_adjustment = SCENARIO_ADJUSTMENTS.get(assumptions.active_scenario, {}).get('interest_rate', Decimal('0.00'))
        effective_rate = (entry.base_interest_rate + interest_adjustment) / Decimal('100')
        
        return generate_amortization_schedule(
            loan_amount=entry.loan_amount,
            annual_rate=effective_rate,
            tenor_years=entry.tenor,
            payments_per_year=entry.payments_per_year,
            start_date=entry.loan_start_date
        )

    @staticmethod
    def get_portfolio_total_amortization(portfolio: RealEstatePortfolio):
        """
        Aggregates amortization schedules across all active loans in a portfolio.
        Returns a monthly timeline.
        """
        entries = FinancingEntry.objects.filter(
            property__portfolio=portfolio
        ).exclude(
            property__status="SOLD"
        ).select_related('property', 'property__portfolio__assumptions')
        
        # Aggregate by month and year
        # Key: (year, month), Value: totals
        aggregated = defaultdict(lambda: {
            "periodic_payment": Decimal('0.00'),
            "principal_payment": Decimal('0.00'),
            "interest_payment": Decimal('0.00'),
        })
        
        for entry in entries:
            schedule = FinancingSelectors.get_amortization_schedule(entry)
            
            # For each period in the schedule, calculate the date
            start_date = entry.loan_start_date
            months_per_period = 12 // entry.payments_per_year
            
            for item in schedule:
                # Calculate the date for this period
                period = item['period']
                total_months_offset = months_per_period * (period - 1)
                
                # Rough date calculation
                year_offset = (start_date.month + total_months_offset - 1) // 12
                month = (start_date.month + total_months_offset - 1) % 12 + 1
                year = start_date.year + year_offset
                
                key = (year, month)
                aggregated[key]["periodic_payment"] += item["periodic_payment"]
                aggregated[key]["principal_payment"] += item["principal_payment"]
                aggregated[key]["interest_payment"] += item["interest_payment"]
        
        # Sort by date and format
        sorted_keys = sorted(aggregated.keys())
        result = []
        for key in sorted_keys:
            year, month = key
            totals = aggregated[key]
            result.append({
                "date": f"{year}-{month:02d}",
                "periodic_payment": totals["periodic_payment"],
                "principal_payment": totals["principal_payment"],
                "interest_payment": totals["interest_payment"],
            })
            
        return result
