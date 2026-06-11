from typing import Dict, List

from rdflib import URIRef
from rdflib.term import Node

from search.api_models.api_models import SelectedFacet
from search.query.items.facets.facet_objects import FacetObject


def extract_active_facets_from_selected_facets(
    selected_facets: List[SelectedFacet], facets_to_match_mapped_by_key: Dict[URIRef, FacetObject]
) -> Dict[FacetObject, List[Node]]:
    active_facets = {}
    for selected_facet in selected_facets:
        if target_facet := facets_to_match_mapped_by_key.get(URIRef(selected_facet.key)):
            active_facet_items = _extract_active_facet_items_from_selected_facet(
                selected_facet, target_facet
            )
            if active_facet_items:
                active_facets[target_facet] = active_facet_items

    return active_facets


def _extract_active_facet_items_from_selected_facet(
    selected_facet: SelectedFacet, target_facet: FacetObject
) -> List[Node]:
    # selected_nodes = []
    # for selected_facet_item in selected_facet.selected:
    #     selected_facet_item_as_node = target_facet.selected_facet_initializer(selected_facet_item)
    #     if selected_facet_item_as_node in target_facet.items:
    #         selected_nodes.append(selected_facet_item_as_node)
    #
    # return selected_nodes

    # equivalent to the explicit for loop
    return [
        selected_facet_item_as_node
        for selected_facet_item in selected_facet.selected
        if (
            selected_facet_item_as_node := target_facet.selected_facet_initializer(
                selected_facet_item
            )
        )
        in target_facet.items
    ]
