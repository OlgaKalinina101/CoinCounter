"""
Django signals for dashboard application.

Automatically populates month and year fields for Deal and Lead models
based on their modification dates.

Note: Transaction model handles month/year in its save() method,
so no signal is needed for it.
"""
from django.db.models.signals import pre_save
from django.dispatch import receiver

from coin_desk.models import Deal, Lead


@receiver(pre_save, sender=Deal)
def set_deal_month_year(sender, instance, **kwargs):
    """Populate month and year fields for Deal based on date_modify."""
    if instance.date_modify:
        instance.month = instance.date_modify.month
        instance.year = instance.date_modify.year
    else:
        instance.month = None
        instance.year = None


@receiver(pre_save, sender=Lead)
def set_lead_month_year(sender, instance, **kwargs):
    """Populate month and year fields for Lead based on date_modify."""
    if instance.date_modify:
        instance.month = instance.date_modify.month
        instance.year = instance.date_modify.year
    else:
        instance.month = None
        instance.year = None

