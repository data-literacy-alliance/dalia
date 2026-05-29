from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from pages.models import Page


def _delete_file(file_field):
    if file_field and file_field.name:
        try:
            storage = file_field.storage
            if storage.exists(file_field.name):
                storage.delete(file_field.name)
        except Exception:
            pass


@receiver(pre_save, sender=Page)
def delete_old_docx_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Page.objects.get(pk=instance.pk)
    except Page.DoesNotExist:
        return
    old_file = old.docx_file
    new_file = instance.docx_file
    if old_file and old_file != new_file:
        _delete_file(old_file)


@receiver(post_delete, sender=Page)
def delete_docx_on_page_delete(sender, instance, **kwargs):
    _delete_file(instance.docx_file)
