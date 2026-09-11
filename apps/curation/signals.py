from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from curation.models.resources import Resource, ResourceContent


@receiver(post_save, sender=Resource)
def clear_review_on_publish(sender, instance, **kwargs):
    """
    When a Resource is saved with is_published=True, clear submitted_for_review on all its
    contents. Guards on update_fields so unrelated Resource saves (e.g. title edits) do not
    accidentally clear pending submissions from other users.
    Preserves submitted_at and submitted_by for audit history.
    """
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and "is_published" not in update_fields:
        return
    if instance.is_published:
        instance.contents.filter(submitted_for_review=True).update(submitted_for_review=False)


@receiver(pre_save, sender=ResourceContent)
def capture_rc_is_active_before_save(sender, instance, **kwargs):
    """Capture current is_active before saving so handle_rc_activated can detect the change."""
    if instance.pk:
        instance._pre_save_is_active = (
            ResourceContent.objects.filter(pk=instance.pk)
            .values_list("is_active", flat=True)
            .first()
        ) or False
    else:
        instance._pre_save_is_active = False


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


@receiver(post_save, sender=ResourceContent)
def handle_rc_activated(sender, instance, created, **kwargs):
    """
    When an RC is activated via the admin form (is_active flips False→True via .save()):
    - deactivate all sibling RCs
    - clear submitted_for_review on all RCs of the same resource (incl. the activated one)
    Does NOT fire from queryset .update() calls (only triggered by .save()).
    Preserves submitted_at and submitted_by for audit history.
    """
    if created:
        return  # auto_activate_first_version handles creation
    was_active = getattr(instance, "_pre_save_is_active", None)
    if not instance.is_active or instance.is_active == was_active:
        return
    ResourceContent.objects.filter(resource_id=instance.resource_id).exclude(pk=instance.pk).update(
        is_active=False, submitted_for_review=False
    )
    ResourceContent.objects.filter(pk=instance.pk).update(submitted_for_review=False)
