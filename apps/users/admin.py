"""Users admin configuration with Unfold theme."""

from core.admin import BaseModelAdmin
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import UserDetails

User = get_user_model()


@admin.register(User)
class UserAdmin(DjangoUserAdmin, BaseModelAdmin):
    """Custom User admin with Unfold theme."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ["email", "username", "first_name", "last_name", "is_staff"]
    list_filter = ["is_staff", "is_superuser", "is_active"]
    search_fields = [
        "email",
        "username",
        "first_name",
        "last_name",
        "person__first_name",
        "person__last_name",
    ]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )


@admin.register(UserDetails)
class UserDetailsAdmin(BaseModelAdmin):
    """
    Read-only admin dashboard showing comprehensive user activity statistics.
    Provides a paginated table with clickable columns linking to filtered admin pages.
    """

    list_display = (
        "username_link",
        "full_name_link",
        "person_profile_status",
        "email",
        "owned_resources_count",
        "created_content_count",
        "submitted_content_count",
        "reviews_count",
        "bookmarks_count",
        "likes_count",
        "community_memberships_count",
        "view_events_count",
        "edit_logs_count",
        "last_login",
        "is_active",
    )

    list_filter = ("is_active", "is_staff", "last_login", "date_joined")
    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "person__first_name",
        "person__last_name",
    )
    ordering = ("-date_joined",)
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("person")
        qs = qs.annotate(
            resources_count=Count("owned_resources", distinct=True),
            created_contents_count=Count("created_resource_contents", distinct=True),
            submitted_contents_count=Count("submitted_resource_contents", distinct=True),
            review_count=Count("reviews_written", distinct=True),
            bookmark_count=Count("bookmarks", distinct=True),
            like_count=Count("likes", distinct=True),
            membership_count=Count("community_memberships", distinct=True),
            view_event_count=Count("view_events", distinct=True),
            edit_log_count=Count("edit_logs", distinct=True),
        )
        return qs

    def username_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank"><strong>{}</strong></a>', url, obj.username
        )

    username_link.short_description = "Username"
    username_link.admin_order_field = "username"

    def full_name_link(self, obj):
        try:
            person = obj.person
            url = reverse("admin:curation_person_change", args=[person.pk])
            full_name = (
                person.full_name
                if hasattr(person, "full_name")
                else f"{person.first_name} {person.last_name}".strip()
            )
            return format_html('<a href="{}" target="_blank">{}</a>', url, full_name or person.pk)
        # Not every User has a linked Person (it is optional). RelatedObjectDoesNotExist is
        # the common case; broad except also covers unexpected DB errors — safe here because
        # N/A is a correct fallback for an admin-only read-only column.
        except Exception:
            return mark_safe('<span style="color: #999; font-style: italic;">N/A</span>')

    full_name_link.short_description = "Full Name"

    def owned_resources_count(self, obj):
        count = obj.resources_count
        if count == 0:
            return mark_safe('<span style="color: #999;">0</span>')
        url = reverse("admin:curation_resource_changelist") + f"?owner__id__exact={obj.pk}"
        return format_html(
            '<a href="{}" target="_blank" style="color: #007bff;">{}</a>', url, count
        )

    owned_resources_count.short_description = "Resources"
    owned_resources_count.admin_order_field = "resources_count"

    def created_content_count(self, obj):
        count = obj.created_contents_count
        if count == 0:
            return mark_safe('<span style="color: #999;">0</span>')
        url = (
            reverse("admin:curation_resourcecontent_changelist")
            + f"?created_by__id__exact={obj.pk}"
        )
        return format_html(
            '<a href="{}" target="_blank" style="color: #28a745;">{}</a>', url, count
        )

    created_content_count.short_description = "Created"
    created_content_count.admin_order_field = "created_contents_count"

    def submitted_content_count(self, obj):
        count = obj.submitted_contents_count
        if count == 0:
            return mark_safe('<span style="color: #999;">0</span>')
        url = (
            reverse("admin:curation_resourcecontent_changelist")
            + f"?submitted_by__id__exact={obj.pk}"
        )
        return format_html(
            '<a href="{}" target="_blank" style="color: #17a2b8;">{}</a>', url, count
        )

    submitted_content_count.short_description = "Submitted"
    submitted_content_count.admin_order_field = "submitted_contents_count"

    def reviews_count(self, obj):
        count = obj.review_count
        if count == 0:
            return mark_safe('<span style="color: #999;">0</span>')
        url = reverse("admin:curation_review_changelist") + f"?reviewer__id__exact={obj.pk}"
        return format_html(
            '<a href="{}" target="_blank" style="color: #fd7e14;">{}</a>', url, count
        )

    reviews_count.short_description = "Reviews"
    reviews_count.admin_order_field = "review_count"

    def bookmarks_count(self, obj):
        count = obj.bookmark_count
        if count == 0:
            return mark_safe('<span style="color: #999;">0</span>')
        url = reverse("admin:curation_bookmark_changelist") + f"?user__id__exact={obj.pk}"
        return format_html(
            '<a href="{}" target="_blank" style="color: #6f42c1;">{}</a>', url, count
        )

    bookmarks_count.short_description = "Bookmarks"
    bookmarks_count.admin_order_field = "bookmark_count"

    def likes_count(self, obj):
        count = obj.like_count
        if count == 0:
            return mark_safe('<span style="color: #999;">0</span>')
        url = reverse("admin:curation_like_changelist") + f"?user__id__exact={obj.pk}"
        return format_html(
            '<a href="{}" target="_blank" style="color: #e83e8c;">{}</a>', url, count
        )

    likes_count.short_description = "Likes"
    likes_count.admin_order_field = "like_count"

    def community_memberships_count(self, obj):
        count = obj.membership_count
        if count == 0:
            return mark_safe('<span style="color: #999;">0</span>')
        url = (
            reverse("admin:curation_communitymembership_changelist") + f"?user__id__exact={obj.pk}"
        )
        return format_html(
            '<a href="{}" target="_blank" style="color: #20c997;">{}</a>', url, count
        )

    community_memberships_count.short_description = "Communities"
    community_memberships_count.admin_order_field = "membership_count"

    def view_events_count(self, obj):
        count = obj.view_event_count
        if count == 0:
            return mark_safe('<span style="color: #999;">0</span>')
        url = reverse("admin:curation_viewevent_changelist") + f"?user__id__exact={obj.pk}"
        return format_html(
            '<a href="{}" target="_blank" style="color: #6c757d;">{}</a>', url, count
        )

    view_events_count.short_description = "Views"
    view_events_count.admin_order_field = "view_event_count"

    def edit_logs_count(self, obj):
        count = obj.edit_log_count
        if count == 0:
            return mark_safe('<span style="color: #999;">0</span>')
        url = reverse("admin:curation_editlog_changelist") + f"?user__id__exact={obj.pk}"
        return format_html(
            '<a href="{}" target="_blank" style="color: #dc3545;">{}</a>', url, count
        )

    edit_logs_count.short_description = "Edit Logs"
    edit_logs_count.admin_order_field = "edit_log_count"

    # ------------------------------------------------------------------
    # Person profile status column + create-person action
    # ------------------------------------------------------------------

    def person_profile_status(self, obj):
        try:
            person = obj.person
            url = reverse("admin:curation_person_change", args=[person.pk])
            return format_html(
                '<a href="{}" target="_blank" style="color:#28a745;font-weight:bold;">&#10003; Profile OK</a>',
                url,
            )
        except Exception:
            create_url = reverse("admin:users_userdetails_create_person", args=[obj.pk])
            return format_html(
                '<span style="color:#dc3545;font-weight:bold;">&#10007; Missing</span> '
                '&nbsp;<a href="{}" style="background:#dc3545;color:#fff;padding:2px 8px;'
                'border-radius:3px;font-size:11px;text-decoration:none;">Create Profile</a>',
                create_url,
            )

    person_profile_status.short_description = "Person Profile"
    person_profile_status.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:user_id>/create-person/",
                self.admin_site.admin_view(self.create_person_view),
                name="users_userdetails_create_person",
            ),
        ]
        return custom + urls

    @staticmethod
    def _extract_oidc_name(extra_data):
        """Read given_name / family_name from both old flat and new nested extra_data formats."""
        given = extra_data.get("given_name", "")
        family = extra_data.get("family_name", "")
        if given or family:
            return given, family
        userinfo = extra_data.get("userinfo", {}) or {}
        return userinfo.get("given_name", ""), userinfo.get("family_name", "")

    def create_person_view(self, request, user_id):
        from allauth.socialaccount.models import SocialAccount
        from curation.models import Person

        changelist_url = reverse("admin:users_userdetails_changelist")
        user = User.objects.filter(pk=user_id).first()
        if not user:
            messages.error(request, f"User id={user_id} not found.")
            return HttpResponseRedirect(changelist_url)

        if Person.objects.filter(user=user).exists():
            messages.info(request, f"Person profile already exists for {user.username}.")
            return HttpResponseRedirect(changelist_url)

        # Try to get name from OIDC social account
        sa = SocialAccount.objects.filter(user=user).first()
        extra_data = sa.extra_data if sa else {}
        given, family = self._extract_oidc_name(extra_data)

        # Fall back to Django User name fields if OIDC has nothing
        if not given:
            given = user.first_name or user.username
        if not family:
            family = user.last_name or ""

        Person.objects.create(
            user=user,
            first_name=given,
            last_name=family,
            privacy_level="private",
            email_notifications=True,
        )
        messages.success(
            request,
            f"Person profile created for {user.username} ({given} {family}).".strip(),
        )
        return HttpResponseRedirect(changelist_url)
