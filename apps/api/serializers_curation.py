from curation import models as cf
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers

User = get_user_model()


class _AllReadOnlySerializer(serializers.ModelSerializer):
    """
    Base serializer that exposes all model fields but marks them read-only.
    Avoids invalid read_only_fields="__all__" (must be list/tuple).
    """

    class Meta:
        fields = "__all__"

    def get_fields(self):
        # Let DRF build fields first, then flip them to read-only
        fields = super().get_fields()
        for f in fields.values():
            f.read_only = True
        return fields


class CommunitySerializer(_AllReadOnlySerializer):
    class Meta(_AllReadOnlySerializer.Meta):
        model = cf.Community


class CommunityWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = cf.Community
        fields = ("title", "description")


class DisciplineSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)
    children_count = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    is_root = serializers.SerializerMethodField()
    ancestors = serializers.SerializerMethodField()

    class Meta:
        model = cf.Discipline
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "slug", "parent_label")

    def get_children_count(self, obj):
        """Return count of direct children"""
        return obj.get_children().count()

    def get_level(self, obj):
        """Return hierarchy level (0 for root)"""
        return obj.get_level()

    def get_is_root(self, obj):
        """Check if this is a root discipline"""
        return obj.is_root()

    def get_ancestors(self, obj):
        """Return list of ancestor disciplines"""
        return [
            {"id": ancestor.pk, "label": ancestor.label, "uuid": str(ancestor.uuid)}
            for ancestor in obj.get_ancestors()
        ]

    def validate_parent_id(self, value):
        """Prevent circular references and self-references"""
        if value:
            instance = getattr(self, "instance", None)
            if instance:
                # Prevent self-reference
                if value.pk == instance.pk:
                    raise serializers.ValidationError("A discipline cannot be its own parent.")

                # Prevent circular reference by checking if the selected parent
                # is a descendant of the current instance
                if instance in value.get_descendants():
                    raise serializers.ValidationError(
                        "Cannot create circular reference in hierarchy."
                    )

        return value


class FileFormatSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = cf.FileFormat
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "slug")


class LearningResourceTypeSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = cf.LearningResourceType
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "slug")


class LicenseSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = cf.License
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "slug")


class MediaTypeSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = cf.MediaType
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "slug")


class LanguageSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = cf.Language
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "slug")


class OrganizationSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = cf.Organization
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "slug")


class PersonSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = cf.Person
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified")


class ProficiencyLevelSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = cf.ProficiencyLevel
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "slug")


class TargetGroupSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = cf.TargetGroup
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "slug")


# ---------- resource / content serializers ----------
# Split READ vs WRITE so the frontend has a clear contract.


class ResourceSerializer(serializers.ModelSerializer):
    """Grouper object (no translatable fields)."""

    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = cf.Resource
        fields = ["id", "uuid", "title", "owner", "is_removed", "created", "modified"]
        read_only_fields = ("id", "uuid", "created", "modified")


class MinimalUserSerializer(serializers.ModelSerializer):
    """
    Safe read-only user representation.
    Explicit allowlist — blocks password, is_staff, is_superuser, groups,
    user_permissions, date_joined, last_login, created_at, updated_at.
    """

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]
        read_only_fields = ["id", "username", "first_name", "last_name", "email"]


class ResourceContentReadSerializer(serializers.ModelSerializer):
    """Expanded view of a content version (nice for Swagger & dev UIs)."""

    uuid = serializers.UUIDField(read_only=True)
    resource = ResourceSerializer(read_only=True)
    resource_uuid = serializers.UUIDField(source="resource.uuid", read_only=True)
    resource_title = serializers.CharField(source="resource.title", read_only=True)
    created_by = MinimalUserSerializer(read_only=True)
    submitted_by = MinimalUserSerializer(read_only=True)
    keywords = serializers.SerializerMethodField()

    def get_keywords(self, obj):
        return sorted(obj.keywords.names())

    class Meta:
        model = cf.ResourceContent
        fields = "__all__"
        depth = 1  # expand M2M and FKs one level for convenient inspection


