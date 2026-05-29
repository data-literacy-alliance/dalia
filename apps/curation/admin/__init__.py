"""
Modular admin configuration for curation app.

Modules:
- inlines.py: Inline admin classes
- vocabularies.py: Controlled vocabulary admins
- profiles.py: Person and Organization admins
- communities.py: Community and membership admins
- relations.py: RelationTypeCategory and RelationType admins
- resources.py: Resource and ResourceContent admins
- interactions.py: Bookmark and Like admins
- analytics.py: ViewEvent and EditLog admins
- reviews.py: Review system admins
- consents.py: GDPR consent admins
"""

from curation.admin import (  # noqa: F401
    analytics,
    communities,
    consents,
    interactions,
    profiles,
    relations,
    resources,
    reviews,
    vocabularies,
)

__all__ = [
    "analytics",
    "communities",
    "consents",
    "interactions",
    "profiles",
    "relations",
    "resources",
    "reviews",
    "vocabularies",
]
