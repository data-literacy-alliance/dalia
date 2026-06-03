from typing import Collection, Dict, List

from rdflib import DCTERMS, URIRef
from rdflib.term import Node

from search.query.items.metadata.one_to_many_metadata import get_one_to_many_metadata_for_resources
from search.query.labels.label_service import VAR_ITEM, VAR_LABEL, get_labels_for_item_uris
from search.query.utils import Dataset, filter_by_lang
from search.rdf.namespace import SKOS_last_call

_LABEL_GRAPH_PATTERN = (
    (VAR_ITEM, SKOS_last_call.prefLabel, VAR_LABEL),
    filter_by_lang(VAR_LABEL),
)


def _map_language_uris_to_string_label(items: Collection[Node]) -> Dict[Node, str]:
    mapping = get_labels_for_item_uris(items, Dataset.ONTOLOGIES, _LABEL_GRAPH_PATTERN)
    # print(f"DEBUG (languages.py): _map_language_uris_to_string_label mapping: {mapping}") # ADD THIS LINE
    return mapping


def get_languages_for_resources(resource_uri_refs: List[URIRef]) -> Dict[URIRef, List[str]]:
    """
    Retrieve the languages for each of the given learning resource URIRefs.

    :param resource_uri_refs: List of learning resource URIRefs
    :return: Associations between the learning resource URIRefs and their respective list of languages.
    """
    # print(f"DEBUG (languages.py): get_languages_for_resources called with resource_uri_refs: {resource_uri_refs}")  # ADD THIS LINE
    return get_one_to_many_metadata_for_resources(
        resource_uri_refs=resource_uri_refs,
        relation=DCTERMS.language,
        items_mapping_fn=_map_language_uris_to_string_label,
    )
