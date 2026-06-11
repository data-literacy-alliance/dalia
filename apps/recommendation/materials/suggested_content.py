"""
Suggested content retrieval based on SPARQL queries.

This module implements a recommendation algorithm that suggests learning resources
based on multiple criteria:
1. Resources that are part of the same collection (isPartOf relationship)
2. Resources that are based on the same source (isBasedOn relationship)
3. Related resources (isRelatedTo relationship)
4. Resources by the same authors (matching ORCID IDs)
5. Resources with shared keywords (2+ in common)
6. Resources in the same discipline

The algorithm ranks suggestions in the order listed above, returning up to 6
recommended resources.

MIGRATION NOTE (Phase 3):
✅ Updated to use apps.search structure after legacy dalia app migration.
All SPARQL utilities, query builders, and RDF namespaces now imported from search.
"""

from typing import Set
from uuid import UUID

from rdflib import URIRef, Variable

# Phase 3: Updated to use apps.search structure
from search.query.items.metadata.items import get_metadata_for_learning_resources
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import QueryBuilder
from search.rdf.dalia_kb import _LEARNING_RESOURCE_BASE_URI
from search.rdf.namespace import SCHEMA, MoDalia, fabio

from ..api_models.api_models import SuggestedContents


def _get_shared_keywords(uuid: UUID):
    query = f"""
        PREFIX schema: <https://schema.org/>
        SELECT ?sub (COUNT(?sharedKeyword) AS ?keywordCount) WHERE {{
            <{_LEARNING_RESOURCE_BASE_URI}{uuid}> schema:keywords ?sharedKeyword .
            ?sub schema:keywords ?sharedKeyword .
            FILTER(?sub != <{_LEARNING_RESOURCE_BASE_URI}{uuid}>)
        }}
        GROUP BY ?sub
        HAVING(?keywordCount >= 2)
        """

    results = query_dalia_dataset(query)
    return [result[0] for result in results]


def _get_is_part_of(uuid: UUID):
    var_material = Variable("material")
    query = (
        QueryBuilder()
        .SELECT(var_material)
        .WHERE(
            (
                URIRef(f"{_LEARNING_RESOURCE_BASE_URI}{uuid}"),
                URIRef(URIRef(SCHEMA.NS + "isPartOf")),
                var_material,
            )
        )
        .build()
    )
    results = query_dalia_dataset(query)
    return [result[0] for result in results]


def _get_is_related_to(uuid: UUID):
    var_material = Variable("material")
    query = (
        QueryBuilder()
        .SELECT(var_material)
        .WHERE(
            (
                URIRef(f"{_LEARNING_RESOURCE_BASE_URI}{uuid}"),
                URIRef(URIRef(MoDalia.NS + "isRelatedTo")),
                var_material,
            )
        )
        .build()
    )
    results = query_dalia_dataset(query)
    return [result[0] for result in results]


def _get_is_based_on(uuid: UUID):
    var_material = Variable("material")
    query = (
        QueryBuilder()
        .SELECT(var_material)
        .WHERE(
            (
                URIRef(f"{_LEARNING_RESOURCE_BASE_URI}{uuid}"),
                URIRef(URIRef(MoDalia.NS + "isBasedOn")),
                var_material,
            )
        )
        .build()
    )
    results = query_dalia_dataset(query)
    return [result[0] for result in results]


def _get_authors(uuid: UUID):
    query = f"""
        PREFIX arq: <http://jena.apache.org/ARQ/list#>
        PREFIX schema: <https://schema.org/>
        PREFIX m4i: <http://w3id.org/nfdi4ing/metadata4ing#>

        SELECT DISTINCT ?lr WHERE {{
            <{_LEARNING_RESOURCE_BASE_URI}{uuid}> schema:author ?list.
            ?list arq:member ?member.
            ?member a ?type.
	        ?member m4i:orcidId ?id.
            ?lr schema:author ?newlist.
            ?newlist arq:member ?newmember.
            ?newmember m4i:orcidId ?id.
            FILTER(?lr != <{_LEARNING_RESOURCE_BASE_URI}{uuid}>)
            FILTER(?type = schema:Person)
        }}
    LIMIT 10"""
    results = query_dalia_dataset(query)
    return [result[0] for result in results]


def _get_same_discipline(uuid: UUID):
    var_material = Variable("material")
    var_discipline = Variable("discipline")
    query = (
        QueryBuilder()
        .SELECT(var_material)
        .WHERE(
            (
                URIRef(f"{_LEARNING_RESOURCE_BASE_URI}{uuid}"),
                URIRef(URIRef(fabio.NS + "hasDiscipline")),
                var_discipline,
            ),
            (
                var_material,
                URIRef(URIRef(fabio.NS + "hasDiscipline")),
                var_discipline,
            ),
        )
        .build()
    )
    results = query_dalia_dataset(query)
    return [result[0] for result in results]


RANKING = (
    _get_is_part_of,
    _get_is_based_on,
    _get_is_related_to,
    _get_authors,
    _get_shared_keywords,
    _get_same_discipline,
)


def get_suggested_contents_id(uuid: UUID) -> Set:
    number_of_materials = 6
    results = set()
    for i in range(len(RANKING)):
        for result in RANKING[i](uuid):
            if _LEARNING_RESOURCE_BASE_URI == result[: len(_LEARNING_RESOURCE_BASE_URI)]:
                results.add(result)
            if len(results) == number_of_materials:
                return results

    return results


def get_suggested_contents(uuid: UUID) -> SuggestedContents:
    ids = get_suggested_contents_id(uuid)
    return SuggestedContents(get_metadata_for_learning_resources(list(ids)))
