from __future__ import annotations

from curation.models.base import Activatable, OrderedModel, TimeStampedModel, UUIDMixin
from django.db import models


class RelationTypeCategory(UUIDMixin, Activatable, TimeStampedModel):
    """
    Categories for organizing relation types (e.g., Content Relations, Version Relations).
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7, default="#6c757d", help_text="Hex color code for UI display"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "name")
        verbose_name_plural = "Relation Type Categories"

    def __str__(self):
        return self.name


class RelationType(UUIDMixin, Activatable, TimeStampedModel):
    """
    Dynamic relation types to replace hardcoded RELATION_TYPE_CHOICES.
    """

    code = models.CharField(max_length=64, unique=True, help_text="Machine-readable identifier")
    label = models.CharField(max_length=100, help_text="Human-readable display name")
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        RelationTypeCategory, on_delete=models.PROTECT, related_name="relation_types"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("category__order", "order", "label")

    def __str__(self):
        return self.label


class ResourceLink(UUIDMixin, OrderedModel, TimeStampedModel):
    """
    Additional URLs associated with a resource content.
    """

    content = models.ForeignKey(
        "curation.ResourceContent", on_delete=models.CASCADE, related_name="links"
    )
    url = models.URLField()

    def __str__(self):
        return self.url


class ResourceRelatedItem(UUIDMixin, OrderedModel, TimeStampedModel):
    """
    Related items connected to a resource (DOI references, etc.).
    """

    content = models.ForeignKey(
        "curation.ResourceContent", on_delete=models.CASCADE, related_name="related_items"
    )
    relation_type = models.ForeignKey(
        RelationType, on_delete=models.PROTECT, related_name="related_items"
    )
    target_url = models.URLField(help_text="URL or DOI resolver link")

    def __str__(self):
        return f"{self.relation_type.label} -> {self.target_url}"


class ResourceCommunityRelation(UUIDMixin, OrderedModel, TimeStampedModel):
    """
    Relationships between resources and communities.
    """

    content = models.ForeignKey(
        "curation.ResourceContent", on_delete=models.CASCADE, related_name="community_relations"
    )
    community = models.ForeignKey(
        "curation.Community", on_delete=models.CASCADE, related_name="resource_relations"
    )
    relation_type = models.ForeignKey(
        RelationType, on_delete=models.PROTECT, related_name="community_relations"
    )

    class Meta(OrderedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["content", "community", "relation_type"],
                name="unique_resource_community_relation",
            )
        ]

    def __str__(self):
        return f"{self.community} [{self.relation_type.label}]"
