from typing import Dict, List

from rdflib import URIRef
from rdflib.term import Node

from search.api_models.api_models import SelectedFacet
from search.query.items.facets.facet_objects import COMMUNITY_FACET, DISCIPLINE_FACET, FacetObject


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
    if target_facet is COMMUNITY_FACET or target_facet is DISCIPLINE_FACET:
        # Community: accept any valid URIRef (no expansion needed).
        if target_facet is COMMUNITY_FACET:
            return [
                node
                for item in selected_facet.selected
                if (node := target_facet.selected_facet_initializer(item))
            ]
        # Discipline: expand selected URI to include all descendant sub-disciplines.
        # This ensures clicking a parent discipline (or any ancestor) includes all children.
        from curation.models import Discipline as DisciplineModel

        nodes = []
        visited: set = set()

        def _expand(uri: str) -> None:
            if uri in visited:
                return
            visited.add(uri)
            node = target_facet.selected_facet_initializer(uri)
            if node:
                nodes.append(node)
            # Include direct children recursively (depth-first, guards cycles via visited)
            for child_uri in DisciplineModel.objects.filter(
                parent_id__uri=uri, is_active=True
            ).values_list("uri", flat=True):
                if child_uri:
                    _expand(child_uri)

        for item in selected_facet.selected:
            _expand(item)
        return nodes

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