# NOTE: created_by, submitted_by, submitted_at are intentionally writable here.
# The view (ResourceContentViewSet.create) sets them explicitly via data mutation
# BEFORE calling is_valid(), so DRF receives them as regular input fields.
# Adding them to read_only_fields would make DRF strip them → model save fails
# (no model default). If the view is ever refactored to use serializer.save(created_by=...),
# move them to read_only_fields at that point.
class ResourceContentWriteSerializer(serializers.ModelSerializer):
    """
    Write serializer for creating/updating a DRAFT content.
    Frontend sends simple IDs for M2M fields (DRF handles that).
    If 'resource' is omitted, the ViewSet will create one automatically.
    keywords is handled explicitly: TaggableManager is not a real model field
    so DRF cannot introspect it; we pop it from validated_data and call
    instance.keywords.set() after the underlying save.
    """

    uuid = serializers.UUIDField(read_only=True)
    uuid = serializers.UUIDField(read_only=True)
    keywords = serializers.ListField(
        child=serializers.CharField(allow_blank=False, trim_whitespace=True),
        required=False,
        allow_null=True,
        default=None,
        write_only=True,
    )

    class Meta:
        model = cf.ResourceContent
        fields = "__all__"
        # 'resource' may be omitted on POST to create a new grouper
        read_only_fields = ("id", "uuid", "created", "modified")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["keywords"] = sorted(instance.keywords.names())
        return data

    def validate_languages(self, value):
        """Ensure at least one language is provided."""
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one language is required.")
        return value

    def create(self, validated_data):
        keywords = validated_data.pop("keywords", None) or []
        instance = super().create(validated_data)
        if keywords:
            instance.keywords.set(keywords)
        return instance

    def update(self, instance, validated_data):
        keywords = validated_data.pop("keywords", None)
        instance = super().update(instance, validated_data)
        if keywords is not None:
            instance.keywords.set(keywords)
        return instance


# ---------- Community Management ----------
class CommunityMembershipSerializer(serializers.ModelSerializer):
    """Community membership with role management."""

    uuid = serializers.UUIDField(read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)
    community_title = serializers.CharField(source="community.title", read_only=True)

    class Meta:
        model = cf.CommunityMembership
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "joined_at", "approved_at")


# ---------- User Interactions ----------
class BookmarkSerializer(serializers.ModelSerializer):
    """User bookmarks with content object details."""

    uuid = serializers.UUIDField(read_only=True)
    content_object_str = serializers.CharField(source="content_object.__str__", read_only=True)

    class Meta:
        model = cf.Bookmark
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified")


class LikeSerializer(serializers.ModelSerializer):
    """User likes/favorites with content object details."""

    uuid = serializers.UUIDField(read_only=True)
    content_object_str = serializers.CharField(source="content_object.__str__", read_only=True)

    class Meta:
        model = cf.Like
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified")


class ViewEventSerializer(_AllReadOnlySerializer):
    """Analytics view events (read-only)."""

    content_object_str = serializers.CharField(source="content_object.__str__", read_only=True)

    class Meta(_AllReadOnlySerializer.Meta):
        model = cf.ViewEvent


class EditLogSerializer(_AllReadOnlySerializer):
    """Audit trail edit logs (read-only)."""

    content_object_str = serializers.CharField(source="content_object.__str__", read_only=True)

    class Meta(_AllReadOnlySerializer.Meta):
        model = cf.EditLog


# ---------- Review System ----------
class ReviewAnswerSerializer(serializers.ModelSerializer):
    """Review answers - typically nested under Review."""

    uuid = serializers.UUIDField(read_only=True)
    question_text = serializers.CharField(source="question.question_text", read_only=True)
    answer_value = serializers.SerializerMethodField()

    class Meta:
        model = cf.ReviewAnswer
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified")

    def get_answer_value(self, obj):
        """Get the actual answer value regardless of type."""
        return obj.get_answer_value()


class ReviewReadSerializer(serializers.ModelSerializer):
    """Review with expanded details for read operations."""

    uuid = serializers.UUIDField(read_only=True)
    resource_content_title = serializers.CharField(source="resource_content.title", read_only=True)
    reviewer_username = serializers.CharField(source="reviewer.username", read_only=True)
    community_title = serializers.CharField(source="community.title", read_only=True)
    answers = ReviewAnswerSerializer(many=True, read_only=True)
    average_score = serializers.SerializerMethodField()

    class Meta:
        model = cf.Review
        fields = "__all__"

    def get_average_score(self, obj):
        """Get average score from rating questions."""
        return obj.get_score()


class ReviewWriteSerializer(serializers.ModelSerializer):
    """Review for write operations."""

    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = cf.Review
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "submitted_at", "completed_at")


class ReviewQuestionSerializer(serializers.ModelSerializer):
    """Review question configuration."""

    uuid = serializers.UUIDField(read_only=True)
    community_title = serializers.CharField(source="community.title", read_only=True)

    class Meta:
        model = cf.ReviewQuestion
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified")


