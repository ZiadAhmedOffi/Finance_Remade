from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import RealEstateInvestorAction, RealEstateInvestorStats

@receiver(post_save, sender=RealEstateInvestorAction)
def investor_action_saved(sender, instance, **kwargs):
    """Recalculate stats for the investor (and seller/buyer in secondary cases)."""
    RealEstateInvestorStats.recalculate_investor_stats(instance.investor, instance.portfolio)
    if instance.investor_selling:
        RealEstateInvestorStats.recalculate_investor_stats(instance.investor_selling, instance.portfolio)
    if instance.investor_sold_to:
        RealEstateInvestorStats.recalculate_investor_stats(instance.investor_sold_to, instance.portfolio)

@receiver(post_delete, sender=RealEstateInvestorAction)
def investor_action_deleted(sender, instance, **kwargs):
    """Recalculate stats for the investor (and seller/buyer in secondary cases)."""
    RealEstateInvestorStats.recalculate_investor_stats(instance.investor, instance.portfolio)
    if instance.investor_selling:
        RealEstateInvestorStats.recalculate_investor_stats(instance.investor_selling, instance.portfolio)
    if instance.investor_sold_to:
        RealEstateInvestorStats.recalculate_investor_stats(instance.investor_sold_to, instance.portfolio)
