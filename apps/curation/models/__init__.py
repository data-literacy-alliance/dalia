"""Curation models package — re-exports all models for convenience."""

# Import modules first
from curation.models import (
    base,
    communities,
    consents,
    constants,
    interactions,
    profiles,
    relations,
    resources,
    reviews,
    vocabularies,
)

# Base abstract models
UUIDMixin = base.UUIDMixin
TimeStampedModel = base.TimeStampedModel
Activatable = base.Activatable
NamedVocabulary = base.NamedVocabulary
OrderedModel = base.OrderedModel

# Constants
PRIVACY_CHOICES = constants.PRIVACY_CHOICES

# Profile models
Person = profiles.Person
Organization = profiles.Organization

# Vocabulary models
LearningResourceType = vocabularies.LearningResourceType
Discipline = vocabularies.Discipline
License = vocabularies.License
ProficiencyLevel = vocabularies.ProficiencyLevel
TargetGroup = vocabularies.TargetGroup
FileFormat = vocabularies.FileFormat
MediaType = vocabularies.MediaType
Language = vocabularies.Language

# Core resource models + managers
ResourceManager = resources.ResourceManager
ResourceContentManager = resources.ResourceContentManager
Resource = resources.Resource
ResourceContent = resources.ResourceContent

# Relationship models
RelationTypeCategory = relations.RelationTypeCategory
RelationType = relations.RelationType
ResourceLink = relations.ResourceLink
ResourceRelatedItem = relations.ResourceRelatedItem
ResourceCommunityRelation = relations.ResourceCommunityRelation

# Community models
Community = communities.Community
CommunityMembership = communities.CommunityMembership

# Interaction models
Bookmark = interactions.Bookmark
Like = interactions.Like
ViewEvent = interactions.ViewEvent
EditLog = interactions.EditLog

# Review models
Review = reviews.Review
ReviewQuestion = reviews.ReviewQuestion
ReviewAnswer = reviews.ReviewAnswer

# Consent models
ResourceConsent = consents.ResourceConsent
ResourcePublishingConsent = consents.ResourcePublishingConsent

__all__ = [
    # Base classes
    "UUIDMixin", "TimeStampedModel", "Activatable", "NamedVocabulary", "OrderedModel",
    # Constants
    "PRIVACY_CHOICES",
    # Profiles
    "Person", "Organization",
    # Vocabularies
    "LearningResourceType", "Discipline", "License", "ProficiencyLevel",
    "TargetGroup", "FileFormat", "MediaType", "Language",
    # Resources
    "ResourceManager", "ResourceContentManager", "Resource", "ResourceContent",
    # Relations
    "RelationTypeCategory", "RelationType", "ResourceLink",
    "ResourceRelatedItem", "ResourceCommunityRelation",
    # Communities
    "Community", "CommunityMembership",
    # Interactions
    "Bookmark", "Like", "ViewEvent", "EditLog",
    # Reviews
    "Review", "ReviewQuestion", "ReviewAnswer",
    # Consents
    "ResourceConsent", "ResourcePublishingConsent",
]
