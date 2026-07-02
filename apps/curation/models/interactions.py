from __future__ import annotations

from curation.models.base import TimeStampedModel, UUIDMixin
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Bookmark(UUIDMixin, TimeStampedModel):
    """
    User bookmarks for any content type.
    Future-proof with GenericForeignKey for Resources, LearningPaths, Events.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks"
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    notes = models.TextField(blank=True, help_text="Personal notes about this bookmark")
    is_private = models.BooleanField(
        default=True, help_text="Whether this bookmark is private to the user"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_type", "object_id"], name="unique_user_bookmark"
            )
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["user", "created"]),
        ]
        ordering = ("-created",)

    def __str__(self):
        return f"{self.user.username} bookmarked {self.content_object}"


class Like(UUIDMixin, TimeStampedModel):
    """
    User likes/favorites for any content type.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes"
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_type", "object_id"], name="unique_user_like"
            )
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["user", "created"]),
        ]
        ordering = ("-created",)

    def __str__(self):
        return f"{self.user.username} liked {self.content_object}"


class ViewEvent(TimeStampedModel):
    """
    Analytics tracking for content views.
    No UUID needed for analytics data.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,  # Allow anonymous views
        related_name="view_events",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    # Always populated — enables view count queries across PG and Fuseki resources.
    resource_uuid = models.UUIDField(null=True, blank=True, db_index=True)

    session_id = models.CharField(
        max_length=40, blank=True, help_text="Session ID for anonymous users"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Additional analytics data
    referrer = models.URLField(blank=True)
    duration_seconds = models.IntegerField(
        null=True, blank=True, help_text="Time spent viewing content"
    )

    class Meta:
        ordering = ("-created",)
        indexes = [
            models.Index(fields=["content_type", "object_id", "created"]),
            models.Index(fields=["user", "created"]),
            models.Index(fields=["content_type", "object_id", "user", "created"]),
            models.Index(fields=["session_id", "created"]),
            models.Index(fields=["resource_uuid"]),
        ]

    def __str__(self):
        viewer = self.user.username if self.user else f"Anonymous ({self.session_id})"
        return f"{viewer} viewed {self.content_object}"


class EditLog(UUIDMixin, TimeStampedModel):
    """
    Audit trail for content changes.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="edit_logs"
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    action = models.CharField(
        max_length=20,
        choices=[
            ("create", "Create"),
            ("update", "Update"),
            ("delete", "Delete"),
            ("publish", "Publish"),
            ("unpublish", "Unpublish"),
        ],
    )
    changes = models.JSONField(default=dict, help_text="JSON representation of what changed")
    reason = models.TextField(blank=True, help_text="Reason for the change")

    class Meta:
        ordering = ("-created",)
        indexes = [
            models.Index(fields=["content_type", "object_id", "created"]),
            models.Index(fields=["user", "created"]),
            models.Index(fields=["action", "created"]),
        ]

    def __str__(self):
        return f"{self.user.username} {self.action} {self.content_object}"
