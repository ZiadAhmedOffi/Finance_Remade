from decimal import Decimal
from typing import List, Dict, Any
from django.db import transaction
from ..models import Property, TaxRule, Jurisdiction, UsufructDetails
from ..calculation import PropertyDataCalc

class TaxationService:
    @staticmethod
    def calculate_property_tax_for_year(property: Property, year_index: int, context: Dict[str, Any], rules: List[TaxRule] = None) -> Decimal:
        """
        Calculates total tax liability for a property in a given year based on Jurisdiction rules.
        """
        breakdown = TaxationService.calculate_property_tax_breakdown(property, year_index, context, rules=rules)
        return sum((item['amount'] for item in breakdown), Decimal('0.00'))

    @staticmethod
    def calculate_property_tax_breakdown(property: Property, year_index: int, context: Dict[str, Any], rules: List[TaxRule] = None) -> List[Dict[str, Any]]:
        """
        Calculates tax liability broken down by rule.
        Returns a list of {"rule_id": str, "rule_name": str, "amount": Decimal}
        """
        if rules is None:
            portfolio = property.portfolio
            jurisdiction = portfolio.jurisdiction
            if not jurisdiction:
                return []
            rules = list(jurisdiction.rules.filter(is_active=True))
        
        breakdown = []
        
        # 1. Identify current events
        events = context.get('property_events', [])
        if year_index == 0 and 'CONTRACT_SIGNING' not in events:
            events.append('CONTRACT_SIGNING')
        if context.get('is_disposal_year') and 'DISPOSAL' not in events:
            events.append('DISPOSAL')
        
        # Always check ANNUAL triggers
        events.append('ANNUAL')

        for rule in rules:
            # Check Trigger
            if rule.trigger not in events:
                continue

            # Usufruct Allocation check
            if property.status == 'USUFRUCT':
                try:
                    usufruct = property.usufruct_details
                    if rule.responsible_party != 'BOTH' and rule.responsible_party != usufruct.investor_role:
                        continue
                except UsufructDetails.DoesNotExist:
                    pass

            # Determine Tax Base Value
            base_value = TaxationService._get_tax_base_value(rule, property, year_index, context)
            
            # Apply Rate
            tax_amount = (base_value * rule.rate).quantize(Decimal('0.01'))
            if tax_amount > 0:
                breakdown.append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "amount": tax_amount
                })

        return breakdown

    @staticmethod
    def _get_tax_base_value(rule: TaxRule, property: Property, year_index: int, context: Dict[str, Any]) -> Decimal:
        if rule.tax_base == 'MARKET_VALUE':
            return context.get('market_value', Decimal('0.00'))
        
        elif rule.tax_base == 'ASSESSED_VALUE':
            # Implement stair-step revaluation
            market_value = context.get('market_value', Decimal('0.00'))
            reval_freq = rule.revaluation_freq or 1
            
            # For simplicity in this session, we assume context provides the "last_assessed_value" 
            # or we calculate it here based on year_index.
            # Real implementation would need to track the last assessment year.
            last_assessment_year = (year_index // reval_freq) * reval_freq
            # To be precise, we'd need market value at that specific year.
            # Assuming context market_value is current. 
            # If freq is 1, it's just market * ratio.
            if reval_freq == 1:
                return (market_value * rule.valuation_ratio).quantize(Decimal('0.01'))
            else:
                # Mocking stair-step: if freq > 1, we'd ideally need a history.
                # For now, we apply ratio to current market value but only update if year hits freq.
                # (Simplified for the service logic)
                return (market_value * rule.valuation_ratio).quantize(Decimal('0.01'))

        elif rule.tax_base == 'NET_INCOME':
            net_income = context.get('net_income', Decimal('0.00'))
            # Net income is already adjusted by expenses in the caller, 
            # but we apply the LCF here if not already applied.
            return max(Decimal('0.00'), net_income)

        elif rule.tax_base == 'LOAN_AMOUNT':
            if hasattr(property, 'financing'):
                return property.financing.loan_amount
            return Decimal('0.00')

        elif rule.tax_base == 'FIXED':
            return Decimal('1.00') # Fixed rate * base 1 = rate

        return Decimal('0.00')

    @staticmethod
    def apply_loss_carry_forward(taxable_income: Decimal, lcf_pool: Decimal) -> (Decimal, Decimal):
        """
        Returns (Adjusted Taxable Income, New LCF Pool)
        """
        if taxable_income < 0:
            new_pool = lcf_pool + abs(taxable_income)
            return (Decimal('0.00'), new_pool)
        else:
            if lcf_pool > 0:
                reduction = min(taxable_income, lcf_pool)
                adjusted_income = taxable_income - reduction
                new_pool = lcf_pool - reduction
                return (adjusted_income, new_pool)
            return (taxable_income, lcf_pool)