# ---------- Legal Compliance ----------
class ResourceConsentSerializer(serializers.ModelSerializer):
    """GDPR consent tracking."""

    uuid = serializers.UUIDField(read_only=True)
    resource_content_title = serializers.CharField(source="resource_content.title", read_only=True)
    person_name = serializers.CharField(source="person.full_name", read_only=True)
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = cf.ResourceConsent
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "granted_at", "withdrawn_at")

    def get_is_valid(self, obj):
        """Check if consent is currently valid."""
        return obj.is_valid()


class ResourcePublishingConsentSerializer(serializers.ModelSerializer):
    """Publishing consent management."""

    uuid = serializers.UUIDField(read_only=True)
    resource_content_title = serializers.CharField(source="resource_content.title", read_only=True)
    consenting_person_name = serializers.CharField(
        source="consenting_person.full_name", read_only=True
    )
    is_complete = serializers.SerializerMethodField()
    consent_summary = serializers.SerializerMethodField()

    class Meta:
        model = cf.ResourcePublishingConsent
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified", "consent_given_at", "withdrawn_at")

    def get_is_complete(self, obj):
        """Check if all required consents are given."""
        return obj.is_complete()

    def get_consent_summary(self, obj):
        """Get summary of all consents given."""
        return obj.get_consent_summary()


# ---------- Resource Relations ----------
class RelationTypeCategorySerializer(serializers.ModelSerializer):
    """Relation type categories for organizing relation types."""

    uuid = serializers.UUIDField(read_only=True)
    relation_types_count = serializers.SerializerMethodField()

    class Meta:
        model = cf.RelationTypeCategory
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified")

    def get_relation_types_count(self, obj):
        """Count of active relation types in this category."""
        return obj.relation_types.filter(is_active=True).count()


class RelationTypeSerializer(serializers.ModelSerializer):
    """Relation types with category information."""

    uuid = serializers.UUIDField(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_color = serializers.CharField(source="category.color", read_only=True)

    class Meta:
        model = cf.RelationType
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified")


class ResourceLinkSerializer(serializers.ModelSerializer):
    """External resource links."""

    uuid = serializers.UUIDField(read_only=True)
    content_title = serializers.CharField(source="content.title", read_only=True)

    class Meta:
        model = cf.ResourceLink
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified")


class ResourceCommunityRelationSerializer(serializers.ModelSerializer):
    """Resource-community associations."""

    uuid = serializers.UUIDField(read_only=True)
    content_title = serializers.CharField(source="content.title", read_only=True)
    community_title = serializers.CharField(source="community.title", read_only=True)
    relation_type_label = serializers.CharField(source="relation_type.label", read_only=True)
    relation_type_code = serializers.CharField(source="relation_type.code", read_only=True)
    relation_type_category = serializers.CharField(
        source="relation_type.category.name", read_only=True
    )
    relation_type_category_color = serializers.CharField(
        source="relation_type.category.color", read_only=True
    )

    class Meta:
        model = cf.ResourceCommunityRelation
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the content field queryset dynamically based on request context
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user

            content_qs = cf.ResourceContent.objects.all()

            # Apply filtering based on user role — no CMS versioning, use is_published field
            if user.is_authenticated and (
                user.is_superuser or user.groups.filter(name="Curators").exists()
            ):
                # Superusers/Curators can link to any content
                pass
            elif user.is_authenticated:
                # Regular users can link to published content or their own unpublished content
                content_qs = content_qs.filter(Q(is_published=True) | Q(created_by=user))

            # Update the content field queryset
            self.fields["content"].queryset = content_qs


class ResourceRelatedItemSerializer(serializers.ModelSerializer):
    """Resource relationships."""

    uuid = serializers.UUIDField(read_only=True)

    # Read-only display fields
    content_title = serializers.CharField(source="content.title", read_only=True)
    relation_type_label = serializers.CharField(source="relation_type.label", read_only=True)
    relation_type_code = serializers.CharField(source="relation_type.code", read_only=True)
    relation_type_category = serializers.CharField(
        source="relation_type.category.name", read_only=True
    )
    relation_type_category_color = serializers.CharField(
        source="relation_type.category.color", read_only=True
    )

    class Meta:
        model = cf.ResourceRelatedItem
        fields = "__all__"
        read_only_fields = ("id", "uuid", "created", "modified")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the content field queryset dynamically based on request context
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user

            content_qs = cf.ResourceContent.objects.all()

            # Apply filtering based on user role — no CMS versioning, use is_published field
            if user.is_authenticated and (
                user.is_superuser or user.groups.filter(name="Curators").exists()
            ):
                # Superusers/Curators can link to any content
                pass
            elif user.is_authenticated:
                # Regular users can link to published content or their own unpublished content
                content_qs = content_qs.filter(Q(is_published=True) | Q(created_by=user))

            # Update the content field queryset
            self.fields["content"].queryset = content_qs
