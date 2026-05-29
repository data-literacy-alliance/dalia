"""
Admin classes for review models (Review, ReviewQuestion, ReviewAnswer).
"""
from core.admin import BaseModelAdmin
from curation.admin.inlines import ReviewAnswerInline
from curation.models import Review, ReviewQuestion
from django import forms
from django.contrib import admin
from django.forms.widgets import NumberInput, Textarea


@admin.register(Review)
class ReviewAdmin(BaseModelAdmin):
    list_display = ("resource_content", "reviewer", "status", "recommendation", "created", "uuid")
    list_filter = ("status", "recommendation", "community", "created")
    search_fields = (
        "resource_content__id", "resource_content__title",
        "resource_content__resource__id", "resource_content__resource__title",
        "reviewer__username", "summary", "uuid",
    )
    readonly_fields = ("uuid", "created", "modified", "submitted_at", "completed_at")
    raw_id_fields = ("resource_content", "reviewer", "community")
    inlines = [ReviewAnswerInline]

    fieldsets = (
        (None, {
            "fields": ("resource_content", "reviewer", "community", "uuid"),
        }),
        ("Review Content", {
            "fields": ("status", "recommendation", "summary", "terms_version"),
        }),
        ("Timeline", {
            "fields": ("created", "submitted_at", "completed_at"),
        }),
    )

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        queryset.update(status="approved")
        self.message_user(request, f"Approved {queryset.count()} reviews.")

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request, queryset):
        queryset.update(status="rejected")
        self.message_user(request, f"Rejected {queryset.count()} reviews.")

    actions = [approve_reviews, reject_reviews]


class ReviewQuestionAdminForm(forms.ModelForm):
    """Custom form for ReviewQuestion with better widgets and validation."""

    class Meta:
        model = ReviewQuestion
        fields = [
            "community",
            "question_text",
            "question_type",
            "choices",
            "min_value",
            "max_value",
            "order",
            "required",
            "is_active",
            "help_text_field",
        ]
        widgets = {
            "choices": Textarea(attrs={
                "rows": 4,
                "placeholder": '["Option 1", "Option 2", "Option 3"]',
            }),
            "min_value": NumberInput(attrs={"min": 0, "max": 100}),
            "max_value": NumberInput(attrs={"min": 1, "max": 100}),
            "question_text": Textarea(attrs={"rows": 3}),
            "help_text_field": Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get("question_type")
        choices = cleaned_data.get("choices")
        min_value = cleaned_data.get("min_value")
        max_value = cleaned_data.get("max_value")

        if question_type == "choice" and not choices:
            raise forms.ValidationError("Choice questions must have choices defined.")

        if question_type in ["rating", "scale"]:
            if min_value is None or max_value is None:
                raise forms.ValidationError("Rating/scale questions must have min and max values.")
            if min_value >= max_value:
                raise forms.ValidationError("Min value must be less than max value.")

        return cleaned_data


@admin.register(ReviewQuestion)
class ReviewQuestionAdmin(BaseModelAdmin):
    form = ReviewQuestionAdminForm
    list_display = ("question_text_short", "community", "question_type", "required", "is_active", "order", "uuid")
    list_filter = ("question_type", "community", "required", "is_active")
    search_fields = ("question_text", "uuid")
    readonly_fields = ("uuid", "created", "modified")
    raw_id_fields = ("community",)

    fieldsets = (
        (None, {
            "fields": ("community", "question_text", "question_type", "uuid"),
        }),
        ("Configuration", {
            "fields": ("choices", "min_value", "max_value", "help_text_field"),
        }),
        ("Settings", {
            "fields": ("order", "required", "is_active"),
        }),
    )

    def question_text_short(self, obj):
        text = obj.question_text
        return text[:50] + "..." if len(text) > 50 else text
    question_text_short.short_description = "Question"

    @admin.action(description="Activate selected questions")
    def activate_questions(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"Activated {queryset.count()} questions.")

    @admin.action(description="Deactivate selected questions")
    def deactivate_questions(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {queryset.count()} questions.")

    actions = [activate_questions, deactivate_questions]
