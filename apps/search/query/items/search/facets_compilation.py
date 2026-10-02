from typing import Dict, List

from rdflib.term import Node

from search.api_models.api_models import Facet, FacetCategory, FacetItem
from search.query.items.facets.existing_facet_items_in_database import (
    get_existing_facet_items_in_text_search_for_facet,
)
from search.query.items.facets.facet_objects import DISCIPLINE_FACET, FacetObject


def compile_facets_for_text_search(
    text_query: str, active_facets: Dict[FacetObject, List[Node]], facets: List[FacetObject]
) -> List[Facet]:
    return [_compile_facet_for_text_search(text_query, active_facets, facet) for facet in facets]


def _compile_facet_for_text_search(
    text_query: str, active_facets: Dict[FacetObject, List[Node]], facet: FacetObject
) -> Facet:
    found_facet_items = get_existing_facet_items_in_text_search_for_facet(
        text_query, active_facets, facet
    )
    active_facet_items = active_facets.get(facet, [])

    facet_state: Dict[Node, bool] = {facet: True for facet in active_facet_items}
    for facet_item in found_facet_items:
        if facet_item not in facet_state:
            facet_state[facet_item] = False

    facet_items_sorted = [
        FacetItem(label=item_label, value=str(item_key), active=facet_state.get(item_key, False))
        for item_key, item_label in facet.items.items()
    ]

    # For DISCIPLINE_FACET: attach any active sub-discipline as a child of its
    # top-level ancestor so the sidebar can show it highlighted.
    if facet is DISCIPLINE_FACET:
        top_level_uris = {str(k) for k in facet.items.keys()}
        from curation.models import Discipline as DisciplineModel

        for active_node in active_facet_items:
            active_uri = str(active_node)
            if active_uri in top_level_uris:
                continue  # already a top-level item, no child needed
            # Walk up parent chain to find the top-level ancestor
            try:
                disc = DisciplineModel.objects.get(uri=active_uri)
                root = disc
                for _ in range(5):
                    if root.parent_id_id is None:
                        break
                    root = DisciplineModel.objects.get(pk=root.parent_id_id)
                root_uri = root.uri
            except DisciplineModel.DoesNotExist:
                continue
            # Attach sub-discipline as child of the matching top-level FacetItem
            for fi in facet_items_sorted:
                if fi.value == root_uri:
                    if fi.children is None:
                        fi.children = []
                    fi.children.append(FacetItem(label=disc.label, value=active_uri, active=True))
                    break

    result_facet = Facet()
    result_facet.facetCategory = FacetCategory(label=facet.label, name=str(facet.key))
    result_facet.facetItems = facet_items_sorted

    return result_facet
