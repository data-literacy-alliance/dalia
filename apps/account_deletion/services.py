"""
Service layer for account deletion operations.

This module contains all business logic for handling account deletion requests,
content discovery, and GDPR-compliant data erasure.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .models import AccountDeletionItem, AccountDeletionLog, AccountDeletionRequest

logger = logging.getLogger(__name__)
User = get_user_model()


class AccountDeletionService:
    """
    Main service for handling account deletion operations.
    """

    # Models with ForeignKey to User that contain personal data.
    # Dropped: djangocms_stories, filer, djangocms_versioning (not in dalia20).
    # entity_mapping entries are kept but handled gracefully via ContentType.DoesNotExist.
    PERSONAL_DATA_MODELS = [
        # Core user data
        ("curation", "Person"),
        ("socialaccount", "SocialAccount"),
        ("account", "EmailAddress"),
        ("authtoken", "Token"),
        # User-created content
        ("curation", "Resource"),
        ("curation", "ResourceContent"),
        ("curation", "Review"),
        # User interactions
        ("curation", "Bookmark"),
        ("curation", "Like"),
        ("curation", "ViewEvent"),
        ("curation", "CommunityMembership"),
        # User consents
        ("curation", "ResourceConsent"),
        ("curation", "ResourcePublishingConsent"),
        # Logs and tracking
        ("curation", "EditLog"),
        ("admin", "LogEntry"),
        # Entity mapping (may not exist yet; handled gracefully)
        ("entity_mapping", "EntityMapping"),
        ("entity_mapping", "SyncLog"),
    ]

    @classmethod
    @transaction.atomic
    def create_deletion_request(
        cls, user, initiated_by=None, ip_address: str | None = None, user_agent: str | None = None
    ) -> AccountDeletionRequest:
        """
        Create a new account deletion request and discover all related content.

        Args:
            user: User whose account will be deleted
            initiated_by: User who initiated the request (None = self-initiated)
            ip_address: IP address of the initiator
            user_agent: User agent string

        Returns:
            AccountDeletionRequest: Created deletion request with all items
        """
        # Check if there's already a pending or confirmed request
        existing = AccountDeletionRequest.objects.filter(
            user=user, status__in=["pending", "confirmed"]
        ).first()

        if existing:
            raise ValueError(
                f"User {user.username} already has an active deletion request (#{existing.id})"
            )

        # Create user snapshot for audit trail
        user_snapshot = cls._create_user_snapshot(user)

        # Create the deletion request
        deletion_request = AccountDeletionRequest.objects.create(
            user=user,
            initiated_by=initiated_by or user,
            user_snapshot=user_snapshot,
            status="pending",
        )

        # Create audit log entry
        AccountDeletionLog.objects.create(
            deletion_request=deletion_request,
            action="request_created",
            details={
                "user_id": user.id,
                "username": user.username,
                "self_initiated": initiated_by is None or initiated_by == user,
            },
            performed_by=initiated_by or user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Discover and catalog all user content
        cls._discover_user_content(deletion_request)

        logger.info(
            f"Created deletion request #{deletion_request.id} for user {user.username} "
            f"(initiated by {initiated_by.username if initiated_by else 'self'})"
        )

        return deletion_request

    @classmethod
    def _create_user_snapshot(cls, user) -> dict:
        """
        Create a complete snapshot of user data for GDPR audit trail.

        Args:
            user: User to snapshot

        Returns:
            Dict: Complete user data snapshot
        """
        from allauth.socialaccount.models import SocialAccount

        snapshot = {
            "django_user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "is_active": user.is_active,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "groups": list(user.groups.values_list("name", flat=True)),
            }
        }

        # Add Person profile if exists
        try:
            person = user.person
            snapshot["person"] = {
                "id": person.id,
                "uuid": str(person.uuid),
                "first_name": person.first_name,
                "last_name": person.last_name,
                "orcid": person.orcid,
                "homepage": person.homepage,
                "uri": person.uri,
                "privacy_level": person.privacy_level,
            }
        except Exception:
            snapshot["person"] = None

        # Add social accounts
        social_accounts = SocialAccount.objects.filter(user=user)
        snapshot["social_accounts"] = [
            {
                "provider": sa.provider,
                "uid": sa.uid,
                "date_joined": sa.date_joined.isoformat(),
                "extra_data_keys": list(sa.extra_data.keys()) if sa.extra_data else [],
            }
            for sa in social_accounts
        ]

        snapshot["snapshot_created_at"] = timezone.now().isoformat()

        return snapshot

    @classmethod
    def _discover_user_content(cls, deletion_request: AccountDeletionRequest) -> None:
        """
        Discover all content associated with the user and create AccountDeletionItem records.

        Args:
            deletion_request: Deletion request to attach items to
        """
        user = deletion_request.user
        discovered_count = 0

        for app_label, model_name in cls.PERSONAL_DATA_MODELS:
            try:
                with transaction.atomic():
                    content_type = ContentType.objects.get(
                        app_label=app_label, model=model_name.lower()
                    )
                    model_class = content_type.model_class()

                    if not model_class:
                        logger.warning(f"Could not load model: {app_label}.{model_name}")
                        continue

                    # Try common field names for user relationships
                    user_fields = [
                        "user",
                        "owner",
                        "created_by",
                        "submitted_by",
                        "reviewer",
                        "user_ptr",
                    ]

                    for field_name in user_fields:
                        if hasattr(model_class, field_name):
                            objects = model_class.objects.filter(**{field_name: user})

                            for obj in objects:
                                cls._create_deletion_item(
                                    deletion_request=deletion_request,
                                    content_object=obj,
                                    app_label=app_label,
                                    model_name=model_name,
                                )
                                discovered_count += 1
                            break

            except ContentType.DoesNotExist:
                # Expected for disabled apps like entity_mapping
                logger.warning(f"ContentType not found: {app_label}.{model_name}")
                continue
            except Exception as e:
                logger.error(f"Error discovering content for {app_label}.{model_name}: {e}")
                continue

        # Log discovery completion
        AccountDeletionLog.objects.create(
            deletion_request=deletion_request,
            action="content_discovered",
            details={
                "items_count": discovered_count,
                "models_scanned": len(cls.PERSONAL_DATA_MODELS),
            },
            performed_by=deletion_request.initiated_by,
        )

        logger.info(
            f"Discovered {discovered_count} content items for deletion request #{deletion_request.id}"
        )

    @classmethod
    def _create_deletion_item(
        cls,
        deletion_request: AccountDeletionRequest,
        content_object,
        app_label: str,
        model_name: str,
    ) -> AccountDeletionItem:
        """
        Create a single deletion item from a content object.
        """
        content_type = ContentType.objects.get_for_model(content_object)
        summary = cls._generate_content_summary(content_object, model_name)
        content_data = cls._create_content_snapshot(content_object)

        return AccountDeletionItem.objects.create(
            deletion_request=deletion_request,
            content_type=content_type,
            object_id=content_object.pk,
            model_name=model_name,
            app_label=app_label,
            content_summary=summary,
            content_data=content_data,
            action="pending",
        )

    @classmethod
    def _generate_content_summary(cls, obj, model_name: str) -> str:
        """Generate human-readable summary of content for admin review."""
        if hasattr(obj, "title"):
            return f"{model_name}: {obj.title[:100]}"
        elif hasattr(obj, "name"):
            return f"{model_name}: {obj.name[:100]}"
        elif hasattr(obj, "__str__"):
            return f"{model_name}: {str(obj)[:100]}"
        else:
            return f"{model_name} #{obj.pk}"

    @classmethod
    def _create_content_snapshot(cls, obj) -> dict:
        """Create a snapshot of content object for audit trail."""
        snapshot = {
            "model": obj.__class__.__name__,
            "pk": obj.pk,
        }

        for field in obj._meta.get_fields():
            if field.concrete and not field.many_to_many and not field.one_to_many:
                try:
                    value = getattr(obj, field.name)
                    if hasattr(value, "isoformat"):
                        snapshot[field.name] = value.isoformat()
                    elif hasattr(value, "__str__") and not callable(value):
                        snapshot[field.name] = str(value)
                    else:
                        snapshot[field.name] = value
                except Exception:
                    snapshot[field.name] = "<error retrieving value>"

        snapshot["snapshot_created_at"] = timezone.now().isoformat()
        return snapshot

    @classmethod
    def send_confirmation_email(cls, deletion_request: AccountDeletionRequest) -> bool:
        """
        Send confirmation email with deletion link to user.
        """
        if deletion_request.status != "pending":
            raise ValueError(
                f"Cannot send confirmation email for request in status: {deletion_request.status}"
            )

        user = deletion_request.user
        confirmation_url = cls._build_confirmation_url(deletion_request.confirmation_token)

        context = {
            "user": user,
            "deletion_request": deletion_request,
            "confirmation_url": confirmation_url,
            "token_expires_at": deletion_request.token_expires_at,
            "days_valid": 7,
        }

        html_message = render_to_string("emails/deletion_confirmation.html", context)
        plain_message = strip_tags(html_message)

        try:
            send_mail(
                subject="Confirm Your Account Deletion Request",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            AccountDeletionLog.objects.create(
                deletion_request=deletion_request,
                action="confirmation_email_sent",
                details={"recipient": user.email},
                performed_by=None,
            )

            logger.info(f"Sent confirmation email for deletion request #{deletion_request.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send confirmation email: {e}")
            AccountDeletionLog.objects.create(
                deletion_request=deletion_request,
                action="confirmation_email_failed",
                details={"error": str(e)},
                performed_by=None,
            )
            return False

    @classmethod
    @transaction.atomic
    def confirm_deletion(
        cls, confirmation_token: str, ip_address: str | None = None, user_agent: str | None = None
    ) -> AccountDeletionRequest:
        """
        Confirm a deletion request using the confirmation token.
        """
        try:
            deletion_request = AccountDeletionRequest.objects.get(
                confirmation_token=confirmation_token, status="pending"
            )
        except AccountDeletionRequest.DoesNotExist:
            raise ValueError("Invalid or already used confirmation token") from None

        if deletion_request.token_is_expired:
            deletion_request.status = "expired"
            deletion_request.save()
            raise ValueError("Confirmation token has expired")

        deletion_request.status = "confirmed"
        deletion_request.confirmed_at = timezone.now()
        deletion_request.confirmation_ip = ip_address
        deletion_request.confirmation_user_agent = user_agent
        deletion_request.deletion_scheduled_at = timezone.now() + timedelta(days=30)
        deletion_request.save()

        AccountDeletionLog.objects.create(
            deletion_request=deletion_request,
            action="deletion_confirmed",
            details={
                "scheduled_for": deletion_request.deletion_scheduled_at.isoformat(),
                "grace_period_days": 30,
            },
            performed_by=deletion_request.user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        cls._send_confirmed_email(deletion_request)

        logger.info(
            f"Deletion request #{deletion_request.id} confirmed, "
            f"scheduled for {deletion_request.deletion_scheduled_at}"
        )

        return deletion_request

    @classmethod
    @transaction.atomic
    def cancel_deletion(
        cls,
        deletion_request: AccountDeletionRequest,
        cancelled_by,
        reason: str = "",
        ip_address: str | None = None,
    ) -> AccountDeletionRequest:
        """
        Cancel a deletion request.
        """
        if not deletion_request.can_be_cancelled:
            raise ValueError(f"Cannot cancel deletion request in status: {deletion_request.status}")

        deletion_request.status = "cancelled"
        deletion_request.cancelled_at = timezone.now()
        deletion_request.cancelled_by = cancelled_by
        deletion_request.cancellation_reason = reason
        deletion_request.save()

        AccountDeletionLog.objects.create(
            deletion_request=deletion_request,
            action="deletion_cancelled",
            details={
                "reason": reason,
                "cancelled_by_username": cancelled_by.username,
            },
            performed_by=cancelled_by,
            ip_address=ip_address,
        )

        logger.info(f"Deletion request #{deletion_request.id} cancelled by {cancelled_by.username}")

        return deletion_request

    @classmethod
    @transaction.atomic
    def process_deletion(cls, deletion_request: AccountDeletionRequest, admin_user) -> None:
        """
        Execute the actual deletion based on admin-reviewed items.
        """
        if deletion_request.status not in ["confirmed", "processing"]:
            raise ValueError(
                f"Cannot process deletion request in status: {deletion_request.status}"
            )

        pending_items = deletion_request.items.filter(action="pending").count()
        if pending_items > 0:
            raise ValueError(f"Cannot process deletion: {pending_items} items still pending review")

        deletion_request.status = "processing"
        deletion_request.save()

        errors = []
        for item in deletion_request.items.all():
            try:
                cls._process_deletion_item(item)
            except Exception as e:
                error_msg = f"Error processing {item.model_name} #{item.object_id}: {e}"
                errors.append(error_msg)
                item.processing_error = str(e)
                item.save()
                logger.error(error_msg)

        user = deletion_request.user
        username = user.username
        user_id = user.id

        try:
            user.delete()
        except Exception as e:
            errors.append(f"Error deleting user account: {e}")
            logger.error(f"Failed to delete user {username}: {e}")

        deletion_request.status = "completed"
        deletion_request.completed_at = timezone.now()
        deletion_request.completed_by = admin_user
        deletion_request.save()

        AccountDeletionLog.objects.create(
            deletion_request=deletion_request,
            action="deletion_completed",
            details={
                "user_id": user_id,
                "username": username,
                "items_processed": deletion_request.items.count(),
                "errors_count": len(errors),
                "errors": errors if errors else [],
            },
            performed_by=admin_user,
        )

        logger.info(f"Completed deletion of user {username} (request #{deletion_request.id})")

    @classmethod
    def _process_deletion_item(cls, item: AccountDeletionItem) -> None:
        """Process a single deletion item according to admin decision."""
        if item.action == "delete":
            if item.content_object:
                item.content_object.delete()
        elif item.action == "anonymize":
            cls._anonymize_content(item)
        elif item.action == "keep":
            pass

        item.processed_at = timezone.now()
        item.save()

    @classmethod
    def _anonymize_content(cls, item: AccountDeletionItem) -> None:
        """Anonymize content by replacing personal data with generic values."""
        obj = item.content_object
        if not obj:
            return

        user_fields = ["user", "owner", "created_by", "submitted_by", "reviewer"]
        for field_name in user_fields:
            if hasattr(obj, field_name):
                setattr(obj, field_name, None)

        if hasattr(obj, "first_name"):
            obj.first_name = "Deleted"
        if hasattr(obj, "last_name"):
            obj.last_name = "User"
        if hasattr(obj, "email"):
            obj.email = f"deleted_{item.object_id}@example.com"

        obj.save()

    @classmethod
    def _build_confirmation_url(cls, token) -> str:
        """Build the full confirmation URL."""
        base_url = getattr(settings, "SITE_URL", "http://localhost:8000")
        return f"{base_url}/api/account/delete-confirm/{token}/"

    @classmethod
    def _send_confirmed_email(cls, deletion_request: AccountDeletionRequest) -> None:
        """Send email after deletion is confirmed."""
        user = deletion_request.user
        cancellation_url = (
            f"{settings.SITE_URL}/api/account/delete-cancel/{deletion_request.confirmation_token}/"
        )

        context = {
            "user": user,
            "deletion_request": deletion_request,
            "deletion_scheduled_at": deletion_request.deletion_scheduled_at,
            "cancellation_url": cancellation_url,
            "grace_period_days": 30,
        }

        html_message = render_to_string("emails/deletion_confirmed.html", context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject="Account Deletion Confirmed - 30 Day Grace Period",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,
        )

    @classmethod
    def expire_old_tokens(cls) -> int:
        """
        Mark pending requests with expired tokens as 'expired'.
        Called by management command.
        """
        expired_requests = AccountDeletionRequest.objects.filter(
            status="pending", token_expires_at__lt=timezone.now()
        )

        count = expired_requests.count()
        expired_requests.update(status="expired")

        for req in expired_requests:
            AccountDeletionLog.objects.create(
                deletion_request=req,
                action="token_expired",
                details={"expired_at": timezone.now().isoformat()},
                performed_by=None,
            )

        logger.info(f"Expired {count} deletion request tokens")
        return count

    @classmethod
    def process_scheduled_deletions(cls, admin_user=None) -> int:
        """
        Process all confirmed deletions that have passed their grace period.
        Called by management command.
        """
        ready_requests = AccountDeletionRequest.objects.filter(
            status="confirmed", deletion_scheduled_at__lt=timezone.now()
        )

        count = 0
        for req in ready_requests:
            try:
                cls.process_deletion(req, admin_user or req.user)
                count += 1
            except Exception as e:
                logger.error(f"Failed to process scheduled deletion #{req.id}: {e}")

        logger.info(f"Processed {count} scheduled deletions")
        return count
