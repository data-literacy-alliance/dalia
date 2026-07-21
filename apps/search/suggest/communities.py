import concurrent.futures
from typing import List

from django.utils.text import slugify
from rdflib import BNode, DCTERMS, Graph, Literal, RDF, Variable
from rdflib.collection import Collection

from curation.models.communities import Community
from search.api_models.api_models import (
    CurationSuggestPaginatedResult,
    CurationSuggestSearchRequest,
    LabelValueItem,
)
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import Aggregates, FunctionExpressions, QueryBuilder
from search.rdf.namespace import Jena_text, MoDalia


# data for endpoint /curation/suggest/community
def get_communities_suggestions(
    request: CurationSuggestSearchRequest,
) -> CurationSuggestPaginatedResult:
    q = request.q
    limit = request.limit
    offset = request.offset

    # 1. Query PostgreSQL
    pg_qs = Community.objects.filter(title__icontains=q).order_by("title")
    pg_communities = list(pg_qs)

    # Track what's already in PostgreSQL to avoid duplicates from Fuseki
    pg_uris = {c.uri for c in pg_communities if c.uri}
    pg_titles = {c.title for c in pg_communities}

    # 2. Try Fuseki for supplemental results (graceful degradation if Fuseki is down)
    try:
        fuseki_items = _fetch_from_fuseki(q, limit * 2, 0)
    except Exception:
        fuseki_items = []

    # 3. For each Fuseki result not already in PostgreSQL by URI:
    #    - if matched by title (PG record exists without URI), link the Fuseki URI onto it
    #    - otherwise replicate as a new PG record
    for item in fuseki_items:
        fuseki_uri = item.value  # URI string from SPARQL
        label = item.label
        if fuseki_uri in pg_uris:
            continue
        if label in pg_titles:
            # PG record exists but has no URI -- link it to Fuseki now
            for c in pg_communities:
                if c.title == label and not c.uri:
                    Community.objects.filter(pk=c.pk).update(uri=fuseki_uri)
                    c.uri = fuseki_uri
                    pg_uris.add(fuseki_uri)
            continue
        community = _replicate_to_postgres(fuseki_uri, label)
        if community:
            pg_communities.append(community)
            pg_uris.add(community.uri or f"https://id.dalia.education/community/{community.uuid}")
            pg_titles.add(community.title)

    # 4. Sort, count, paginate -- use Fuseki URI as value so detail page resolves correct UUID
    pg_communities.sort(key=lambda c: c.title)
    total = len(pg_communities)
    page = pg_communities[offset : offset + limit]

    return CurationSuggestPaginatedResult(
        count=total,
        offset=offset,
        limit=limit,
        results=[
            LabelValueItem(
                value=c.uri or f"https://id.dalia.education/community/{c.uuid}",
                label=c.title,
            )
            for c in page
        ],
    )


def _replicate_to_postgres(fuseki_uri: str, label: str):
    # Unused here — _enrich_from_fuseki imports these itself. Remove when safe.
    from rdflib import URIRef as _URIRef
    from curation.models.communities import CommunitySocialMedia

    community = Community.objects.filter(uri=fuseki_uri).first()
    if not community:
        community = Community.objects.filter(title=label).first()
        if community:
            if not community.uri:
                Community.objects.filter(pk=community.pk).update(uri=fuseki_uri)
                community.uri = fuseki_uri
        else:
            try:
                community = Community.objects.create(title=label, uri=fuseki_uri)
            except Exception:
                community = (
                    Community.objects.filter(uri=fuseki_uri).first()
                    or Community.objects.filter(title=label).first()
                )

    if community:
        _enrich_from_fuseki(community, fuseki_uri)

    return community


def _enrich_from_fuseki(community, fuseki_uri: str) -> None:
    """Fetch full content from Fuseki and store on the PG community. No-op if already populated."""
    from rdflib import URIRef as _URIRef
    from search.query.communities.one_to_one_metadata import get_one_to_one_metadata_for_communities
    from curation.models.communities import CommunitySocialMedia

    # Only enrich if all content fields are empty (avoid overwriting user-entered data)
    already_enriched = (
        community.description
        or community.website_url
        or community.image
        or community.social_media_links.exists()
    )
    if already_enriched:
        return

    try:
        uri_ref = _URIRef(fuseki_uri)
        metadata_map = get_one_to_one_metadata_for_communities([uri_ref])
        fuseki_data = metadata_map.get(uri_ref)
        if not fuseki_data:
            return

        Community.objects.filter(pk=community.pk).update(
            description=fuseki_data.about or "",
            website_url=fuseki_data.url or "",
            image=fuseki_data.image or None,
        )
        community.description = fuseki_data.about or ""
        community.website_url = fuseki_data.url or ""
        community.image = fuseki_data.image or None

        CommunitySocialMedia.objects.filter(community=community).delete()
        for sm in fuseki_data.social_media or []:
            CommunitySocialMedia.objects.create(community=community, name=sm.name, url=sm.url)
    except Exception:
        pass  # graceful degradation — basic title+uri record is still usable


def _fetch_from_fuseki(q: str, limit: int, offset: int) -> List[LabelValueItem]:
    query = "*" + q + "*"
    sparql_query = prepare_query_for_community_search_and_title_retrieval(query, limit, offset)

    def _run():
        results = query_dalia_dataset(sparql_query)
        return [_process_result_from_metadata_retrieval(result) for result in results]

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run)
        try:
            return future.result(timeout=5)
        except concurrent.futures.TimeoutError:
            raise TimeoutError("Fuseki SPARQL query timed out after 5s")


_VARIABLES = {
    "community": Variable("community"),
    "title": Variable("title"),
}


def _where_for_text_search(query: str, var_community: Variable, var_score: Variable):
    subject_list_for_text_search = Collection(Graph(), BNode(), [var_community, var_score])
    object_list_for_text_search = Collection(Graph(), BNode(), [DCTERMS.title, Literal(query)])

    where = [
        (subject_list_for_text_search, Jena_text.query, object_list_for_text_search),
        (var_community, RDF.type, MoDalia.Community),
    ]

    return tuple(where)


def prepare_query_for_community_search_and_title_retrieval(
    query: str, limit: int, offset: int
) -> str:
    var_community = _VARIABLES["community"]
    var_score = Variable("score")

    return (
        QueryBuilder()
        .SELECT(*_VARIABLES.values())
        .WHERE(
            QueryBuilder()
            .SELECT(var_community, distinct=True)
            .WHERE(*_where_for_text_search(query, var_community, var_score))
            .ORDER_BY(FunctionExpressions.DESC(var_score))
            .LIMIT(limit)
            .OFFSET(offset)
            .build(),
            (var_community, DCTERMS.title, _VARIABLES["title"]),
        )
        .build()
    )


def prepare_query_for_count_in_community_search(query: str) -> str:
    var_community = _VARIABLES["community"]
    var_score = Variable("score")

    return (
        QueryBuilder()
        .SELECT(
            count=Aggregates("COUNT", var_community, ["DISTINCT"]),
        )
        .WHERE(*_where_for_text_search(query, var_community, var_score))
        .build()
    )


def _process_result_from_metadata_retrieval(result) -> LabelValueItem:
    return LabelValueItem(value=str(result.community), label=str(result.title))


def count_results_from_community_search(query: str) -> int:
    sparql_query = prepare_query_for_count_in_community_search(query)
    results = query_dalia_dataset(sparql_query)
    return next(iter(results)).get("count").toPython()
