from __future__ import annotations

from curation.models.base import Activatable, TimeStampedModel, UUIDMixin
from django.conf import settings
from django.db import models
from django.utils.text import slugify

# Feature-specific constants
MEMBERSHIP_ROLES = [
    ("member", "Member"),
    ("moderator", "Moderator"),
    ("admin", "Administrator"),
    ("owner", "Owner"),
]


class Community(UUIDMixin, TimeStampedModel, Activatable):
    """
    Enhanced Community model with governance settings.
    """

    title = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    uri = models.URLField(blank=True, null=True, unique=True)

    # Content fields — replicated from Fuseki for fallback use
    description = models.TextField(blank=True, help_text="Community description and purpose")
    website_url = models.URLField(blank=True, default="", help_text="Community website URL")
    image = models.URLField(blank=True, null=True, help_text="Community logo or banner image URL")

    # Governance and moderation settings
    moderation_policy = models.TextField(
        blank=True, help_text="Community moderation guidelines and policies"
    )
    auto_publish_threshold = models.IntegerField(
        default=2, help_text="Number of positive reviews needed for auto-publishing"
    )
    requires_approval = models.BooleanField(
        default=True, help_text="Whether new members require approval to join"
    )

    class Meta:
        ordering = ("title",)
        verbose_name_plural = "Communities"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:255]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_members(self):
        """Get all community members."""
        return self.memberships.select_related("user").filter(user__is_active=True)

    def get_admins(self):
        """Get community administrators and owners."""
        return self.memberships.filter(role__in=["admin", "owner"]).select_related("user")

    def get_moderators(self):
        """Get community moderators, admins, and owners."""
        return self.memberships.filter(role__in=["moderator", "admin", "owner"]).select_related(
            "user"
        )

    def user_can_moderate(self, user):
        """Check if user has moderation permissions."""
        if not user.is_authenticated:
            return False
        return self.memberships.filter(user=user, role__in=["moderator", "admin", "owner"]).exists()

    def user_can_admin(self, user):
        """Check if user has admin permissions."""
        if not user.is_authenticated:
            return False
        return self.memberships.filter(user=user, role__in=["admin", "owner"]).exists()


class CommunityMembership(UUIDMixin, TimeStampedModel):
    """
    Community membership with roles and permissions.
    Maps to FAIR-DS Organization Ontology (org:Membership).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_memberships"
    )
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_ROLES,
        default="member",
        help_text="Member role (maps to org:role in FAIR-DS ontology)",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(
        default=False, help_text="Whether membership has been approved"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_memberships",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Extended permissions for fine-grained control
    permissions_granted = models.JSONField(
        default=list, help_text="Additional specific permissions beyond role defaults"
    )

    # Integration with Django Groups for global roles
    sync_with_group = models.BooleanField(
        default=False, help_text="Sync role changes with Django user groups"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["community", "user"], name="unique_community_member")
        ]
        ordering = ("community", "role", "user__username")

    def __str__(self):
        return f"{self.user.username} - {self.community.title} ({self.get_role_display()})"

    def get_effective_permissions(self):
        """Get all permissions including role-based and explicitly granted."""
        role_permissions = self.get_role_permissions()
        return list(set(role_permissions + self.permissions_granted))

    def get_role_permissions(self):
        """Get default permissions for the current role."""
        role_perms = {
            "member": ["view_content", "create_content"],
            "moderator": [
                "view_content",
                "create_content",
                "moderate_content",
                "review_submissions",
            ],
            "admin": [
                "view_content",
                "create_content",
                "moderate_content",
                "review_submissions",
                "manage_members",
                "edit_community",
            ],
            "owner": [
                "view_content",
                "create_content",
                "moderate_content",
                "review_submissions",
                "manage_members",
                "edit_community",
                "delete_community",
            ],
        }
        return role_perms.get(self.role, [])

    def has_permission(self, permission):
        """Check if membership has a specific permission."""
        return permission in self.get_effective_permissions()

    def promote_to(self, new_role, promoted_by=None):
        """Promote member to a new role."""
        if new_role not in [choice[0] for choice in MEMBERSHIP_ROLES]:
            raise ValueError(f"Invalid role: {new_role}")

        old_role = self.role
        self.role = new_role
        if promoted_by:
            promotion_log = {
                "action": "promoted",
                "from_role": old_role,
                "to_role": new_role,
                "by": promoted_by.username,
            }
            if not isinstance(self.permissions_granted, list):
                self.permissions_granted = []
            self.permissions_granted.append(promotion_log)

        self.save()

    def approve_membership(self, approved_by):
        """Approve pending membership."""
        from django.utils import timezone

        self.is_approved = True
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.save()


class CommunitySocialMedia(TimeStampedModel):
    """Social media links for a community — editable in admin, replicated from Fuseki."""

    community = models.ForeignKey(
        Community, on_delete=models.CASCADE, related_name="social_media_links"
    )
    name = models.CharField(max_length=100, help_text="Platform name, e.g. Zenodo, YouTube")
    url = models.URLField(help_text="Full URL to the community's profile on this platform")

    class Meta:
        ordering = ("name",)
        verbose_name = "Social Media Link"
        verbose_name_plural = "Social Media Links"

    def __str__(self):
        return f"{self.community.title} — {self.name}"
