from django.db import transaction
from funds.models import InvestmentDeal, CurrentDeal, InvestmentRound, FundLog
from users.services.audit_service import AuditService
from funds.selectors import fund_selectors, deal_selectors

class DealService:
    @transaction.atomic
    def create_investment_deal(self, fund, actor, data, ip_address):
        deal = InvestmentDeal.objects.create(fund=fund, **data)
        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="DEAL_CREATED",
            metadata={"deal_id": str(deal.id), "company_name": deal.company_name}
        )
        AuditService.log(
            actor=actor,
            action="DEAL_CREATED",
            fund=fund,
            metadata={"deal_id": str(deal.id), "company_name": deal.company_name},
            ip=ip_address
        )
        return deal

    @transaction.atomic
    def update_investment_deal(self, deal_id, actor, data, ip_address):
        deal = deal_selectors.get_deal_by_id(deal_id)
        if not deal:
            raise ValueError("Deal not found")
        for attr, value in data.items():
            setattr(deal, attr, value)
        deal.save()
        FundLog.objects.create(
            actor=actor,
            target_fund=deal.fund,
            action="DEAL_UPDATED",
            metadata={"deal_id": str(deal.id), "company_name": deal.company_name}
        )
        AuditService.log(
            actor=actor,
            action="DEAL_UPDATED",
            fund=deal.fund,
            metadata={"deal_id": str(deal.id), "company_name": deal.company_name},
            ip=ip_address
        )
        return deal

    @transaction.atomic
    def delete_investment_deal(self, deal_id, actor, ip_address):
        deal = deal_selectors.get_deal_by_id(deal_id)
        if not deal:
            raise ValueError("Deal not found")
        fund = deal.fund
        company_name = deal.company_name
        deal_uuid = str(deal.id)
        deal.delete()
        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="DEAL_DELETED",
            metadata={"deal_id": deal_uuid, "company_name": company_name}
        )
        AuditService.log(
            actor=actor,
            action="DEAL_DELETED",
            fund=fund,
            metadata={"deal_id": deal_uuid, "company_name": company_name},
            ip=ip_address
        )
        return True

    @transaction.atomic
    def create_current_deal(self, fund, actor, data, ip_address):
        deal = CurrentDeal.objects.create(fund=fund, **data)
        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="CURRENT_DEAL_CREATED",
            metadata={"deal_id": str(deal.id), "company_name": deal.company_name}
        )
        AuditService.log(
            actor=actor,
            action="CURRENT_DEAL_CREATED",
            fund=fund,
            metadata={"deal_id": str(deal.id), "company_name": deal.company_name},
            ip=ip_address
        )
        return deal

    @transaction.atomic
    def update_current_deal(self, deal_id, actor, data, ip_address):
        deal = deal_selectors.get_current_deal_by_id(deal_id)
        if not deal:
            raise ValueError("Current deal not found")
        for attr, value in data.items():
            setattr(deal, attr, value)
        deal.save()
        FundLog.objects.create(
            actor=actor,
            target_fund=deal.fund,
            action="CURRENT_DEAL_UPDATED",
            metadata={"deal_id": str(deal.id), "company_name": deal.company_name}
        )
        AuditService.log(
            actor=actor,
            action="CURRENT_DEAL_UPDATED",
            fund=deal.fund,
            metadata={"deal_id": str(deal.id), "company_name": deal.company_name},
            ip=ip_address
        )
        return deal

    @transaction.atomic
    def delete_current_deal(self, deal_id, actor, ip_address):
        deal = deal_selectors.get_current_deal_by_id(deal_id)
        if not deal:
            raise ValueError("Current deal not found")
        fund = deal.fund
        company_name = deal.company_name
        deal_uuid = str(deal.id)
        deal.delete()
        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="CURRENT_DEAL_DELETED",
            metadata={"deal_id": deal_uuid, "company_name": company_name}
        )
        AuditService.log(
            actor=actor,
            action="CURRENT_DEAL_DELETED",
            fund=fund,
            metadata={"deal_id": deal_uuid, "company_name": company_name},
            ip=ip_address
        )
        return True

    @transaction.atomic
    def create_investment_round(self, fund, actor, data, ip_address):
        company_name = data["company_name"]
        exercise_pro_rata = data.get("exercise_pro_rata", False)
        amount_invested = data.get("amount_invested", 0)
        target_valuation = data["target_valuation"]
        year = data["year"]

        main_deal = fund.current_deals.filter(company_name=company_name, is_pro_rata=False).first()
        round_obj = InvestmentRound.objects.create(fund=fund, **data)

        associated_deal = None
        if exercise_pro_rata and amount_invested > 0:
            associated_deal = CurrentDeal.objects.create(
                fund=fund,
                company_name=company_name,
                company_type=main_deal.company_type if main_deal else "",
                industry=main_deal.industry if main_deal else "",
                entry_year=year,
                latest_valuation_year=year,
                amount_invested=amount_invested,
                entry_valuation=target_valuation,
                latest_valuation=target_valuation,
                is_pro_rata=True,
                parent_deal=main_deal
            )

        fund.current_deals.filter(company_name=company_name).update(
            latest_valuation=target_valuation,
            latest_valuation_year=year
        )

        if associated_deal:
            round_obj.associated_deal = associated_deal
            round_obj.save()

        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="ROUND_CREATED",
            metadata={"company_name": company_name, "round_id": str(round_obj.id)}
        )
        AuditService.log(
            actor=actor,
            action="ROUND_CREATED",
            fund=fund,
            metadata={"round_id": str(round_obj.id), "company_name": company_name},
            ip=ip_address
        )
        return round_obj

    @transaction.atomic
    def update_investment_round(self, round_id, actor, data, ip_address):
        round_obj = deal_selectors.get_round_by_id(round_id)
        if not round_obj:
            raise ValueError("Round not found")

        fund = round_obj.fund
        company_name = data.get("company_name", round_obj.company_name)
        exercise_pro_rata = data.get("exercise_pro_rata", round_obj.exercise_pro_rata)
        amount_invested = data.get("amount_invested", round_obj.amount_invested)
        target_valuation = data.get("target_valuation", round_obj.target_valuation)
        year = data.get("year", round_obj.year)

        for attr, value in data.items():
            setattr(round_obj, attr, value)
        round_obj.save()

        if exercise_pro_rata and amount_invested > 0:
            main_deal = fund.current_deals.filter(company_name=company_name, is_pro_rata=False).first()
            if round_obj.associated_deal:
                deal = round_obj.associated_deal
                deal.amount_invested = amount_invested
                deal.entry_year = year
                deal.latest_valuation_year = year
                deal.entry_valuation = target_valuation
                deal.latest_valuation = target_valuation
                deal.save()
            else:
                new_deal = CurrentDeal.objects.create(
                    fund=fund,
                    company_name=company_name,
                    company_type=main_deal.company_type if main_deal else "",
                    industry=main_deal.industry if main_deal else "",
                    entry_year=year,
                    latest_valuation_year=year,
                    amount_invested=amount_invested,
                    entry_valuation=target_valuation,
                    latest_valuation=target_valuation,
                    is_pro_rata=True,
                    parent_deal=main_deal
                )
                round_obj.associated_deal = new_deal
                round_obj.save()
        elif round_obj.associated_deal:
            round_obj.associated_deal.delete()

        fund.current_deals.filter(company_name=company_name).update(
            latest_valuation=target_valuation,
            latest_valuation_year=year
        )

        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="ROUND_UPDATED",
            metadata={"company_name": company_name, "round_id": str(round_obj.id)}
        )
        AuditService.log(
            actor=actor,
            action="ROUND_UPDATED",
            fund=fund,
            metadata={"round_id": str(round_obj.id), "company_name": company_name},
            ip=ip_address
        )
        return round_obj

    @transaction.atomic
    def delete_investment_round(self, round_id, actor, ip_address):
        round_obj = deal_selectors.get_round_by_id(round_id)
        if not round_obj:
            raise ValueError("Round not found")
        
        fund = round_obj.fund
        company_name = round_obj.company_name
        round_uuid = str(round_obj.id)

        # Delete associated deal if exists
        if round_obj.associated_deal:
            round_obj.associated_deal.delete()
            
        round_obj.delete()

        # Recalculate latest valuation from the remaining rounds
        remaining_rounds = fund.investment_rounds.filter(company_name=company_name).order_by('-year', '-created_at')
        if remaining_rounds.exists():
            latest = remaining_rounds.first()
            fund.current_deals.filter(company_name=company_name).update(
                latest_valuation=latest.target_valuation,
                latest_valuation_year=latest.year
            )
        else:
            # Revert to original deal entry valuation if possible
            main_deal = fund.current_deals.filter(company_name=company_name, is_pro_rata=False).first()
            if main_deal:
                fund.current_deals.filter(company_name=company_name).update(
                    latest_valuation=main_deal.entry_valuation,
                    latest_valuation_year=main_deal.entry_year
                )

        # Log the change
        FundLog.objects.create(
            actor=actor,
            target_fund=fund,
            action="ROUND_DELETED",
            metadata={"round_id": round_uuid, "company_name": company_name}
        )
        AuditService.log(
            actor=actor,
            action="ROUND_DELETED",
            fund=fund,
            metadata={"round_id": round_uuid, "company_name": company_name},
            ip=ip_address
        )
        return True
