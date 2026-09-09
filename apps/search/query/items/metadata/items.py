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

    # Related items are PG-only data; batch-fetch from PG by resource UUID.
    items_related_works = _get_related_works_for_resources(resource_uri_refs)
    resource_uuid_strs = [str(uri_ref).split("/")[-1] for uri_ref in resource_uri_refs]
    view_counts = _get_view_counts_for_resources(resource_uuid_strs)

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
            related_works=items_related_works.get(resource_uri_ref),
            views=view_counts.get(str(resource_uri_ref).split("/")[-1], 0),
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
    item.views = kwargs.get("views") or 0
    item.comments = 0
    item.image = None
    item.links = None
    item.languages = kwargs.get("languages") or []
    item.publisher = None
    item.doi = None
    item.learning_time = 10
    item.versions = None
    item.related_works = kwargs.get("related_works") or []


def _get_related_works_for_resources(resource_uri_refs: List[URIRef]) -> dict:
    """Batch-fetch related items from PG for a list of Fuseki resource URIRefs.

    Related items are stored only in PostgreSQL; this bridges the Fuseki metadata
    path to PG-side relation data.
    """
    from curation.models import ResourceContent
    from search.api_models.api_models import LabelValueItem, RelatedWork

    uuids = [str(uri_ref).split("/")[-1] for uri_ref in resource_uri_refs]
    contents = (
        ResourceContent.objects.filter(
            resource__uuid__in=uuids,
            is_active=True,
            resource__is_published=True,
            resource__is_removed=False,
        )
        .select_related("resource")
        .prefetch_related("related_items__relation_type")
    )
    result: dict = {}
    for content in contents:
        uri_ref = lr_uri_ref(content.resource.uuid)
        result[uri_ref] = [
            RelatedWork(
                type=LabelValueItem(
                    label=ri.relation_type.label,
                    value=ri.relation_type.code,
                ),
                link=ri.target_url,
            )
            for ri in content.related_items.order_by("order").all()
        ]
    return result


def _get_view_counts_for_resources(uuids: List[str]) -> dict:
    """Batch-fetch ViewEvent counts keyed by resource UUID string."""
    from curation.models import ViewEvent
    from django.db.models import Count as DjCount

    if not uuids:
        return {}
    return {
        str(row["resource_uuid"]): row["cnt"]
        for row in ViewEvent.objects.filter(resource_uuid__in=uuids)
        .values("resource_uuid")
        .annotate(cnt=DjCount("id"))
    }
