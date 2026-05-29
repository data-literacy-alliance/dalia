from typing import Collection, Dict

from rdflib import URIRef, Variable

from search.query.utils import Dataset, query_dataset
from search.query_builder.query_builder import OPTIONAL, QueryBuilder, VALUES

VAR_ITEM = Variable("item")
VAR_LABEL = Variable("label")


def prepare_query_for_labels_from_items(items: Collection[URIRef], graph_pattern: tuple, order_by) -> str:
    items_uri_ref_blocks = [[uri_ref] for uri_ref in items]

    return QueryBuilder().SELECT(
        VAR_ITEM,
        VAR_LABEL
    ).WHERE(
        VALUES(
            [VAR_ITEM],
            items_uri_ref_blocks
        ),
        OPTIONAL(
            *graph_pattern
        )
    ).ORDER_BY(
        order_by
    ).build()


def _process_results(results) -> Dict[URIRef, str]:
    mapping = {}
#    print("Raw Query Results:\n", results) # DEBUG
    for result in results:
        mapping[result.item] = str(result.label) if result.label else "Unknown label"
    return mapping


def get_labels_for_item_uris(
        items: Collection[URIRef],
        dataset: Dataset,
        graph_pattern: tuple,
        order_by=VAR_LABEL
) -> Dict[URIRef, str]:
    """
    Retrieves the labels for the given items. Typically, these items should belong to the same category.

    :param items: URIRefs of the items
    :param dataset: The dataset to execute the SPARQL query on.
    :param graph_pattern: Graph pattern to match an item to its label via a SPARQL query. Use the variables VAR_ITEM and
                          VAR_LABEL as query variables.
    :param order_by: Ordering comparator to be used in the SPARQL query. Default: Lexicographic order by label.
    :return: Associations between the item URIRefs and their respective label. The insertion order of this dictionary
             reflects the specified order.
    """
    query = prepare_query_for_labels_from_items(items, graph_pattern, order_by)
#    print("Generated SPARQL Query:\n", query) #DEBUG
    results = query_dataset(dataset, query)
    return _process_results(results)
