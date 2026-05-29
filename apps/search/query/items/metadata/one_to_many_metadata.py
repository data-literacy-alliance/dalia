from collections import defaultdict
from typing import Callable, Collection, Dict, List, Set, TypeVar

from rdflib import RDF, URIRef, Variable
from rdflib.term import Node

from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import QueryBuilder, VALUES
from search.rdf.namespace import educor

_VARIABLES = {
    "lr": Variable("lr"),
    "item": Variable("item")
}


def prepare_query_for_one_to_many_metadata_for_resources(resource_uri_refs: List[URIRef], relation: URIRef) -> str:
    var_lr = _VARIABLES["lr"]

    resource_uri_ref_blocks = [[uri_ref] for uri_ref in resource_uri_refs]

    return QueryBuilder().SELECT(
        *_VARIABLES.values()
    ).WHERE(
        VALUES(
            [var_lr],
            resource_uri_ref_blocks
        ),
        (var_lr, RDF.type, educor.EducationalResource),
        (var_lr, relation, _VARIABLES["item"])
    ).build()


T = TypeVar("T")


def _metadata_from_results(
        results, items_mapping_fn: Callable[[Collection[Node]], Dict[Node, T]]
) -> Dict[URIRef, List[T]]:
    # removes duplicates but preserves order
    distinct_items: List[Node] = list(dict.fromkeys([result.item for result in results]))
    item_mapping: Dict[Node, T] = items_mapping_fn(distinct_items)

    # unsorted collection of metadata items for each learning resource
    lr_metadata_items: Dict[URIRef, Set[Node]] = defaultdict(set)
    for result in results:
        lr_metadata_items[result.lr].add(result.item)

    # sorted list of metadata items according to the sorting of the item_mapping dictionary (insert order) for each
    # learning resource
    return {lr: _collect_sorted_labels(items, item_mapping) for lr, items in lr_metadata_items.items()}


def _collect_sorted_labels(items: Collection[Node], item_mapping: Dict[Node, T]) -> List[T]:
    result = list()
    for node, label in item_mapping.items():
        for item in items:
            if node == item:
                result.append(label)
    return result


def get_one_to_many_metadata_for_resources(
        resource_uri_refs: List[URIRef],
        relation: URIRef,
        items_mapping_fn: Callable[[Collection[Node]], Dict[Node, T]],
) -> Dict[URIRef, List[T]]:
    """
    Retrieve one-to-many metadata of a certain category (relation) for each of the given learning resource URIRefs.

    :param resource_uri_refs: List of learning resource URIRefs
    :param relation: relation between a learning resource and the metadata items (RDF property)
    :param items_mapping_fn: function to generate Python objects from the items received by the SPARQL call (most
           generally RDF nodes)
    :return: Associations between the learning resource URIRefs and their respective list of mapped metadata items.
    """
    query = prepare_query_for_one_to_many_metadata_for_resources(resource_uri_refs, relation)
    results = query_dalia_dataset(query)
    return _metadata_from_results(results, items_mapping_fn)
