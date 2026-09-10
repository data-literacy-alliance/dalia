from __future__ import annotations

from curation.models.base import TimeStampedModel, UUIDMixin
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.core.validators import MinValueValidator, URLValidator
from django.db import models
from django.db.models import GeneratedField, Q
from sortedm2m.fields import SortedManyToManyField
from taggit.managers import TaggableManager


class ResourceManager(models.Manager):
    """Custom manager for Resource with UUID optimizations."""

    def get_by_uuid_with_contents(self, uuid_value):
        """Get resource by UUID with prefetched contents."""
        try:
            return self.select_related("owner").prefetch_related("contents").get(uuid=uuid_value)
        except self.model.DoesNotExist:
            return None

    def active_resources(self):
        """Return only non-removed resources."""
        return self.filter(is_removed=False)


class ResourceContentManager(models.Manager):
    """Custom manager for ResourceContent with UUID optimizations."""

    def get_by_uuid_with_relations(self, uuid_value):
        """Get content by UUID with optimized related object fetching."""
        try:
            return (
                self.select_related("resource", "created_by", "submitted_by")
                .prefetch_related(
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
                    "links",
                    "community_relations",
                    "related_items",
                )
                .get(uuid=uuid_value)
            )
        except self.model.DoesNotExist:
            return None

    def for_review(self):
        """Return contents submitted for review."""
        return self.filter(submitted_for_review=True)


class Resource(UUIDMixin, TimeStampedModel):
    """
    Resource grouper for versioned content.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_resources"
    )
    title = models.CharField(
        max_length=500, blank=True, help_text="Display title for this resource (grouper)."
    )
    is_removed = models.BooleanField(
        default=False, help_text="Soft delete flag. Curators can set this."
    )
    # Publishing fields (replaces django-cms versioning)
    version = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    objects = ResourceManager()

    class Meta:
        permissions = (("soft_delete_resource", "Can soft delete resource"),)
        ordering = ("-created",)

    def __str__(self):
        if self.title:
            return f"Resource #{self.pk} - {self.title}"
        return f"Resource #{self.pk}"


class ResourceContent(UUIDMixin, TimeStampedModel):
    """
    Versioned content with full metadata and relationships.
    """

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="contents")
    languages = models.ManyToManyField(
        "curation.Language",
        blank=False,
        related_name="resource_contents",
        help_text="Languages in which this content is available (at least one required)",
    )

    # Core content fields
    title = models.CharField(max_length=500)
    main_url = models.URLField(validators=[URLValidator()], help_text="Main content URL")
    publication_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)
    size_mb = models.DecimalField(
        max_digits=12, decimal_places=3, blank=True, null=True, validators=[MinValueValidator(0)]
    )

    # FTS — stored generated column; maintained by Postgres on INSERT/UPDATE.
    search_vector = GeneratedField(
        expression=SearchVector("title", "description", config="english"),
        output_field=SearchVectorField(),
        db_persist=True,
    )

    # Authors (ordering matters)
    people = SortedManyToManyField(
        "curation.Person", blank=True, related_name="resource_contents_people"
    )
    organizations = SortedManyToManyField(
        "curation.Organization", blank=True, related_name="resource_contents_orgs"
    )

    # Vocabularies (all multi-select)
    learning_resource_types = models.ManyToManyField("curation.LearningResourceType", blank=True)
    disciplines = models.ManyToManyField("curation.Discipline", blank=True)
    licenses = models.ManyToManyField("curation.License", blank=True)
    proficiency_levels = models.ManyToManyField("curation.ProficiencyLevel", blank=True)
    target_groups = models.ManyToManyField("curation.TargetGroup", blank=True)
    file_formats = models.ManyToManyField("curation.FileFormat", blank=True)
    media_types = models.ManyToManyField("curation.MediaType", blank=True)

    # Keywords (tags)
    keywords = TaggableManager(blank=True)

    # Versioning / auditing
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_resource_contents"
    )

    # Review system integration
    submitted_for_review = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(blank=True, null=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_resource_contents",
        blank=True,
        null=True,
    )
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=False, db_index=True)

    objects = ResourceContentManager()

    class Meta:
        ordering = ("-created",)
        constraints = [
            models.UniqueConstraint(
                fields=["resource"],
                condition=Q(is_active=True),
                name="uniq_active_content_per_resource",
            ),
        ]
        indexes = [
            GinIndex(fields=["search_vector"], name="rc_fts_vector_gin"),
        ]

    def __str__(self):
        resource_title = self.resource.title if self.resource.title else "Untitled"
        return f"RC#{self.pk} - {self.title} (Resource: {resource_title})"

    def copy_relations(self, old_instance: ResourceContent):
        """Copy all relationships from another ResourceContent instance."""
        self.people.set(old_instance.people.all())
        self.organizations.set(old_instance.organizations.all())
        self.learning_resource_types.set(old_instance.learning_resource_types.all())
        self.disciplines.set(old_instance.disciplines.all())
        self.licenses.set(old_instance.licenses.all())
        self.proficiency_levels.set(old_instance.proficiency_levels.all())
        self.target_groups.set(old_instance.target_groups.all())
        self.file_formats.set(old_instance.file_formats.all())
        self.media_types.set(old_instance.media_types.all())
        self.languages.set(old_instance.languages.all())
        self.keywords.set(old_instance.keywords.all())

        # Copy related objects (these will be imported from relations module)
        for link in old_instance.links.all():
            from curation.models.relations import ResourceLink

            ResourceLink.objects.create(content=self, url=link.url, order=link.order)

        for rel in old_instance.community_relations.all():
            from curation.models.relations import ResourceCommunityRelation

            ResourceCommunityRelation.objects.create(
                content=self,
                community=rel.community,
                relation_type=rel.relation_type,
                order=rel.order,
            )

        for item in old_instance.related_items.all():
            from curation.models.relations import ResourceRelatedItem

            ResourceRelatedItem.objects.create(
                content=self,
                relation_type=item.relation_type,
                target_url=item.target_url,
                order=item.order,
            )
