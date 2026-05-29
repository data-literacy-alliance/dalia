"""
Forms for curation app (frontend use).
"""
from __future__ import annotations

from curation.models import (
    RelationType,
    ResourceCommunityRelation,
    ResourceContent,
    ResourceLink,
    ResourceRelatedItem,
)
from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory


class ResourceContentForm(forms.ModelForm):
    class Meta:
        model = ResourceContent
        fields = [
            "resource",
            "languages",
            "title",
            "main_url",
            "publication_date",
            "description",
            "size_mb",
            "people",
            "organizations",
            "learning_resource_types",
            "disciplines",
            "licenses",
            "proficiency_levels",
            "target_groups",
            "file_formats",
            "media_types",
            "keywords",
            "created_by",
        ]
        widgets = {
            "publication_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 6}),
        }

    def clean(self):
        data = super().clean()
        if not data.get("title"):
            self.add_error("title", "Title is required.")
        if not data.get("main_url"):
            self.add_error("main_url", "URL is required.")
        if not data.get("licenses"):
            self.add_error("licenses", "At least one license is required.")
        if not data.get("languages"):
            self.add_error("languages", "At least one language is required.")
        return data


class BaseOrderedFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        for i, form in enumerate(self.forms):
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            if form.cleaned_data.get("order") in (None, ""):
                form.cleaned_data["order"] = i


class ResourceCommunityRelationForm(forms.ModelForm):
    """Custom form for ResourceCommunityRelation with filtered relation types."""

    class Meta:
        model = ResourceCommunityRelation
        fields = ("community", "relation_type", "order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["relation_type"].queryset = RelationType.objects.filter(
            is_active=True
        ).select_related("category").order_by("category__order", "order", "label")
        self.fields["relation_type"].help_text = (
            "Select the type of relationship between this resource and the community."
        )


class ResourceRelatedItemForm(forms.ModelForm):
    """Custom form for ResourceRelatedItem with filtered relation types."""

    class Meta:
        model = ResourceRelatedItem
        fields = ("relation_type", "target_url", "order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["relation_type"].queryset = RelationType.objects.filter(
            is_active=True
        ).select_related("category").order_by("category__order", "order", "label")
        self.fields["relation_type"].help_text = (
            "Select how this resource relates to the target URL."
        )


LinkFormSet = inlineformset_factory(
    parent_model=ResourceContent,
    model=ResourceLink,
    formset=BaseOrderedFormSet,
    fields=("url", "order"),
    extra=1,
    can_delete=True,
)

CommunityRelationFormSet = inlineformset_factory(
    parent_model=ResourceContent,
    model=ResourceCommunityRelation,
    form=ResourceCommunityRelationForm,
    formset=BaseOrderedFormSet,
    extra=1,
    can_delete=True,
)

RelatedItemFormSet = inlineformset_factory(
    parent_model=ResourceContent,
    model=ResourceRelatedItem,
    form=ResourceRelatedItemForm,
    formset=BaseOrderedFormSet,
    extra=1,
    can_delete=True,
)
