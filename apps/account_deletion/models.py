"""
Models for GDPR Article 17 (Right to Erasure) implementation.

This module defines the data models for handling account deletion requests
with full audit trails and admin review capabilities.
"""

import uuid as uuid_lib
from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class AccountDeletionRequest(models.Model):
    """
    Main model for account deletion requests (GDPR Article 17).

    Tracks the complete lifecycle of a deletion request from initiation
    through confirmation, grace period, and final execution.
    """

    # Primary identification
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid_lib.uuid4, unique=True, editable=False)

    # User being deleted
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='deletion_requests',
        help_text="User whose account will be deleted"
    )

    # Request metadata
    confirmation_token = models.UUIDField(
        unique=True,
        default=uuid_lib.uuid4,
        editable=False,
        help_text="Token used for email confirmation link"
    )

    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_deletions',
        help_text="User who initiated the request (self or admin)"
    )

    initiated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the deletion request was created"
    )

    # Request status
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed - Grace Period'),
        ('processing', 'Processing Deletion'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Current status of the deletion request"
    )

    # Confirmation tracking
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user confirmed the deletion via email link"
    )

    confirmation_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address from which confirmation was made"
    )

    confirmation_user_agent = models.TextField(
        blank=True,
        help_text="User agent string from confirmation request"
    )

    # Expiry dates
    token_expires_at = models.DateTimeField(
        db_index=True,
        help_text="Token expiry (7 days from initiated_at)"
    )

    deletion_scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When deletion will be executed (30 days from confirmed_at)"
    )

    # Completion tracking
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When deletion was actually completed"
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_deletions',
        help_text="Admin who executed the deletion"
    )

    # Cancellation tracking
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the request was cancelled"
    )

    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_deletions',
        help_text="Who cancelled the request (user or admin)"
    )

    cancellation_reason = models.TextField(
        blank=True,
        help_text="Reason for cancellation"
    )

    # Snapshot of user data at request time (GDPR audit requirement)
    user_snapshot = models.JSONField(
        default=dict,
        help_text="Complete snapshot of user accounts for GDPR audit trail"
    )

    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-initiated_at']
        verbose_name = "Account Deletion Request"
        verbose_name_plural = "Account Deletion Requests"
        indexes = [
            models.Index(fields=['status', 'token_expires_at']),
            models.Index(fields=['status', 'deletion_scheduled_at']),
        ]

    def __str__(self):
        return f"Deletion Request #{self.id} - {self.user.username} ({self.status})"

    def save(self, *args, **kwargs):
        # Auto-calculate token expiry (7 days)
        if not self.token_expires_at:
            self.token_expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def days_until_deletion(self):
        """Calculate days remaining until scheduled deletion."""
        if not self.deletion_scheduled_at:
            return None
        delta = self.deletion_scheduled_at - timezone.now()
        return max(0, delta.days)

    @property
    def token_is_expired(self):
        """Check if confirmation token has expired."""
        if not self.token_expires_at:
            return False
        return timezone.now() > self.token_expires_at

    @property
    def can_be_cancelled(self):
        """Check if request can still be cancelled."""
        return self.status in ['pending', 'confirmed']

    @property
    def is_in_grace_period(self):
        """Check if request is in 30-day grace period."""
        if not self.deletion_scheduled_at:
            return False
        return self.status == 'confirmed' and timezone.now() < self.deletion_scheduled_at


class AccountDeletionItem(models.Model):
    """
    Individual content items associated with a deletion request.

    Allows admins to review each piece of user-created content and decide
    whether to delete, anonymize, or keep it for business necessity.
    """

    # Primary identification
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid_lib.uuid4, unique=True, editable=False)

    # Link to parent deletion request
    deletion_request = models.ForeignKey(
        AccountDeletionRequest,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Parent deletion request"
    )

    # Content identification via GenericForeignKey
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Type of content (model)"
    )

    object_id = models.PositiveIntegerField(
        help_text="ID of the content object"
    )

    content_object = GenericForeignKey('content_type', 'object_id')

    # Content metadata for display
    model_name = models.CharField(
        max_length=100,
        help_text="Name of the model (e.g., ResourceContent)"
    )

    app_label = models.CharField(
        max_length=100,
        default='',
        help_text="Django app label"
    )

    content_summary = models.TextField(
        help_text="Brief description of content for admin review"
    )

    content_data = models.JSONField(
        default=dict,
        help_text="Full snapshot of content for audit trail"
    )

    # Admin decision
    ACTION_CHOICES = [
        ('pending', 'Pending Review'),
        ('delete', 'Hard Delete'),
        ('anonymize', 'Anonymize'),
        ('keep', 'Keep (Business Necessity)'),
    ]

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        default='pending',
        db_index=True,
        help_text="Admin decision on how to handle this content"
    )

    admin_notes = models.TextField(
        blank=True,
        help_text="Admin notes explaining the decision"
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_deletion_items',
        help_text="Admin who reviewed this item"
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this item was reviewed"
    )

    # Execution tracking
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this item was actually processed"
    )

    processing_error = models.TextField(
        blank=True,
        help_text="Error message if processing failed"
    )

    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['app_label', 'model_name', 'id']
        verbose_name = "Deletion Item"
        verbose_name_plural = "Deletion Items"
        indexes = [
            models.Index(fields=['deletion_request', 'action']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.app_label}.{self.model_name} #{self.object_id} - {self.action}"


class AccountDeletionLog(models.Model):
    """
    Immutable audit log for all deletion-related actions.

    Required for GDPR compliance to prove proper handling of data deletion requests.
    These records should never be deleted (retention: 7 years).
    """

    # Primary identification
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid_lib.uuid4, unique=True, editable=False)

    # Link to deletion request
    deletion_request = models.ForeignKey(
        AccountDeletionRequest,
        on_delete=models.CASCADE,
        related_name='logs',
        help_text="Related deletion request"
    )

    # Log entry details
    action = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Action performed (e.g., 'request_created', 'confirmed', 'cancelled')"
    )

    details = models.JSONField(
        default=dict,
        help_text="Detailed information about the action"
    )

    # Actor information
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who performed the action"
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the actor"
    )

    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )

    # Timestamp (immutable)
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When this action occurred"
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Deletion Audit Log"
        verbose_name_plural = "Deletion Audit Logs"
        indexes = [
            models.Index(fields=['deletion_request', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        return f"[{self.timestamp}] {self.action} by {self.performed_by or 'System'}"

    def save(self, *args, **kwargs):
        # Prevent modification of existing log entries
        if self.pk:
            raise ValueError("Audit log entries cannot be modified")
        super().save(*args, **kwargs)
