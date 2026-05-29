"""
Serializers for account deletion API endpoints.
"""

from rest_framework import serializers

from .models import AccountDeletionItem, AccountDeletionLog, AccountDeletionRequest


class AccountDeletionRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for account deletion requests.
    """
    # Read-only computed fields
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    days_until_deletion = serializers.IntegerField(read_only=True)
    token_is_expired = serializers.BooleanField(read_only=True)
    can_be_cancelled = serializers.BooleanField(read_only=True)
    is_in_grace_period = serializers.BooleanField(read_only=True)

    # URL for confirmation
    confirmation_url = serializers.SerializerMethodField()
    cancellation_url = serializers.SerializerMethodField()

    class Meta:
        model = AccountDeletionRequest
        fields = [
            'id',
            'uuid',
            'user',
            'username',
            'user_email',
            'confirmation_token',
            'initiated_by',
            'initiated_at',
            'status',
            'confirmed_at',
            'token_expires_at',
            'deletion_scheduled_at',
            'completed_at',
            'cancelled_at',
            'cancellation_reason',
            'user_snapshot',
            'days_until_deletion',
            'token_is_expired',
            'can_be_cancelled',
            'is_in_grace_period',
            'confirmation_url',
            'cancellation_url',
            'created',
            'modified',
        ]
        read_only_fields = [
            'id',
            'uuid',
            'confirmation_token',
            'initiated_at',
            'confirmed_at',
            'token_expires_at',
            'deletion_scheduled_at',
            'completed_at',
            'cancelled_at',
            'user_snapshot',
            'created',
            'modified',
        ]

    def get_confirmation_url(self, obj):
        """Build full confirmation URL."""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(
                f'/api/account/delete-confirm/{obj.confirmation_token}/'
            )
        return None

    def get_cancellation_url(self, obj):
        """Build full cancellation URL."""
        if not obj.can_be_cancelled:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(
                f'/api/account/delete-cancel/{obj.confirmation_token}/'
            )
        return None


class AccountDeletionRequestCreateSerializer(serializers.Serializer):
    """
    Serializer for creating deletion requests.
    """
    user_id = serializers.IntegerField(
        required=False,
        help_text="User ID to create deletion request for (admin only). If omitted, creates for self."
    )


class AccountDeletionConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirmation response.
    """
    status = serializers.CharField()
    message = serializers.CharField()
    deletion_scheduled_at = serializers.DateTimeField()
    cancellation_url = serializers.CharField()
    days_remaining = serializers.IntegerField()


class AccountDeletionCancelSerializer(serializers.Serializer):
    """
    Serializer for cancellation response.
    """
    status = serializers.CharField()
    message = serializers.CharField()
    cancelled_at = serializers.DateTimeField()


class AccountDeletionStatusSerializer(serializers.Serializer):
    """
    Serializer for status check response.
    """
    status = serializers.CharField()
    days_remaining = serializers.IntegerField(allow_null=True)
    deletion_scheduled_at = serializers.DateTimeField(allow_null=True)
    can_cancel = serializers.BooleanField()
    initiated_at = serializers.DateTimeField()
    confirmed_at = serializers.DateTimeField(allow_null=True)


class AccountDeletionItemSerializer(serializers.ModelSerializer):
    """
    Serializer for deletion items (admin review).
    """
    model_display = serializers.SerializerMethodField()

    class Meta:
        model = AccountDeletionItem
        fields = [
            'id',
            'uuid',
            'deletion_request',
            'model_name',
            'app_label',
            'model_display',
            'content_summary',
            'action',
            'admin_notes',
            'reviewed_by',
            'reviewed_at',
            'processed_at',
            'processing_error',
            'created',
            'modified',
        ]
        read_only_fields = [
            'id',
            'uuid',
            'model_name',
            'app_label',
            'content_summary',
            'processed_at',
            'processing_error',
            'created',
            'modified',
        ]

    def get_model_display(self, obj):
        """Return app_label.model_name format."""
        return f"{obj.app_label}.{obj.model_name}"


class AccountDeletionLogSerializer(serializers.ModelSerializer):
    """
    Serializer for audit logs (read-only).
    """
    performed_by_username = serializers.CharField(
        source='performed_by.username',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = AccountDeletionLog
        fields = [
            'id',
            'uuid',
            'deletion_request',
            'action',
            'details',
            'performed_by',
            'performed_by_username',
            'ip_address',
            'user_agent',
            'timestamp',
        ]
        read_only_fields = [
            'id',
            'uuid',
            'deletion_request',
            'action',
            'details',
            'performed_by',
            'performed_by_username',
            'ip_address',
            'user_agent',
            'timestamp',
        ]
