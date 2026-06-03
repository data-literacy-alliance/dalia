from typing import Collection, Dict, List

from rdflib import RDFS, URIRef
from rdflib.term import Node, Variable

from search.api_models.api_models import LabelValueItem
from search.query.items.metadata.one_to_many_metadata import get_one_to_many_metadata_for_resources
from search.query.labels.label_service import VAR_ITEM, VAR_LABEL, get_labels_for_item_uris
from search.query.labels.utils import remap_to_label_value_item
from search.query.utils import Dataset, filter_by_lang
from search.rdf.namespace import MoDalia

_VAR_LEVEL_ORDER = Variable("levelOrder")

_LABEL_GRAPH_PATTERN = (
    (VAR_ITEM, RDFS.label, VAR_LABEL),
    (VAR_ITEM, MoDalia.hasOrder, _VAR_LEVEL_ORDER),
    filter_by_lang(VAR_LABEL),
)


def _map_proficiency_level_uris_to_label_value_items(
    items: Collection[Node],
) -> Dict[Node, LabelValueItem]:
    mapping = get_labels_for_item_uris(
        items, Dataset.ONTOLOGIES, _LABEL_GRAPH_PATTERN, order_by=_VAR_LEVEL_ORDER
    )

    return remap_to_label_value_item(mapping)


def get_proficiency_levels_for_resources(
    resource_uri_refs: List[URIRef],
) -> Dict[URIRef, List[LabelValueItem]]:
    """
    Retrieve the proficiency levels for each of the given learning resource URIRefs.

    :param resource_uri_refs: List of learning resource URIRefs
    :return: Associations between the learning resource URIRefs and their respective list of proficiency levels.
    """
    return get_one_to_many_metadata_for_resources(
        resource_uri_refs=resource_uri_refs,
        relation=MoDalia.requiresProficiencyLevel,
        items_mapping_fn=_map_proficiency_level_uris_to_label_value_items,
    )
