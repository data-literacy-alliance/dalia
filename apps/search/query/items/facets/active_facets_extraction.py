from typing import Dict, List

from rdflib import URIRef
from rdflib.term import Node

from search.api_models.api_models import SelectedFacet
from search.query.items.facets.facet_objects import COMMUNITY_FACET, FacetObject


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
    if target_facet is COMMUNITY_FACET:
        # Community filter values are generated dynamically from the database and
        # are not constrained to a fixed items dict — accept any valid URIRef.
        return [
            node
            for item in selected_facet.selected
            if (node := target_facet.selected_facet_initializer(item))
        ]

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
