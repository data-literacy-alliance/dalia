from typing import Collection, Dict, List

from rdflib import SKOS, URIRef
from rdflib.term import Node

from search.api_models.api_models import LabelValueItem
from search.query.items.metadata.one_to_many_metadata import get_one_to_many_metadata_for_resources
from search.query.labels.label_service import VAR_ITEM, VAR_LABEL, get_labels_for_item_uris
from search.query.labels.utils import remap_to_label_value_item
from search.query.utils import Dataset, filter_by_lang
from search.rdf.namespace import MoDalia

_LABEL_GRAPH_PATTERN = (
    (VAR_ITEM, SKOS.prefLabel, VAR_LABEL),
    filter_by_lang(VAR_LABEL),
)


def _map_target_group_uris_to_label_value_items(items: Collection[Node]) -> Dict[Node, LabelValueItem]:
    mapping = get_labels_for_item_uris(items, Dataset.ONTOLOGIES, _LABEL_GRAPH_PATTERN)

    return remap_to_label_value_item(mapping)


def get_target_groups_for_resources(resource_uri_refs: List[URIRef]) -> Dict[URIRef, List[LabelValueItem]]:
    """
    Retrieve the target groups for each of the given learning resource URIRefs.

    :param resource_uri_refs: List of learning resource URIRefs
    :return: Associations between the learning resource URIRefs and their respective list of target groups.
    """
    return get_one_to_many_metadata_for_resources(
        resource_uri_refs=resource_uri_refs,
        relation=MoDalia.hasTargetGroup,
        items_mapping_fn=_map_target_group_uris_to_label_value_items
    )
