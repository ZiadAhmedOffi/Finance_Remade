from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Fund, ModelInput

@receiver(post_save, sender=Fund)
def create_fund_model_inputs(sender, instance, created, **kwargs):
    if created:
        ModelInput.objects.create(fund=instance)
