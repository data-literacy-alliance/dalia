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

from typing import List, Set
from uuid import UUID

from rdflib import URIRef, Variable

# Phase 3: Updated to use apps.search structure
from curation.models.resources import ResourceContent
from search.query.items.metadata.items import get_metadata_for_learning_resources
from search.query.items.search.producers.postgres_producer import postgres_hydrate
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import QueryBuilder
from search.rdf.dalia_kb import _LEARNING_RESOURCE_BASE_URI, lr_uri_ref
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


def get_pg_suggested_contents_id(uuid: UUID) -> Set[str]:
    """Find similar resources in PostgreSQL using shared keywords, disciplines and authors."""
    try:
        rc = (
            ResourceContent.objects.filter(resource__uuid=uuid, is_active=True)
            .select_related("resource")
            .prefetch_related("keywords", "disciplines", "people", "organizations")
            .first()
        )
    except Exception:
        return set()

    if not rc:
        return set()

    results: Set[str] = set()
    number_of_materials = 6

    base_qs = (
        ResourceContent.objects.filter(is_active=True, resource__is_published=True)
        .exclude(resource__uuid=uuid)
        .select_related("resource")
    )

    # 1. Same authors by ORCID
    orcids = [p.orcid for p in rc.people.all() if p.orcid]
    if orcids and len(results) < number_of_materials:
        for similar in base_qs.filter(people__orcid__in=orcids).distinct():
            results.add(str(similar.resource.uuid))
            if len(results) >= number_of_materials:
                return results

    # 2. Shared keywords (2+ in common) — prefetch to avoid N+1
    keyword_names = {k.name for k in rc.keywords.all()}
    if keyword_names and len(results) < number_of_materials:
        candidates = (
            base_qs.filter(keywords__name__in=keyword_names).distinct().prefetch_related("keywords")
        )
        for similar in candidates:
            shared = {k.name for k in similar.keywords.all()} & keyword_names
            if len(shared) >= 2:
                results.add(str(similar.resource.uuid))
                if len(results) >= number_of_materials:
                    return results

    # 3. Same discipline URI
    disc_uris = [d.uri for d in rc.disciplines.all() if d.uri]
    if disc_uris and len(results) < number_of_materials:
        for similar in base_qs.filter(disciplines__uri__in=disc_uris).distinct():
            results.add(str(similar.resource.uuid))
            if len(results) >= number_of_materials:
                return results

    return results


def get_suggested_contents(uuid: UUID) -> SuggestedContents:
    """Merge Fuseki and PG recommendations, hydrate each from its native source."""
    number_of_materials = 6

    # Gather candidates from both sources
    fuseki_uris: Set = get_suggested_contents_id(uuid)
    pg_uuids: Set[str] = get_pg_suggested_contents_id(uuid)

    # Extract UUID strings from Fuseki URIRefs
    fuseki_uuid_strs: Set[str] = {
        str(uri)[len(_LEARNING_RESOURCE_BASE_URI) :]
        for uri in fuseki_uris
        if str(uri).startswith(_LEARNING_RESOURCE_BASE_URI)
    }

    # Merge: PG first (authoritative), then Fuseki extras
    merged: List[str] = list(pg_uuids)
    for fu in fuseki_uuid_strs:
        if fu not in pg_uuids:
            merged.append(fu)
        if len(merged) >= number_of_materials:
            break
    merged = merged[:number_of_materials]

    if not merged:
        return SuggestedContents([])

    # Hydrate PG resources
    pg_hydrated = postgres_hydrate(merged)
    pg_hydrated_uuids = {str(r.id) for r in pg_hydrated}

    # Hydrate remaining from Fuseki
    fuseki_only = [u for u in merged if u not in pg_hydrated_uuids]
    fuseki_resources = []
    if fuseki_only:
        try:
            uri_refs = [lr_uri_ref(UUID(u)) for u in fuseki_only]
            fuseki_resources = get_metadata_for_learning_resources(uri_refs)
        except Exception:
            pass

    return SuggestedContents((pg_hydrated + fuseki_resources)[:number_of_materials])
