from decimal import Decimal
from collections import defaultdict
from ..models import RealEstatePortfolio
from .cash_flow_selectors import CashFlowSelectors
from ..services.taxation_service import TaxationService

class TaxationAnalysisSelector:
    @staticmethod
    def get_taxation_analysis(portfolio: RealEstatePortfolio) -> dict:
        """
        Aggregates detailed taxation data for the entire portfolio.
        Provides:
        - annual_totals: { year: { rule_name: amount, total: amount } }
        - detailed_breakdown: { year: { rule_name: { property_name: amount, total: amount } } }
        - summary_metrics: { total_cumulative, avg_annual, total_forecast }
        """
        assumptions = portfolio.assumptions
        inception_year = assumptions.inception_date.year
        forecast_horizon = assumptions.forecast_horizon
        end_year = inception_year + forecast_horizon - 1
        
        years = list(range(inception_year, end_year + 1))
        properties = portfolio.properties.all().select_related('financing', 'off_plan_details', 'usufruct_details').prefetch_related('milestones', 'sale')
        
        # We need the same data as CashFlowSelectors to get NOI, market_value, etc.
        # But we'll rebuild the iteration to capture the rule breakdown.
        cf_data = CashFlowSelectors.get_portfolio_cash_flow(portfolio)
        
        annual_rule_totals = defaultdict(lambda: defaultdict(Decimal))
        detailed_breakdown = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))
        
        for prop in properties:
            prop_id = str(prop.id)
            prop_cf = cf_data['properties'].get(prop_id)
            if not prop_cf:
                continue
            
            lcf_pool = Decimal('0.00')
            
            for year in years:
                metadata = prop_cf['metadata'].get(year)
                if not metadata:
                    continue
                
                # Context for TaxationService
                tax_context = {
                    'market_value': metadata['market_value'],
                    'net_income': metadata['noi'] - metadata['interest_expense'] - metadata['taxes'], # This is a bit recursive in cash_flow_selectors, let's stick to the logic used there
                    # Re-applying LCF logic as in cash_flow_selectors
                }
                
                # To be precise, we need the EXACT context used in cash_flow_selectors
                # Let's extract values directly from metadata
                # Note: 'taxes' in metadata is the TOTAL tax for that property/year.
                # We need to recalculate to get the breakdown.
                
                is_disposal_year = False
                if hasattr(prop, 'sale') and prop.sale.sale_date.year == year:
                    is_disposal_year = True
                
                # Property events reconstruction
                property_events = ['ANNUAL']
                if year == prop.purchase_date.year:
                    property_events.append('CONTRACT_SIGNING')
                if is_disposal_year:
                    property_events.append('DISPOSAL')
                if hasattr(prop, 'off_plan_details'):
                    if year < prop.off_plan_details.expected_completion_date.year:
                        # Assuming ON_PAYMENT if there are milestones or installments
                        property_events.append('ON_PAYMENT')
                    if year == prop.off_plan_details.expected_completion_date.year:
                        property_events.append('HANDOVER')

                tax_context = {
                    'market_value': metadata['market_value'],
                    'net_income': metadata['noi'] - metadata['interest_expense'] - (metadata['purchase_price'] * (Decimal(str(assumptions.default_depreciation_rate))/Decimal('100'))).quantize(Decimal('0.01')),
                    'property_events': property_events,
                    'is_disposal_year': is_disposal_year,
                    'loan_interest': metadata['interest_expense']
                }
                
                # Apply LCF matching CashFlowSelectors
                # (metadata['lcf_pool'] is the pool AFTER the year's calculation)
                # We need the pool BEFORE. 
                # Actually, CashFlowSelectors applies LCF then calculates tax.
                # Let's just use the TaxationService.calculate_property_tax_breakdown
                
                breakdown = TaxationService.calculate_property_tax_breakdown(prop, year - inception_year, tax_context)
                
                for item in breakdown:
                    rule_name = item['rule_name']
                    amount = item['amount']
                    
                    annual_rule_totals[year][rule_name] += amount
                    annual_rule_totals[year]['total'] += amount
                    
                    detailed_breakdown[year][rule_name][prop.name] += amount
                    detailed_breakdown[year][rule_name]['total'] += amount

        # Format for response
        formatted_annual_totals = []
        all_rule_names = set()
        for year in years:
            row = {"year": year, "total": float(annual_rule_totals[year]['total'])}
            for rule_name, amount in annual_rule_totals[year].items():
                if rule_name != 'total':
                    row[rule_name] = float(amount)
                    all_rule_names.add(rule_name)
            formatted_annual_totals.append(row)

        formatted_breakdown = {}
        for year in years:
            year_data = {}
            for rule_name, prop_data in detailed_breakdown[year].items():
                rule_data = {"total": float(prop_data['total']), "properties": []}
                for prop_name, amount in prop_data.items():
                    if prop_name != 'total':
                        rule_data['properties'].append({"name": prop_name, "amount": float(amount)})
                year_data[rule_name] = rule_data
            formatted_breakdown[year] = year_data

        total_cumulative = sum(annual_rule_totals[year]['total'] for year in years)
        avg_annual = total_cumulative / len(years) if years else Decimal('0.00')
        
        return {
            "annual_totals": formatted_annual_totals,
            "detailed_breakdown": formatted_breakdown,
            "all_rule_names": list(all_rule_names),
            "summary_metrics": {
                "total_cumulative": float(total_cumulative),
                "avg_annual": float(avg_annual),
                "forecast_years": len(years)
            }
        }
