"""Invalidate the cached sending status when its inputs change."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import ContactFormSettings, EmailProvider
from .service import invalidate_sending_status


@receiver([post_save, post_delete], sender=EmailProvider)
@receiver([post_save, post_delete], sender=ContactFormSettings)
def _invalidate_sending_status(sender, **kwargs):
    invalidate_sending_status()
