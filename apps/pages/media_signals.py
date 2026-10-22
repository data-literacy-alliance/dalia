"""Remove the stored file once a MediaImage row is deleted (and the delete committed)."""

from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from pages.models import MediaImage


@receiver(post_delete, sender=MediaImage)
def delete_image_file(sender, instance, **kwargs):
    name = instance.image.name if instance.image else ""
    if not name:
        return
    storage = instance.image.storage
    transaction.on_commit(lambda: storage.delete(name))
