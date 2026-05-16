from decimal import Decimal
from ..models import InstallmentEntry, RealEstatePortfolio
from collections import defaultdict

class InstallmentSelectors:
    @staticmethod
    def get_installment_entries_for_portfolio(portfolio: RealEstatePortfolio) -> list:
        """
        Retrieves all installment entries for a portfolio (excluding sold properties)
        with calculated derived metrics.
        """
        entries = InstallmentEntry.objects.filter(
            property__portfolio=portfolio
        ).exclude(
            property__status="SOLD"
        ).select_related('property')
        
        results = []
        for entry in entries:
            results.append(InstallmentSelectors.calculate_entry_metrics(entry))
        
        return results

    @staticmethod
    def calculate_entry_metrics(entry: InstallmentEntry) -> dict:
        """
        Calculates derived metrics for a single installment entry.
        """
        # Balance = Purchase Price - Down Payment
        balance = entry.property.purchase_price - entry.down_payment
        
        # Periodic Pmt (Equal installments)
        total_periods = entry.tenor * entry.payments_per_year
        periodic_payment = (balance / total_periods) if total_periods > 0 else Decimal('0.00')
        
        # Annual Installment Payment
        annual_payment = periodic_payment * entry.payments_per_year
        
        return {
            "entry": entry,
            "metrics": {
                "balance": float(balance),
                "periodic_payment": periodic_payment,
                "annual_payment": annual_payment,
                "total_periods": total_periods,
            }
        }

    @staticmethod
    def get_installment_schedule(entry: InstallmentEntry) -> list:
        """
        Generates the payment schedule for a single installment entry.
        """
        metrics = InstallmentSelectors.calculate_entry_metrics(entry)
        periodic_payment = metrics['metrics']['periodic_payment']
        total_periods = metrics['metrics']['total_periods']
        
        schedule = []
        start_date = entry.start_date
        months_per_period = 12 // entry.payments_per_year if entry.payments_per_year > 0 else 12
        
        for i in range(1, total_periods + 1):
            # Calculate roughly the date
            total_months_offset = months_per_period * (i - 1)
            year_offset = (start_date.month + total_months_offset - 1) // 12
            month = (start_date.month + total_months_offset - 1) % 12 + 1
            year = start_date.year + year_offset
            
            schedule.append({
                "period": i,
                "date": f"{year}-{month:02d}",
                "payment": periodic_payment,
            })
            
        return schedule

    @staticmethod
    def get_portfolio_total_installments(portfolio: RealEstatePortfolio) -> list:
        """
        Aggregates installment schedules across all active properties in a portfolio.
        """
        entries = InstallmentEntry.objects.filter(
            property__portfolio=portfolio
        ).exclude(
            property__status="SOLD"
        )
        
        aggregated = defaultdict(Decimal)
        
        for entry in entries:
            schedule = InstallmentSelectors.get_installment_schedule(entry)
            for item in schedule:
                aggregated[item['date']] += item['payment']
        
        # Sort by date
        sorted_dates = sorted(aggregated.keys())
        result = []
        for d in sorted_dates:
            result.append({
                "date": d,
                "payment": aggregated[d]
            })
            
        return result
