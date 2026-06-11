from __future__ import annotations

import re

from curation.models.base import Activatable, TimeStampedModel, UUIDMixin
from curation.models.constants import PRIVACY_CHOICES
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# Validators
def validate_orcid(value):
    """Validate ORCID iD format: 0000-0000-0000-0000"""
    if value and not re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", value):
        raise ValidationError("Invalid ORCID iD format. Expected: 0000-0000-0000-0000")


def validate_ror_id(value):
    """Validate ROR ID format"""
    if value and not (value.startswith("https://ror.org/") and len(value) > 17):
        raise ValidationError("Invalid ROR ID format. Expected: https://ror.org/xxxxxxxx")


class Person(UUIDMixin, TimeStampedModel, Activatable):
    """
    Enhanced Person model with OneToOne User relationship and preferences.
    """

    # Enhanced with OneToOne to auth.User for Django integration
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Link to Django user account",
    )
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    orcid = models.CharField(
        max_length=19,
        blank=True,
        validators=[validate_orcid],
        help_text="ORCID iD e.g. 0000-0002-1825-0097",
    )
    homepage = models.URLField(blank=True)
    uri = models.URLField(blank=True)

    # User preferences
    privacy_level = models.CharField(
        max_length=20,
        choices=PRIVACY_CHOICES,
        default="public",
        help_text="Account visibility level",
    )
    email_notifications = models.BooleanField(default=True, help_text="Receive email notifications")

    class Meta:
        ordering = ("first_name", "last_name")

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        """Return the full name combining first and last name."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_display_name(self):
        """Return user's full name or username as fallback."""
        if self.user and self.user.get_full_name():
            return self.user.get_full_name()
        return self.full_name


class Organization(UUIDMixin, TimeStampedModel, Activatable):
    """
    Enhanced Organization model with hierarchy and FAIR-DS compliance.
    """

    name = models.CharField(max_length=255)
    ror_id = models.CharField(
        max_length=64,
        blank=True,
        validators=[validate_ror_id],
        help_text="ROR ID (e.g. https://ror.org/04xfq0f34)",
    )
    # Hierarchical structure for sub-units (FAIR-DS org:hasUnit)
    parent_organization = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_units",
        help_text="Parent organization for hierarchical structure",
    )
    homepage = models.URLField(blank=True)
    uri = models.URLField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def get_units(self):
        """Get all sub-units of this organization (FAIR-DS org:hasUnit)."""
        return self.sub_units.all()

    def get_root_organization(self):
        """Get the root organization by traversing up the hierarchy."""
        current = self
        while current.parent_organization:
            current = current.parent_organization
        return current

    def get_hierarchy_path(self):
        """Get the full hierarchy path as a list from root to this organization."""
        path = []
        current = self
        while current:
            path.insert(0, current)
            current = current.parent_organization
        return path
