"""
Admin for AccountDeletionRequest model.
"""

from core.admin import BaseModelAdmin
from django.contrib import admin
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ..models import AccountDeletionRequest
from ..services import AccountDeletionService
from .inlines import AccountDeletionItemInline, AccountDeletionLogInline


@admin.register(AccountDeletionRequest)
class AccountDeletionRequestAdmin(BaseModelAdmin):
    """
    Admin interface for account deletion requests.
    """

    list_display = [
        "id",
        "user_display",
        "status_badge",
        "initiated_at",
        "days_remaining_display",
        "token_status",
        "items_summary",
        "actions_display",
    ]
    list_filter = [
        "status",
        "initiated_at",
        "confirmed_at",
    ]
    search_fields = [
        "user__username",
        "user__email",
        "uuid",
        "confirmation_token",
    ]
    readonly_fields = [
        "uuid",
        "confirmation_token",
        "initiated_by",
        "initiated_at",
        "confirmed_at",
        "confirmation_ip",
        "confirmation_user_agent",
        "token_expires_at",
        "deletion_scheduled_at",
        "completed_at",
        "completed_by",
        "cancelled_at",
        "cancelled_by",
        "user_snapshot",
        "created",
        "modified",
        "status_badge",
        "days_remaining_display",
        "token_status",
        "review_progress",
    ]
    fieldsets = [
        (
            "User Information",
            {
                "fields": [
                    "user",
                    "user_snapshot",
                ]
            },
        ),
        (
            "Request Status",
            {
                "fields": [
                    "status",
                    "status_badge",
                    "days_remaining_display",
                    "token_status",
                    "review_progress",
                ]
            },
        ),
        (
            "Timeline",
            {
                "fields": [
                    ("initiated_by", "initiated_at"),
                    ("confirmed_at", "confirmation_ip"),
                    "confirmation_user_agent",
                    ("token_expires_at", "deletion_scheduled_at"),
                    ("completed_at", "completed_by"),
                    ("cancelled_at", "cancelled_by", "cancellation_reason"),
                ]
            },
        ),
        (
            "Technical Details",
            {
                "fields": [
                    "uuid",
                    "confirmation_token",
                    ("created", "modified"),
                ],
                "classes": ["collapse"],
            },
        ),
    ]
    inlines = [AccountDeletionItemInline, AccountDeletionLogInline]

    actions = [
        "send_confirmation_emails",
        "cancel_selected_requests",
        "mark_as_expired",
    ]

    def user_display(self, obj):
        """Display user with link to admin."""
        url = reverse("admin:users_user_change", args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>', url, obj.user.username, obj.user.email
        )

    user_display.short_description = "User"

    def status_badge(self, obj):
        """Display status with color-coded badge."""
        colors = {
            "pending": "#FFA500",
            "confirmed": "#FF4500",
            "processing": "#4169E1",
            "completed": "#228B22",
            "cancelled": "#808080",
            "expired": "#696969",
        }
        color = colors.get(obj.status, "#000000")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    def days_remaining_display(self, obj):
        """Display days until deletion or N/A."""
        if obj.status == "confirmed" and obj.deletion_scheduled_at:
            days = obj.days_until_deletion
            if days is not None:
                if days == 0:
                    return mark_safe('<strong style="color: #dc2626;">Today!</strong>')
                elif days <= 7:
                    return format_html('<strong style="color: orange;">{} days</strong>', days)
                else:
                    return f"{days} days"
        return mark_safe("<em>N/A</em>")

    days_remaining_display.short_description = "Days Remaining"

    def token_status(self, obj):
        """Display token expiry status."""
        if obj.status == "pending":
            if not obj.token_expires_at:
                return mark_safe("<em>Not set</em>")
            if obj.token_is_expired:
                return mark_safe('<span style="color: #dc2626;font-weight:500;">Expired</span>')
            else:
                delta = obj.token_expires_at - timezone.now()
                hours = int(delta.total_seconds() / 3600)
                return format_html('<span style="color: green;">Valid ({} hours)</span>', hours)
        return mark_safe("<em>N/A</em>")

    token_status.short_description = "Token"

    def items_summary(self, obj):
        """Display summary of deletion items."""
        items = obj.items.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(action="pending")),
            delete=Count("id", filter=Q(action="delete")),
            anonymize=Count("id", filter=Q(action="anonymize")),
            keep=Count("id", filter=Q(action="keep")),
        )
        return format_html(
            "{} total<br><small>Pending: {} | Delete: {} | Anonymize: {} | Keep: {}</small>",
            items["total"],
            items["pending"],
            items["delete"],
            items["anonymize"],
            items["keep"],
        )

    items_summary.short_description = "Content Items"

    def review_progress(self, obj):
        """Display review progress bar."""
        items = obj.items.aggregate(
            total=Count("id"),
            reviewed=Count("id", filter=~Q(action="pending")),
        )
        if items["total"] == 0:
            return "No items"

        percentage = int((items["reviewed"] / items["total"]) * 100)
        color = "#228B22" if percentage == 100 else "#FFA500"

        return format_html(
            '<div style="width: 200px; background-color: #f0f0f0; border: 1px solid #ccc;">'
            '<div style="width: {}%; background-color: {}; color: white; text-align: center; '
            'padding: 2px 0;">{} / {} ({}%)</div></div>',
            percentage,
            color,
            items["reviewed"],
            items["total"],
            percentage,
        )

    review_progress.short_description = "Review Progress"

    def actions_display(self, obj):
        """Display quick action buttons."""
        buttons = []

        if obj.status == "pending":
            buttons.append(
                format_html(
                    '<a class="button" href="{}">Send Email</a>',
                    reverse("admin:account_deletion_send_email", args=[obj.pk]),
                )
            )

        if obj.can_be_cancelled:
            buttons.append(
                format_html(
                    '<a class="button" href="{}">Cancel</a>',
                    reverse("admin:account_deletion_cancel", args=[obj.pk]),
                )
            )

        if obj.status == "confirmed":
            pending = obj.items.filter(action="pending").count()
            if pending == 0:
                buttons.append(
                    format_html(
                        '<a class="button" href="{}" style="background-color: #dc3545;">Process Deletion</a>',
                        reverse("admin:account_deletion_process", args=[obj.pk]),
                    )
                )

        return mark_safe(" ".join(buttons)) if buttons else mark_safe("<em>No actions</em>")

    actions_display.short_description = "Quick Actions"

    def get_urls(self):
        """Add custom admin URLs."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/send-email/",
                self.admin_site.admin_view(self.send_email_view),
                name="account_deletion_send_email",
            ),
            path(
                "<int:pk>/cancel/",
                self.admin_site.admin_view(self.cancel_view),
                name="account_deletion_cancel",
            ),
            path(
                "<int:pk>/process/",
                self.admin_site.admin_view(self.process_view),
                name="account_deletion_process",
            ),
        ]
        return custom_urls + urls

    def send_email_view(self, request, pk):
        """Custom view to send confirmation email."""
        deletion_request = self.get_object(request, pk)

        if request.method == "POST":
            success = AccountDeletionService.send_confirmation_email(deletion_request)
            if success:
                self.message_user(
                    request, f"Confirmation email sent to {deletion_request.user.email}"
                )
            else:
                self.message_user(request, "Failed to send email", level="error")
            return self.response_post_save_change(request, deletion_request)

        context = {
            "title": "Send Confirmation Email",
            "deletion_request": deletion_request,
            "opts": self.model._meta,
        }
        return render(request, "admin/account_deletion/send_email.html", context)

    def cancel_view(self, request, pk):
        """Custom view to cancel deletion request."""
        deletion_request = self.get_object(request, pk)

        if request.method == "POST":
            reason = request.POST.get("reason", "")
            try:
                AccountDeletionService.cancel_deletion(
                    deletion_request=deletion_request, cancelled_by=request.user, reason=reason
                )
                self.message_user(request, "Deletion request cancelled successfully")
                return self.response_post_save_change(request, deletion_request)
            except ValueError as e:
                self.message_user(request, str(e), level="error")

        context = {
            "title": "Cancel Deletion Request",
            "deletion_request": deletion_request,
            "opts": self.model._meta,
        }
        return render(request, "admin/account_deletion/cancel.html", context)

    def process_view(self, request, pk):
        """Custom view to process deletion."""
        deletion_request = self.get_object(request, pk)

        if request.method == "POST":
            try:
                AccountDeletionService.process_deletion(
                    deletion_request=deletion_request, admin_user=request.user
                )
                self.message_user(request, "Deletion processed successfully")
                return self.response_post_save_change(request, deletion_request)
            except ValueError as e:
                self.message_user(request, str(e), level="error")

        items = deletion_request.items.aggregate(
            delete=Count("id", filter=Q(action="delete")),
            anonymize=Count("id", filter=Q(action="anonymize")),
            keep=Count("id", filter=Q(action="keep")),
        )

        context = {
            "title": "Process Deletion",
            "deletion_request": deletion_request,
            "items_summary": items,
            "opts": self.model._meta,
        }
        return render(request, "admin/account_deletion/process.html", context)

    # List actions

    def send_confirmation_emails(self, request, queryset):
        """Send confirmation emails to selected pending requests."""
        count = 0
        for req in queryset.filter(status="pending"):
            if AccountDeletionService.send_confirmation_email(req):
                count += 1
        self.message_user(request, f"Sent {count} confirmation emails")

    send_confirmation_emails.short_description = "Send confirmation emails to selected"

    def cancel_selected_requests(self, request, queryset):
        """Cancel selected requests."""
        count = 0
        for req in queryset.filter(status__in=["pending", "confirmed"]):
            try:
                AccountDeletionService.cancel_deletion(
                    deletion_request=req,
                    cancelled_by=request.user,
                    reason="Cancelled by admin via bulk action",
                )
                count += 1
            except ValueError:
                pass
        self.message_user(request, f"Cancelled {count} requests")

    cancel_selected_requests.short_description = "Cancel selected requests"

    def mark_as_expired(self, request, queryset):
        """Mark selected pending requests as expired."""
        count = queryset.filter(status="pending", token_expires_at__lt=timezone.now()).update(
            status="expired"
        )
        self.message_user(request, f"Marked {count} requests as expired")

    mark_as_expired.short_description = "Mark as expired"
