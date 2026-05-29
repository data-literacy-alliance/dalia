"""
Suggestion/autocomplete functions for curation endpoints.

These functions provide autocomplete suggestions for various vocabularies used in the Dalia platform:
- Communities
- Disciplines
- Languages
- Learning resource types
- Licenses
- Media types
- Proficiency levels
- Relation types
- Target groups
"""

from .communities import get_communities_suggestions
from .disciplines import get_disciplines_suggestions
from .languages import get_languages_suggestions
from .learning_resource_types import get_learning_resource_types_suggestions
from .licenses import get_licenses_suggestions
from .media_types import get_media_types_suggestions
from .proficiency_levels import get_proficiency_levels_suggestions
from .relation_types import get_relation_types_suggestions
from .target_groups import get_target_groups_suggestions

__all__ = [
    "get_communities_suggestions",
    "get_disciplines_suggestions",
    "get_languages_suggestions",
    "get_learning_resource_types_suggestions",
    "get_licenses_suggestions",
    "get_media_types_suggestions",
    "get_proficiency_levels_suggestions",
    "get_relation_types_suggestions",
    "get_target_groups_suggestions",
]
