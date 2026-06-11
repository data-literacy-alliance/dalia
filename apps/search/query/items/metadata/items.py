from typing import List, Optional
from uuid import UUID

from rdflib import URIRef

from search.api_models.api_models import Resource
from search.query.items.metadata.authors import get_authors_metadata_for_resources
from search.query.items.metadata.disciplines import get_disciplines_for_resources
from search.query.items.metadata.format import get_format_metadata_for_resources
from search.query.items.metadata.item_communities import get_communities_for_resources
from search.query.items.metadata.keywords import get_keywords_metadata_for_resources
from search.query.items.metadata.languages import get_languages_for_resources
from search.query.items.metadata.learning_resource_types import (
    get_learning_resource_types_for_resources,
)
from search.query.items.metadata.media_types import get_media_types_for_resources
from search.query.items.metadata.one_to_one_metadata import get_one_to_one_metadata_for_resources
from search.query.items.metadata.proficiency_levels import get_proficiency_levels_for_resources
from search.query.items.metadata.target_groups import get_target_groups_for_resources
from search.rdf.dalia_kb import lr_uri_ref


# data for endpoint /items/{itemId}
def get_metadata_for_learning_resource(resource_id: UUID) -> Optional[Resource]:
    items = get_metadata_for_learning_resources([lr_uri_ref(resource_id)])
    # print(f"DEBUG (items.py): get_metadata_for_learning_resource items: {items}") # ADD THIS LINE

    if not items:
        # indicate 404
        return None

    # print(f"DEBUG (items.py): Metadata for resource {resource_id}: {items}") # ADD THIS LINE

    # indicate 200
    return items[0]


def get_metadata_for_learning_resources(resource_uri_refs: List[URIRef]) -> List[Resource]:
    if not resource_uri_refs:
        return []

    # TODO: Parallelize these calls
    items = get_one_to_one_metadata_for_resources(resource_uri_refs)
    items_learning_resource_types = get_learning_resource_types_for_resources(resource_uri_refs)
    items_media_types = get_media_types_for_resources(resource_uri_refs)
    items_disciplines = get_disciplines_for_resources(resource_uri_refs)
    items_target_groups = get_target_groups_for_resources(resource_uri_refs)
    items_proficiency_levels = get_proficiency_levels_for_resources(resource_uri_refs)
    items_format = get_format_metadata_for_resources(resource_uri_refs)
    items_keywords = get_keywords_metadata_for_resources(resource_uri_refs)
    items_authors = get_authors_metadata_for_resources(resource_uri_refs)
    items_communities = get_communities_for_resources(resource_uri_refs)
    items_languages = get_languages_for_resources(resource_uri_refs)

    # print(f"DEBUG (items.py): get_metadata_for_learning_resources - items_languages: {items_languages}") # ADD THIS LINE

    results = []
    for resource_uri_ref in resource_uri_refs:
        item = items.get(resource_uri_ref)
        if not item:
            continue

        _add_metadata_to_item(
            item,
            learning_resource_types=items_learning_resource_types.get(resource_uri_ref),
            media_types=items_media_types.get(resource_uri_ref),
            disciplines=items_disciplines.get(resource_uri_ref),
            target_groups=items_target_groups.get(resource_uri_ref),
            proficiency_levels=items_proficiency_levels.get(resource_uri_ref),
            format=items_format.get(resource_uri_ref),
            keywords=items_keywords.get(resource_uri_ref),
            authors=items_authors.get(resource_uri_ref),
            communities=items_communities.get(resource_uri_ref),
            languages=items_languages.get(resource_uri_ref),
        )
        # print(f"DEBUG (items.py): get_metadata_for_learning_resources - item after _add_metadata_to_item, languages: {item.languages}")
        results.append(item)

    return results


def _add_metadata_to_item(item: Resource, **kwargs) -> None:
    item.learning_resource_types = kwargs.get("learning_resource_types") or []
    item.media_types = kwargs.get("media_types") or []
    item.disciplines = kwargs.get("disciplines") or []
    item.target_groups = kwargs.get("target_groups") or []
    item.proficiency_levels = kwargs.get("proficiency_levels") or []
    item.format = kwargs.get("format") or None
    item.tags = kwargs.get("keywords") or []
    item.authors = kwargs.get("authors") or []
    item.communities = kwargs.get("communities") or []
    item.likes = 0
    item.views = 0
    item.comments = 0
    item.image = None
    item.links = None
    item.languages = kwargs.get("languages") or []
    item.publisher = None
    item.doi = None
    item.learning_time = 10
    item.versions = None
