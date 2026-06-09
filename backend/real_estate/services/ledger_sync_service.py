from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import date
from ..models import (
    RealEstatePortfolio,
    Property,
    PropertySale,
    FinancingEntry,
    InstallmentEntry,
    RealEstateInvestorAction,
    LedgerAccount,
    LedgerYear,
    LedgerTransaction
)
from .ledger_service import LedgerTransactionService, LedgerYearService

class LedgerSyncService:
    @staticmethod
    def _get_account(portfolio, name):
        return LedgerAccount.objects.get(portfolio=portfolio, name=name)

    @staticmethod
    @transaction.atomic
    def sync_historical_data(portfolio: RealEstatePortfolio, target_year: int):
        """
        Calculates cumulative balances from inception to (target_year - 1) 
        and creates an opening balance transaction in target_year.
        """
        # 1. Ensure ledger year exists
        ledger_year = LedgerYearService.get_or_create_ledger_year(portfolio, target_year)
        
        # Check if already initialized
        if LedgerTransaction.objects.filter(ledger_year=ledger_year, source_type="OPENING_BALANCE").exists():
            return

        reference_date = date(target_year - 1, 12, 31)
        
        # We need to calculate:
        # ASSETS: Cash, Property Assets
        # LIABILITIES: Mortgage Payable, Installment Payable
        # EQUITY: Paid-in Capital, Retained Earnings
        
        from ..selectors.portfolio_selectors import PortfolioSelectors
        metrics = PortfolioSelectors.get_portfolio_nav_metrics(portfolio, reference_date=reference_date)
        
        entries = []
        
        # 1. Cash Reserves
        cash_account = LedgerSyncService._get_account(portfolio, "Cash")
        cash_amount = Decimal(str(metrics["cash_reserves"]))
        if cash_amount != 0:
            entries.append({
                "account": cash_account,
                "amount": abs(cash_amount),
                "entry_type": "DEBIT" if cash_amount > 0 else "CREDIT"
            })
            
        # 2. Property Assets (Cost Basis for accounting usually, but nav_metrics uses market value)
        # Actually, for a pure T-balance bookkeeping, we should use Cost Basis.
        # But the user asked for "integration with all other parts".
        # Let's use Cost Basis for assets to keep it simple, or Market Value if requested.
        # The plan says "displaying the T-balance... integrated with all other parts".
        # Accounting standards usually use Cost Basis. Let's stick to Cost Basis for now.
        
        property_assets_account = LedgerSyncService._get_account(portfolio, "Property Assets")
        total_cost_basis = portfolio.properties.filter(purchase_date__lte=reference_date).aggregate(total=Sum('purchase_price'))['total'] or Decimal('0.00')
        # Add Usufruct prep costs
        total_prep = sum(p.usufruct_details.prep_cost for p in portfolio.properties.filter(status="USUFRUCT", purchase_date__lte=reference_date) if hasattr(p, 'usufruct_details'))
        total_assets = total_cost_basis + total_prep
        
        if total_assets > 0:
            entries.append({
                "account": property_assets_account,
                "amount": total_assets,
                "entry_type": "DEBIT"
            })

        # 3. Paid-in Capital
        equity_account = LedgerSyncService._get_account(portfolio, "Paid-in Capital")
        total_investments = RealEstateInvestorAction.objects.filter(
            portfolio=portfolio, 
            type="PRIMARY_INVESTMENT",
            year__lt=target_year
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        if total_investments > 0:
            entries.append({
                "account": equity_account,
                "amount": total_investments,
                "entry_type": "CREDIT"
            })

        # 4. Liabilities (Mortgages & Installments)
        total_liabilities = Decimal(str(metrics.get("total_liabilities", 0)))
        if total_liabilities > 0:
            # We need to distinguish between Mortgage and Installment payables for the ledger
            from ..selectors.financing_selectors import FinancingSelectors
            from ..selectors.installment_selectors import InstallmentSelectors

            mortgage_acc = LedgerSyncService._get_account(portfolio, "Mortgage Payable")
            installment_acc = LedgerSyncService._get_account(portfolio, "Installment Payable")
            off_plan_acc = LedgerSyncService._get_account(portfolio, "Off-plan Payable")
            
            # Recalculate granularly for the ledger entries
            # Mortgages
            financing_entries = FinancingEntry.objects.filter(property__portfolio=portfolio, loan_start_date__lte=reference_date)
            for f in financing_entries:
                schedule = FinancingSelectors.get_amortization_schedule(f)
                last_balance = f.loan_amount
                months_per_period = 12 // f.payments_per_year
                for item in schedule:
                    total_months_offset = months_per_period * (item['period'] - 1)
                    payment_date = date(f.loan_start_date.year + (f.loan_start_date.month + total_months_offset - 1) // 12, 
                                        (f.loan_start_date.month + total_months_offset - 1) % 12 + 1, 1)
                    if payment_date <= reference_date:
                        last_balance = Decimal(str(item['ending_balance']))
                    else: break
                
                if last_balance > 0:
                    entries.append({"account": mortgage_acc, "amount": last_balance, "entry_type": "CREDIT"})

            # Installments
            installment_entries = InstallmentEntry.objects.filter(property__portfolio=portfolio, start_date__lte=reference_date)
            for i in installment_entries:
                schedule = InstallmentSelectors.get_installment_schedule(i)
                total_paid = Decimal('0.00')
                total_principal = i.property.purchase_price - i.down_payment
                for item in schedule:
                    y, m = map(int, item['date'].split('-'))
                    if date(y, m, 1) <= reference_date:
                        total_paid += Decimal(str(item['payment']))
                    else: break
                
                remaining = max(Decimal('0.00'), total_principal - total_paid)
                if remaining > 0:
                    entries.append({"account": installment_acc, "amount": remaining, "entry_type": "CREDIT"})

            # Off-plan Payables
            off_plan_properties = portfolio.properties.filter(status="OFF_PLAN", purchase_date__lte=reference_date)
            for opp in off_plan_properties:
                total_price = opp.purchase_price or Decimal('0.00')
                unpaid_milestones = opp.milestones.filter(date__gt=reference_date).filter(date__gt=opp.purchase_date)
                remaining = sum((m.percentage_of_price / Decimal('100.00')) * total_price for m in unpaid_milestones)
                
                if remaining > 0:
                    entries.append({"account": off_plan_acc, "amount": remaining, "entry_type": "CREDIT"})

        # 5. Retained Earnings (The plug to balance the opening transaction if historical P&L isn't tracked)
        re_account = LedgerSyncService._get_account(portfolio, "Retained Earnings")
        
        current_debit = sum((Decimal(str(e["amount"])) for e in entries if e["entry_type"] == "DEBIT"), Decimal('0.00'))
        current_credit = sum((Decimal(str(e["amount"])) for e in entries if e["entry_type"] == "CREDIT"), Decimal('0.00'))
        
        diff = current_debit - current_credit
        if diff != 0:
            entries.append({
                "account": re_account,
                "amount": abs(diff),
                "entry_type": "CREDIT" if diff > 0 else "DEBIT"
            })

        if entries:
            LedgerTransactionService.create_transaction(
                portfolio=portfolio,
                ledger_year=ledger_year,
                description=f"Cumulative Opening Balance for {target_year}",
                date=date(target_year, 1, 1),
                entries=entries,
                source_type="OPENING_BALANCE"
            )

    @staticmethod
    @transaction.atomic
    def sync_property_acquisition(property_obj: Property):
        """
        Hook for property creation.
        Debit: Property Assets
        Credit: Cash
        """
        portfolio = property_obj.portfolio
        year = property_obj.purchase_date.year
        ledger_year = LedgerYearService.get_or_create_ledger_year(portfolio, year)
        
        cost = property_obj.purchase_price or Decimal('0.00')
        if property_obj.status == "USUFRUCT":
            cost += getattr(property_obj.usufruct_details, 'prep_cost', Decimal('0.00'))

        if cost == 0:
            return

        entries = [
            {"account": LedgerSyncService._get_account(portfolio, "Property Assets"), "amount": cost, "entry_type": "DEBIT"},
            {"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": cost, "entry_type": "CREDIT"}
        ]

        LedgerTransactionService.create_transaction(
            portfolio=portfolio,
            ledger_year=ledger_year,
            description=f"Acquisition of {property_obj.name}",
            date=property_obj.purchase_date,
            entries=entries,
            source_type="PROPERTY_ACQUISITION",
            source_id=property_obj.id
        )

    @staticmethod
    @transaction.atomic
    def sync_investor_investment(action: RealEstateInvestorAction):
        """
        Hook for capital injection.
        Debit: Cash
        Credit: Paid-in Capital
        """
        if action.type != "PRIMARY_INVESTMENT":
            return

        portfolio = action.portfolio
        year = action.year
        ledger_year = LedgerYearService.get_or_create_ledger_year(portfolio, year)
        
        amount = action.amount or Decimal('0.00')
        if amount == 0:
            return

        entries = [
            {"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": amount, "entry_type": "DEBIT"},
            {"account": LedgerSyncService._get_account(portfolio, "Paid-in Capital"), "amount": amount, "entry_type": "CREDIT"}
        ]

        LedgerTransactionService.create_transaction(
            portfolio=portfolio,
            ledger_year=ledger_year,
            description=f"Capital Injection by {action.investor.email}",
            date=date(year, 1, 1), # Action only has year, so we use start of year or current date if in same year
            entries=entries,
            source_type="INVESTOR_INVESTMENT",
            source_id=action.id
        )

    @staticmethod
    @transaction.atomic
    def sync_property_sale(sale: PropertySale):
        """
        Hook for property sale.
        Debit: Cash (Net Proceeds)
        Debit: Mortgage Payable (Loan Payoff)
        Debit: Installment Payable (Installment Payoff)
        Credit: Property Assets (Cost Basis)
        Credit/Debit: Retained Earnings (Realized Gain/Loss)
        """
        from ..selectors.property_sale_selectors import PropertySaleSelector
        metrics = PropertySaleSelector.calculate_sale_metrics(sale)
        m = metrics["metrics"]
        
        portfolio = sale.property.portfolio
        ledger_year = LedgerYearService.get_or_create_ledger_year(portfolio, sale.sale_date.year)
        
        entries = []
        # 1. Cash (Net Proceeds)
        if m["net_proceeds"] != 0:
            entries.append({"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": abs(m["net_proceeds"]), "entry_type": "DEBIT" if m["net_proceeds"] > 0 else "CREDIT"})
        
        # 2. Mortgage Payable (Loan Payoff)
        if m["loan_payoff"] > 0:
            entries.append({"account": LedgerSyncService._get_account(portfolio, "Mortgage Payable"), "amount": m["loan_payoff"], "entry_type": "DEBIT"})
            
        # 3. Installment Payable (Installment Payoff)
        if m.get("installment_payoff", 0) > 0:
            entries.append({"account": LedgerSyncService._get_account(portfolio, "Installment Payable"), "amount": m["installment_payoff"], "entry_type": "DEBIT"})

        # 3.5 Off-plan Payable (Off-plan Payoff)
        if sale.property.status == "OFF_PLAN":
             total_price = sale.property.purchase_price or Decimal('0.00')
             unpaid_milestones = sale.property.milestones.filter(date__gt=sale.sale_date).filter(date__gt=sale.property.purchase_date)
             off_plan_payoff = sum((m.percentage_of_price / Decimal('100.00')) * total_price for m in unpaid_milestones)
             if off_plan_payoff > 0:
                 entries.append({"account": LedgerSyncService._get_account(portfolio, "Off-plan Payable"), "amount": off_plan_payoff, "entry_type": "DEBIT"})

        # 4. Property Assets (Cost Basis)
        if m["cost_basis"] > 0:
            entries.append({"account": LedgerSyncService._get_account(portfolio, "Property Assets"), "amount": m["cost_basis"], "entry_type": "CREDIT"})
            
        # 5. Retained Earnings (Realized Gain/Loss - Dynamic Balancing Plug)
        # We calculate the balancing figure to ensure the transaction always balances.
        current_debit = sum(e["amount"] for e in entries if e["entry_type"] == "DEBIT")
        current_credit = sum(e["amount"] for e in entries if e["entry_type"] == "CREDIT")
        balancing_diff = current_debit - current_credit
        
        if balancing_diff != 0:
            entries.append({
                "account": LedgerSyncService._get_account(portfolio, "Retained Earnings"), 
                "amount": abs(balancing_diff), 
                "entry_type": "CREDIT" if balancing_diff > 0 else "DEBIT"
            })

        LedgerTransactionService.create_transaction(
            portfolio=portfolio,
            ledger_year=ledger_year,
            description=f"Sale of {sale.property.name}",
            date=sale.sale_date,
            entries=entries,
            source_type="PROPERTY_SALE",
            source_id=sale.id
        )

    @staticmethod
    @transaction.atomic
    def sync_financing_entry(entry: FinancingEntry):
        """
        Hook for loan creation.
        Debit: Cash
        Credit: Mortgage Payable
        """
        portfolio = entry.property.portfolio
        ledger_year = LedgerYearService.get_or_create_ledger_year(portfolio, entry.loan_start_date.year)
        
        entries = [
            {"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": entry.loan_amount, "entry_type": "DEBIT"},
            {"account": LedgerSyncService._get_account(portfolio, "Mortgage Payable"), "amount": entry.loan_amount, "entry_type": "CREDIT"}
        ]

        LedgerTransactionService.create_transaction(
            portfolio=portfolio,
            ledger_year=ledger_year,
            description=f"Mortgage Loan for {entry.property.name}",
            date=entry.loan_start_date,
            entries=entries,
            source_type="FINANCING_CREATION",
            source_id=entry.id
        )

    @staticmethod
    @transaction.atomic
    def sync_projected_cash_flow(portfolio: RealEstatePortfolio, year: int):
        """
        Pull projected Rent, Opex, Taxes, and Financing (Interest/Principal) from selectors into the ledger.
        Creates separate transactions for better clarity in the T-balance.
        """
        from ..selectors.cash_flow_selectors import CashFlowSelectors
        from ..selectors.financing_selectors import FinancingSelectors
        from ..selectors.installment_selectors import InstallmentSelectors
        import logging
        logger = logging.getLogger(__name__)
        
        cf_data = CashFlowSelectors.get_portfolio_cash_flow(portfolio, start_year=year, end_year=year)
        ledger_year = LedgerYearService.get_or_create_ledger_year(portfolio, year)
        
        # Delete existing sync to allow refresh/re-sync
        LedgerTransaction.objects.filter(ledger_year=ledger_year, source_type="CASH_FLOW_SYNC").delete()

        # 1. Rental Income
        total_effective_rent = Decimal('0.00')
        for prop_id, prop_data in cf_data["properties"].items():
            meta = prop_data["metadata"].get(year)
            if meta:
                total_effective_rent += meta["effective_rent"]

        if total_effective_rent > 0:
            LedgerTransactionService.create_transaction(
                portfolio=portfolio,
                ledger_year=ledger_year,
                description=f"Projected Rental Income for {year}",
                date=date(year, 12, 31),
                entries=[
                    {"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": total_effective_rent, "entry_type": "DEBIT"},
                    {"account": LedgerSyncService._get_account(portfolio, "Rental Income"), "amount": total_effective_rent, "entry_type": "CREDIT"}
                ],
                source_type="CASH_FLOW_SYNC"
            )

        # 2. Operating Expenses
        total_opex = Decimal('0.00')
        for prop_id, prop_data in cf_data["properties"].items():
            meta = prop_data["metadata"].get(year)
            if meta:
                total_opex += meta["opex"]

        if total_opex > 0:
            LedgerTransactionService.create_transaction(
                portfolio=portfolio,
                ledger_year=ledger_year,
                description=f"Projected Operating Expenses for {year}",
                date=date(year, 12, 31),
                entries=[
                    {"account": LedgerSyncService._get_account(portfolio, "Operational Expenses"), "amount": total_opex, "entry_type": "DEBIT"},
                    {"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": total_opex, "entry_type": "CREDIT"}
                ],
                source_type="CASH_FLOW_SYNC"
            )

        # 3. Financing (Mortgages)
        total_interest = Decimal('0.00')
        total_principal = Decimal('0.00')
        
        mortgage_entries = FinancingEntry.objects.filter(property__portfolio=portfolio)
        for me in mortgage_entries:
            schedule = FinancingSelectors.get_amortization_schedule(me)
            months_per_period = 12 // me.payments_per_year
            for item in schedule:
                total_months_offset = months_per_period * (item['period'] - 1)
                payment_date = date(me.loan_start_date.year + (me.loan_start_date.month + total_months_offset - 1) // 12, 
                                    (me.loan_start_date.month + total_months_offset - 1) % 12 + 1, 1)
                if payment_date.year == year:
                    total_interest += item['interest_payment']
                    total_principal += item['principal_payment']

        if total_interest > 0 or total_principal > 0:
            entries = []
            if total_interest > 0:
                entries.append({"account": LedgerSyncService._get_account(portfolio, "Financing Expenses"), "amount": total_interest, "entry_type": "DEBIT"})
            if total_principal > 0:
                entries.append({"account": LedgerSyncService._get_account(portfolio, "Mortgage Payable"), "amount": total_principal, "entry_type": "DEBIT"})
            
            entries.append({"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": total_interest + total_principal, "entry_type": "CREDIT"})

            LedgerTransactionService.create_transaction(
                portfolio=portfolio,
                ledger_year=ledger_year,
                description=f"Projected Mortgage Payment for {year}",
                date=date(year, 12, 31),
                entries=entries,
                source_type="CASH_FLOW_SYNC"
            )

        # 4. Installments
        total_inst_pmt = Decimal('0.00')
        installment_entries = InstallmentEntry.objects.filter(property__portfolio=portfolio)
        for ie in installment_entries:
            schedule = InstallmentSelectors.get_installment_schedule(ie)
            for item in schedule:
                y = int(item['date'].split('-')[0])
                if y == year:
                    total_inst_pmt += Decimal(str(item['payment']))

        if total_inst_pmt > 0:
            LedgerTransactionService.create_transaction(
                portfolio=portfolio,
                ledger_year=ledger_year,
                description=f"Projected Installment Payment for {year}",
                date=date(year, 12, 31),
                entries=[
                    {"account": LedgerSyncService._get_account(portfolio, "Installment Payable"), "amount": total_inst_pmt, "entry_type": "DEBIT"},
                    {"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": total_inst_pmt, "entry_type": "CREDIT"}
                ],
                source_type="CASH_FLOW_SYNC"
            )

        # 5. Off-plan Milestones
        total_milestone_pmt = Decimal('0.00')
        off_plan_properties = portfolio.properties.filter(status="OFF_PLAN")
        for opp in off_plan_properties:
            for m in opp.milestones.filter(date__year=year):
                if m.date > opp.purchase_date:
                    total_milestone_pmt += (m.percentage_of_price / Decimal('100.00')) * (opp.purchase_price or Decimal('0.00'))

        if total_milestone_pmt > 0:
            LedgerTransactionService.create_transaction(
                portfolio=portfolio,
                ledger_year=ledger_year,
                description=f"Projected Milestone Payment for {year}",
                date=date(year, 12, 31),
                entries=[
                    {"account": LedgerSyncService._get_account(portfolio, "Off-plan Payable"), "amount": total_milestone_pmt, "entry_type": "DEBIT"},
                    {"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": total_milestone_pmt, "entry_type": "CREDIT"}
                ],
                source_type="CASH_FLOW_SYNC"
            )

        # 6. Taxes
        total_taxes = cf_data["portfolio_taxes"].get(year, Decimal('0.00'))
        if total_taxes > 0:
            LedgerTransactionService.create_transaction(
                portfolio=portfolio,
                ledger_year=ledger_year,
                description=f"Projected Tax Expense for {year}",
                date=date(year, 12, 31),
                entries=[
                    {"account": LedgerSyncService._get_account(portfolio, "Tax Expense"), "amount": total_taxes, "entry_type": "DEBIT"},
                    {"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": total_taxes, "entry_type": "CREDIT"}
                ],
                source_type="CASH_FLOW_SYNC"
            )

    @staticmethod
    @transaction.atomic
    def sync_installment_entry(entry: InstallmentEntry):
        """
        Hook for installment plan creation.
        Debit: Cash (Refund of the financed portion from the initial asset acquisition)
        Credit: Installment Payable
        """
        portfolio = entry.property.portfolio
        ledger_year = LedgerYearService.get_or_create_ledger_year(portfolio, entry.start_date.year)
        
        # The amount to be financed
        financed_amount = entry.property.purchase_price - entry.down_payment
        if financed_amount <= 0:
            return

        entries = [
            {"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": financed_amount, "entry_type": "DEBIT"},
            {"account": LedgerSyncService._get_account(portfolio, "Installment Payable"), "amount": financed_amount, "entry_type": "CREDIT"}
        ]

        LedgerTransactionService.create_transaction(
            portfolio=portfolio,
            ledger_year=ledger_year,
            description=f"Installment Plan for {entry.property.name}",
            date=entry.start_date,
            entries=entries,
            source_type="FINANCING_CREATION",
            source_id=entry.id
        )

    @staticmethod
    @transaction.atomic
    def sync_off_plan_creation(property_obj: Property):
        """
        Hook for off-plan property creation/milestone update.
        Debit: Cash (Refund of the portion to be paid via milestones)
        Credit: Off-plan Payable
        """
        portfolio = property_obj.portfolio
        if property_obj.status != "OFF_PLAN":
            # Delete if status changed from OFF_PLAN
            LedgerTransactionService.delete_transaction_by_source(
                source_type="OFF_PLAN_PAYABLE_CREATION",
                source_id=property_obj.id
            )
            return

        # Delete existing to allow update
        LedgerTransactionService.delete_transaction_by_source(
            source_type="OFF_PLAN_PAYABLE_CREATION",
            source_id=property_obj.id
        )

        total_price = property_obj.purchase_price or Decimal('0.00')
        if total_price == 0:
            return

        # Payable is the sum of milestones AFTER purchase_date
        payable_amount = Decimal('0.00')
        for m in property_obj.milestones.all():
            if m.date > property_obj.purchase_date:
                payable_amount += (m.percentage_of_price / Decimal('100.00')) * total_price

        if payable_amount <= 0:
            return

        ledger_year = LedgerYearService.get_or_create_ledger_year(portfolio, property_obj.purchase_date.year)
        
        entries = [
            {"account": LedgerSyncService._get_account(portfolio, "Cash"), "amount": payable_amount, "entry_type": "DEBIT"},
            {"account": LedgerSyncService._get_account(portfolio, "Off-plan Payable"), "amount": payable_amount, "entry_type": "CREDIT"}
        ]

        LedgerTransactionService.create_transaction(
            portfolio=portfolio,
            ledger_year=ledger_year,
            description=f"Off-plan Payable Recognition for {property_obj.name}",
            date=property_obj.purchase_date,
            entries=entries,
            source_type="OFF_PLAN_PAYABLE_CREATION",
            source_id=property_obj.id
        )
