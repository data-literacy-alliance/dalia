"""
Admin inline classes for curation app.
"""

from curation.models import (
    ResourceCommunityRelation,
    ResourceLink,
    ResourceRelatedItem,
    ReviewAnswer,
)
from unfold.admin import TabularInline


class ResourceLinkInline(TabularInline):
    model = ResourceLink
    extra = 0


class ResourceCommunityRelationInline(TabularInline):
    model = ResourceCommunityRelation
    extra = 0


class ResourceRelatedItemInline(TabularInline):
    model = ResourceRelatedItem
    extra = 0


class ReviewAnswerInline(TabularInline):
    model = ReviewAnswer
    extra = 1
    fields = ("question", "text_answer", "choice_answer", "rating_answer", "boolean_answer")
