from typing import Collection, Dict, List

from rdflib import URIRef
from rdflib.term import Node

from search.query.items.metadata.one_to_many_metadata import get_one_to_many_metadata_for_resources
from search.rdf.namespace import SCHEMA


def _map_keyword_literals_to_string(items: Collection[Node]) -> Dict[Node, str]:
    return {item: str(item) for item in items}


def get_keywords_metadata_for_resources(resource_uri_refs: List[URIRef]) -> Dict[URIRef, List[str]]:
    """
    Retrieve the keywords metadata for each of the given learning resource URIRefs.

    :param resource_uri_refs: List of learning resource URIRefs
    :return: Associations between the learning resource URIRefs and their respective list of keywords.
    """
    return get_one_to_many_metadata_for_resources(
        resource_uri_refs=resource_uri_refs,
        relation=SCHEMA.keywords,
        items_mapping_fn=_map_keyword_literals_to_string,
    )
