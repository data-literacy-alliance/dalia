"""
API models for recommendation app.

MIGRATION NOTE (Phase 3):
✅ Updated to use apps.search structure after legacy dalia app migration.
The Item dataclass is now imported from search.api_models.
"""

from dataclasses import dataclass
from typing import List, Optional

from search.api_models.api_models import Item


@dataclass
class SuggestedContents:
    """
    Dataclass representing a collection of suggested learning resources.

    Attributes:
        results: Optional list of Item objects representing suggested content
    """

    results: Optional[List[Item]]
