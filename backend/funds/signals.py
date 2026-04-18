from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Fund, ModelInput, InvestmentRound, CurrentDeal, InvestorAction, CurrentInvestorStats, InvestorRequest, PossibleCapitalSource
from datetime import datetime

@receiver(post_save, sender=InvestorRequest)
def investor_request_created(sender, instance, created, **kwargs):
    """Automatically create a PossibleCapitalSource entry for investment requests."""
    if created and instance.type == 'INVESTMENT':
        PossibleCapitalSource.objects.create(
            fund=instance.fund,
            name=f"Req: {instance.user.first_name} {instance.user.last_name} ({instance.user.email})",
            amount=instance.requested_amount,
            year=datetime.now().year
        )

@receiver(post_save, sender=Fund)
def create_fund_model_inputs(sender, instance, created, **kwargs):
    if created:
        ModelInput.objects.create(fund=instance)

@receiver(post_save, sender=InvestmentRound)
def round_saved(sender, instance, **kwargs):
    """Trigger recalculation when a round is saved."""
    InvestmentRound.recalculate_for_company(instance.fund, instance.company_name)

@receiver(post_delete, sender=InvestmentRound)
def round_deleted(sender, instance, **kwargs):
    """Trigger recalculation when a round is deleted."""
    InvestmentRound.recalculate_for_company(instance.fund, instance.company_name)

@receiver(post_save, sender=CurrentDeal)
def deal_saved(sender, instance, **kwargs):
    """
    If a pro-rata deal is saved, sync its amount_invested back to the associated InvestmentRound,
    and trigger recalculation.
    """
    if instance.is_pro_rata:
        # Avoid recursion by checking if round already has this amount
        try:
            round_obj = instance.investment_round
            if float(round_obj.amount_invested) != float(instance.amount_invested):
                InvestmentRound.objects.filter(id=round_obj.id).update(amount_invested=instance.amount_invested)
                # After updating the round amount, we must recalculate
                InvestmentRound.recalculate_for_company(instance.fund, instance.company_name)
        except InvestmentRound.DoesNotExist:
            pass
    elif not instance.is_pro_rata:
        # If the main deal is updated (e.g. initial amount), recalculate all rounds
        InvestmentRound.recalculate_for_company(instance.fund, instance.company_name)

@receiver(post_delete, sender=CurrentDeal)
def deal_deleted(sender, instance, **kwargs):
    """If a deal is deleted, recalculate company rounds."""
    InvestmentRound.recalculate_for_company(instance.fund, instance.company_name)

@receiver(post_save, sender=InvestorAction)
def investor_action_saved(sender, instance, **kwargs):
    """If any action is saved, recalcaulte investor statistics."""
    CurrentInvestorStats.recalculate_investor_stats(instance, instance.investor, instance.fund, "save")

@receiver(post_delete, sender=InvestorAction)
def investor_action_deleted(sender, instance, **kwargs):
    """If any action is deleted, recalcaulte investor statistics."""
    CurrentInvestorStats.recalculate_investor_stats(instance, instance.investor, instance.fund, "delete")