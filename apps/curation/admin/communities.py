"""
Admin classes for community-related models.
"""

from core.admin import BaseModelAdmin
from curation.models import Community, CommunityMembership, CommunitySocialMedia
from django.contrib import admin
from unfold.admin import TabularInline


class CommunitySocialMediaInline(TabularInline):
    model = CommunitySocialMedia
    extra = 1
    fields = ("name", "url")


@admin.register(Community)
class CommunityAdmin(BaseModelAdmin):
    list_display = ("title", "slug", "uri", "is_active", "uuid")
    list_filter = ("is_active",)
    search_fields = ("title", "slug", "description", "uuid")
    readonly_fields = ("uuid",)
    inlines = [CommunitySocialMediaInline]

    fieldsets = (
        (
            None,
            {"fields": ("title", "slug", "is_active", "uuid", "uri")},
        ),
        (
            "Content",
            {"fields": ("description", "website_url", "image")},
        ),
        (
            "Governance",
            {
                "fields": ("moderation_policy", "auto_publish_threshold", "requires_approval"),
            },
        ),
    )


@admin.register(CommunityMembership)
class CommunityMembershipAdmin(BaseModelAdmin):
    list_display = ("user", "community", "role", "is_approved", "joined_at", "uuid")
    list_filter = ("role", "is_approved", "community", "joined_at")
    search_fields = ("user__username", "user__email", "community__title", "uuid")
    readonly_fields = ("uuid", "joined_at", "approved_at")

    fieldsets = (
        (
            None,
            {
                "fields": ("user", "community", "role", "uuid"),
            },
        ),
        (
            "Approval",
            {
                "fields": ("is_approved", "approved_by", "approved_at"),
            },
        ),
        (
            "Permissions",
            {
                "fields": ("permissions_granted", "sync_with_group"),
            },
        ),
    )

    @admin.action(description="Approve selected memberships")
    def approve_memberships(self, request, queryset):
        for membership in queryset.filter(is_approved=False):
            membership.approve_membership(request.user)
        self.message_user(request, f"Approved {queryset.count()} memberships.")

    @admin.action(description="Promote to moderator")
    def promote_to_moderator(self, request, queryset):
        for membership in queryset:
            membership.promote_to("moderator", request.user)
        self.message_user(request, f"Promoted {queryset.count()} members to moderator.")

    actions = [approve_memberships, promote_to_moderator]
