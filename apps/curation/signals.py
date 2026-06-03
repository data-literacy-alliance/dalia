from django.db.models.signals import post_save
from django.dispatch import receiver

from curation.models.resources import Resource, ResourceContent


@receiver(post_save, sender=Resource)
def clear_review_on_publish(sender, instance, **kwargs):
    """
    Publishing a Resource moves it to state 2 (published).
    Clear submitted_for_review on all its contents so no content stays in
    the ambiguous state where is_published=True and submitted_for_review=True.
    Uses queryset.update() to bypass post_save signals on ResourceContent.
    """
    if instance.is_published:
        instance.contents.filter(submitted_for_review=True).update(submitted_for_review=False)


@receiver(post_save, sender=ResourceContent)
def auto_activate_first_version(sender, instance, created, **kwargs):
    """Set is_active and version on the first content created for a resource."""
    if not created:
        return
    siblings = ResourceContent.objects.filter(resource_id=instance.resource_id)
    version_number = siblings.count()  # count includes the just-inserted row
    updates = {"version": version_number}
    already_active = siblings.exclude(pk=instance.pk).filter(is_active=True).exists()
    if not already_active:
        updates["is_active"] = True
    ResourceContent.objects.filter(pk=instance.pk).update(**updates)
