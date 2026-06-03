from typing import Dict, List

from rdflib import DCTERMS, RDF, URIRef, Variable

from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import GROUP_CONCAT, QueryBuilder, VALUES
from search.rdf.namespace import educor

_VARIABLES = {"lr": Variable("lr"), "formats": Variable("formats")}


def prepare_query_for_format_metadata_for_resources(resource_uri_refs: List[URIRef]) -> str:
    var_lr = _VARIABLES["lr"]
    var_format = Variable("format")

    resource_uri_ref_blocks = [[uri_ref] for uri_ref in resource_uri_refs]

    return (
        QueryBuilder()
        .SELECT(var_lr, **{_VARIABLES["formats"]: GROUP_CONCAT(var_format, separator=", ")})
        .WHERE(
            VALUES([var_lr], resource_uri_ref_blocks),
            (var_lr, RDF.type, educor.EducationalResource),
            (var_lr, DCTERMS.format, var_format),
        )
        .GROUP_BY(var_lr)
        .build()
    )


def format_from_result(result) -> str:
    return str(result.formats) if result.formats else None


def get_format_metadata_for_resources(resource_uri_refs: List[URIRef]) -> Dict[URIRef, str]:
    """
    Retrieve the format metadata for each of the given learning resource URIRefs.

    :param resource_uri_refs: List of learning resource URIRefs
    :return: Associations between the learning resource URIRefs and their respective format.
    """
    query = prepare_query_for_format_metadata_for_resources(resource_uri_refs)

    results = query_dalia_dataset(query)
    return {result.lr: format_from_result(result) for result in results}
