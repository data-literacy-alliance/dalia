from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import (
    Bookmark,
    CommunityMembership,
    Like,
    Resource,
    ResourceConsent,
    ResourceContent,
    ResourcePublishingConsent,
    Review,
)
from .notifications import notify_curators_submission  # webhook placeholder

User = get_user_model()


@transaction.atomic
def submit_for_review(content: ResourceContent, user: User) -> None:
    """
    Flag a draft for curator review and trigger the notification placeholder.
    """
    if hasattr(content, "submitted_for_review"):
        content.submitted_for_review = True
        content.save(update_fields=["submitted_for_review"])
    elif hasattr(content.resource, "submitted_for_review"):
        content.resource.submitted_for_review = True
        content.resource.save(update_fields=["submitted_for_review"])
    else:
        pass

    notify_curators_submission(resource=content.resource, submitted_by=user, content=content)


def soft_delete(resource: Resource, user: User) -> None:
    """
    Soft delete a grouper (Curators only).
    """
    if hasattr(resource, "is_removed"):
        if not resource.is_removed:
            resource.is_removed = True
            resource.save(update_fields=["is_removed"])


@transaction.atomic
def approve_membership(membership: CommunityMembership, approved_by: User) -> None:
    """
    Approve a pending community membership.
    """
    membership.status = 'approved'
    membership.approved_at = timezone.now()
    membership.approved_by = approved_by
    membership.save(update_fields=['status', 'approved_at', 'approved_by'])


@transaction.atomic
def promote_member(membership: CommunityMembership, new_role: str, promoted_by: User) -> None:
    """
    Promote a member to a higher role.
    """
    membership.role = new_role
    membership.save(update_fields=['role'])


@transaction.atomic
def toggle_bookmark(user: User, content_object: object) -> tuple:
    """
    Toggle bookmark for a content object.
    Returns (is_bookmarked, was_created)
    """
    content_type = ContentType.objects.get_for_model(content_object)
    bookmark, created = Bookmark.objects.get_or_create(
        user=user,
        content_type=content_type,
        object_id=content_object.pk
    )

    if not created:
        bookmark.delete()
        return False, False

    return True, True


@transaction.atomic
def toggle_like(user: User, content_object: object) -> tuple:
    """
    Toggle like for a content object.
    Returns (is_liked, was_created)
    """
    content_type = ContentType.objects.get_for_model(content_object)
    like, created = Like.objects.get_or_create(
        user=user,
        content_type=content_type,
        object_id=content_object.pk
    )

    if not created:
        like.delete()
        return False, False

    return True, True


@transaction.atomic
def submit_review(review: Review) -> None:
    """
    Submit a review for moderation.
    """
    review.status = 'submitted'
    review.submitted_at = timezone.now()
    review.save(update_fields=['status', 'submitted_at'])


@transaction.atomic
def approve_review(review: Review, approved_by: User) -> None:
    """
    Approve a submitted review.
    """
    review.status = 'approved'
    review.completed_at = timezone.now()
    review.save(update_fields=['status', 'completed_at'])


@transaction.atomic
def reject_review(review: Review, rejected_by: User, reason: str = "") -> None:
    """
    Reject a submitted review.
    """
    review.status = 'rejected'
    review.completed_at = timezone.now()
    review.save(update_fields=['status', 'completed_at'])


@transaction.atomic
def grant_resource_consent(
    consent: ResourceConsent,
    consent_text: str,
    version: str,
    ip_address: str | None = None,
    user_agent: str | None = None
) -> None:
    """
    Grant resource consent with audit trail.
    """
    consent.status = 'granted'
    consent.consent_text = consent_text
    consent.consent_version = version
    consent.granted_at = timezone.now()
    consent.ip_address = ip_address or ''
    consent.user_agent = user_agent or ''
    consent.save(update_fields=[
        'status', 'consent_text', 'consent_version',
        'granted_at', 'ip_address', 'user_agent'
    ])


@transaction.atomic
def withdraw_resource_consent(consent: ResourceConsent, reason: str = "") -> None:
    """
    Withdraw resource consent with reason.
    """
    consent.status = 'withdrawn'
    consent.withdrawn_at = timezone.now()
    consent.withdrawal_reason = reason
    consent.save(update_fields=['status', 'withdrawn_at', 'withdrawal_reason'])


@transaction.atomic
def withdraw_all_publishing_consents(consent: ResourcePublishingConsent, reason: str = "") -> None:
    """
    Withdraw all publishing consents for a resource.
    """
    consent.is_active = False
    consent.cc0_agreed = False
    consent.data_processing_agreed = False
    consent.public_display_agreed = False
    consent.analytics_agreed = False
    consent.withdrawn_at = timezone.now()
    consent.withdrawal_reason = reason
    consent.save(update_fields=[
        'is_active', 'cc0_agreed', 'data_processing_agreed',
        'public_display_agreed', 'analytics_agreed',
        'withdrawn_at', 'withdrawal_reason'
    ])


def log_view_event(user: User, content_object: object, ip_address: str = "", user_agent: str = "") -> None:
    """
    Log a view event for analytics (non-transactional).
    """
    from .models import ViewEvent

    content_type = ContentType.objects.get_for_model(content_object)
    ViewEvent.objects.create(
        user=user,
        content_type=content_type,
        object_id=content_object.pk,
        ip_address=ip_address,
        user_agent=user_agent
    )


def log_edit_event(
    user: User,
    content_object: object,
    action: str,
    changes: dict = None,
    ip_address: str = "",
    user_agent: str = ""
) -> None:
    """
    Log an edit event for audit trail (non-transactional).
    """
    from .models import EditLog

    content_type = ContentType.objects.get_for_model(content_object)
    EditLog.objects.create(
        user=user,
        content_type=content_type,
        object_id=content_object.pk,
        action=action,
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent
    )
