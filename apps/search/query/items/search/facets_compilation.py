from typing import Dict, List

from rdflib.term import Node

from search.api_models.api_models import Facet, FacetCategory, FacetItem
from search.query.items.facets.existing_facet_items_in_database import (
    get_existing_facet_items_in_text_search_for_facet,
)
from search.query.items.facets.facet_objects import FacetObject


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

    result_facet = Facet()
    result_facet.facetCategory = FacetCategory(label=facet.label, name=str(facet.key))
    result_facet.facetItems = facet_items_sorted

    return result_facet
