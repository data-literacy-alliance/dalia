import shutil
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from pages.models import Page, SearchPage, WebsitePage

SEARCH_MEDIA_PARTS = ("pages", "media")
# Proxy saves send ``sender=<proxy class>``, so every concrete and proxy class is connected.
PAGE_MODELS = (Page, SearchPage, WebsitePage)


def _delete_file(file_field):
    if file_field and file_field.name:
        try:
            storage = file_field.storage
            if storage.exists(file_field.name):
                storage.delete(file_field.name)
        except Exception:
            pass


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
        instance._stale_docx = old_file


def delete_stale_docx_after_save(sender, instance, **kwargs):
    """Delete the replaced DOCX only once the save has committed."""
    stale = instance.__dict__.pop("_stale_docx", None)
    if stale is None or stale.name == (instance.docx_file.name if instance.docx_file else None):
        return
    transaction.on_commit(lambda: _delete_file(stale))


def _remove_search_media_dir(pk):
    target = Path(settings.MEDIA_ROOT).joinpath(*SEARCH_MEDIA_PARTS, str(int(pk)))
    shutil.rmtree(target, ignore_errors=True)


def delete_files_on_page_delete(sender, instance, **kwargs):
    _delete_file(instance.docx_file)
    if instance.site == Page.SITE_SEARCH and instance.pk:
        # Search pages keep DOCX images in pages/media/<pk>/; website images belong to MediaImage.
        pk = instance.pk
        transaction.on_commit(lambda: _remove_search_media_dir(pk))


for _model in PAGE_MODELS:
    pre_save.connect(
        delete_old_docx_on_change,
        sender=_model,
        dispatch_uid=f"pages_docx_pre_save_{_model.__name__}",
    )
    post_save.connect(
        delete_stale_docx_after_save,
        sender=_model,
        dispatch_uid=f"pages_docx_post_save_{_model.__name__}",
    )
    post_delete.connect(
        delete_files_on_page_delete,
        sender=_model,
        dispatch_uid=f"pages_files_post_delete_{_model.__name__}",
    )
