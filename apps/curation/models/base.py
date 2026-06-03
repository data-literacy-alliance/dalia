from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class UUIDMixin(models.Model):
    """
    Adds a unique, non-editable UUID to a model.
    Not a primary key - external-stable identifier.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    class Meta:
        abstract = True

    @classmethod
    def get_by_uuid(cls, uuid_value):
        """Get instance by UUID with proper error handling."""
        try:
            return cls.objects.get(uuid=uuid_value)
        except cls.DoesNotExist:
            return None

    @classmethod
    def filter_by_uuid(cls, uuid_values):
        """Filter queryset by list of UUIDs."""
        return cls.objects.filter(uuid__in=uuid_values)


class TimeStampedModel(models.Model):
    """Adds created and modified timestamp fields."""

    created = models.DateTimeField(default=timezone.now, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Activatable(models.Model):
    """Adds is_active field for soft delete pattern."""

    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class NamedVocabulary(UUIDMixin, Activatable, TimeStampedModel):
    """
    Base class for controlled vocabulary models.
    Provides label, slug, URI fields with auto-slugification.
    """

    label = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    uri = models.URLField(blank=True)

    class Meta:
        abstract = True
        ordering = ("label",)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.label)[:255]
        super().save(*args, **kwargs)

    def __str__(self):  # noqa: DJ012
        return self.label


class OrderedModel(models.Model):
    """Adds ordering functionality for child models."""

    order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ("order", "pk")
