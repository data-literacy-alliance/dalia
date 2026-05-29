"""User models for DALIA 2.0."""

from core.models import TimeStampedModel
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser, TimeStampedModel):
    """
    Custom User model for DALIA.
    Extends Django's AbstractUser with unique email constraint.
    Inherits created_at/updated_at from core.TimeStampedModel.
    """

    email = models.EmailField(
        _("email address"),
        unique=True,
        help_text=_("Required. A valid email address."),
    )

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip() or self.username

    def get_short_name(self):
        return self.first_name or self.username


class UserDetails(User):
    """Proxy model for User providing a read-only activity dashboard in admin."""

    class Meta:
        proxy = True
        verbose_name = "User Details"
        verbose_name_plural = "User Details"
