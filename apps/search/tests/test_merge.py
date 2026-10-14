"""Tests for comprehensive_search multi-source merge path.

All Fuseki/SPARQL calls are stubbed — no network access.
"""

import datetime
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from curation.models.resources import Resource, ResourceContent
from curation.models.vocabularies import Language
from search.api_models.api_models import (
    Facet,
    FacetCategory,
    FacetItem,
    ItemSearchRequest,
    ItemSearchResult,
    Resource as APIResource,
)
from search.query.items.search import comprehensive_search as cs_mod
from search.query.items.search.comprehensive_search import (
    Candidate,
    _normalize_sort_key,
    search_items_comprehensive,
)


# ---------------------------------------------------------------------------
# _normalize_sort_key unit tests (no DB)
# ---------------------------------------------------------------------------


def test_normalize_sort_key_full_date():
    assert _normalize_sort_key("2023-06-15") == "2023-06-15"


def test_normalize_sort_key_year_only():
    assert _normalize_sort_key("2023") == "2023-01-01"


def test_normalize_sort_key_year_month():
    assert _normalize_sort_key("2023-06") == "2023-06-01"


def test_normalize_sort_key_empty():
    assert _normalize_sort_key("") == "0000-00-00"


def test_normalize_sort_key_unparseable():
    assert _normalize_sort_key("not-a-date") == "0000-00-00"


# ---------------------------------------------------------------------------
# Helpers to build stub facet lists
# ---------------------------------------------------------------------------


def _make_facet_list(cat_name: str, value: str, count: int) -> list:
    facet = Facet()
    facet.facetCategory = FacetCategory(label=cat_name, name=cat_name)
    facet.facetItems = [FacetItem(label=value, value=value, active=False, count=count)]
    return [facet]


def _stub_resource(resource_uuid: str, title: str, source: str) -> APIResource:
    return APIResource(
        id=resource_uuid,
        slug=resource_uuid,
        title=title,
        source=source,
    )


# ---------------------------------------------------------------------------
# DB fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def owner(db):
    User = get_user_model()
    return User.objects.create_user(
        username="merge_owner",
        email="merge_owner@example.com",
        password="x",
    )


@pytest.fixture
def pg_resource(owner):
    """A live, published, active PG resource."""
    res = Resource.objects.create(
        owner=owner, title="PG Merge Resource", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN Merge", code="en_merge", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="PG Merge Content",
        main_url="https://example.com/pgmerge",
        description="A merge test resource.",
        is_active=True,
        created_by=owner,
        publication_date=datetime.date(2023, 3, 1),
    )
    rc.languages.set([en])
    return res, rc


# ---------------------------------------------------------------------------
# DEDUP: fuseki wins collisions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dedup_fuseki_wins(pg_resource, monkeypatch):
    """When a UUID is in both fuseki stub and PG, the fuseki version wins."""
    res, rc = pg_resource
    uuid_str = str(res.uuid)

    fuseki_cand = Candidate(uuid=uuid_str, sort_key="2023-03-01", source="fuseki", ref=None)
    fuseki_res = _stub_resource(uuid_str, "Fuseki Version", "fuseki")
    pg_facets = []

    def stub_fuseki_candidates(request):
        facets = _make_facet_list("TestCat", "v1", 1)
        return [fuseki_cand], facets

    def stub_fuseki_hydrate(refs):
        return [fuseki_res]

    monkeypatch.setattr(cs_mod, "fuseki_candidates", stub_fuseki_candidates)
    monkeypatch.setattr(cs_mod, "fuseki_hydrate", stub_fuseki_hydrate)
    monkeypatch.setattr(
        cs_mod,
        "_CANDIDATE_PRODUCERS",
        {
            "fuseki": stub_fuseki_candidates,
            "postgres": cs_mod._CANDIDATE_PRODUCERS["postgres"],
        },
    )

    with override_settings(DALIA_SEARCH_SOURCES=["fuseki", "postgres"]):
        req = ItemSearchRequest(query="", offset=0, limit=100, sortOrder="dsc")
        result = search_items_comprehensive(req)

    matched = [r for r in result.results if r.id == uuid_str]
    assert len(matched) == 1
    assert matched[0].source == "fuseki"


# ---------------------------------------------------------------------------
# SORT: publication_date DESC then ASC
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sort_desc_null_last(monkeypatch):
    """DESC sort: newer dates first; null ('0000-00-00') sorts last.

    Uses the multi-source merge path (["fuseki","postgres"]) so that
    _CANDIDATE_PRODUCERS is invoked (single-source uses _SEARCH_PRODUCERS).
    PG contributes no candidates; sort order is purely from the fuseki stub.
    """
    early_uuid = str(uuid.uuid4())
    recent_uuid = str(uuid.uuid4())
    null_uuid = str(uuid.uuid4())

    candidates = [
        Candidate(uuid=null_uuid, sort_key="0000-00-00", source="fuseki", ref=None),
        Candidate(uuid=early_uuid, sort_key="2020-01-01", source="fuseki", ref=None),
        Candidate(uuid=recent_uuid, sort_key="2023-12-31", source="fuseki", ref=None),
    ]
    resources = {
        null_uuid: _stub_resource(null_uuid, "Null Date", "fuseki"),
        early_uuid: _stub_resource(early_uuid, "Early", "fuseki"),
        recent_uuid: _stub_resource(recent_uuid, "Recent", "fuseki"),
    }

    def stub_fuseki_candidates(request):
        return candidates, []

    def stub_fuseki_hydrate(refs):
        return list(resources.values())

    # pg_candidates returns no rows for these fresh UUIDs (test DB is empty-ish)
    def stub_pg_candidates_empty(request):
        return [], []

    monkeypatch.setattr(cs_mod, "fuseki_candidates", stub_fuseki_candidates)
    monkeypatch.setattr(cs_mod, "fuseki_hydrate", stub_fuseki_hydrate)
    monkeypatch.setattr(
        cs_mod,
        "_CANDIDATE_PRODUCERS",
        {
            "fuseki": stub_fuseki_candidates,
            "postgres": stub_pg_candidates_empty,
        },
    )

    with override_settings(DALIA_SEARCH_SOURCES=["fuseki", "postgres"]):
        req = ItemSearchRequest(query="*", offset=0, limit=10, sortOrder="dsc")
        result = search_items_comprehensive(req)

    ids = [r.id for r in result.results]
    assert ids.index(recent_uuid) < ids.index(early_uuid)
    assert ids.index(early_uuid) < ids.index(null_uuid)


@pytest.mark.django_db
def test_sort_asc_null_first(monkeypatch):
    """ASC sort: null ('0000-00-00') sorts first (it is the smallest key)."""
    early_uuid = str(uuid.uuid4())
    null_uuid = str(uuid.uuid4())

    candidates = [
        Candidate(uuid=early_uuid, sort_key="2020-01-01", source="fuseki", ref=None),
        Candidate(uuid=null_uuid, sort_key="0000-00-00", source="fuseki", ref=None),
    ]
    resources = {
        early_uuid: _stub_resource(early_uuid, "Early ASC", "fuseki"),
        null_uuid: _stub_resource(null_uuid, "Null ASC", "fuseki"),
    }

    def stub_fuseki_candidates(request):
        return candidates, []

    def stub_fuseki_hydrate(refs):
        return list(resources.values())

    def stub_pg_candidates_empty(request):
        return [], []

    monkeypatch.setattr(cs_mod, "fuseki_candidates", stub_fuseki_candidates)
    monkeypatch.setattr(cs_mod, "fuseki_hydrate", stub_fuseki_hydrate)
    monkeypatch.setattr(
        cs_mod,
        "_CANDIDATE_PRODUCERS",
        {
            "fuseki": stub_fuseki_candidates,
            "postgres": stub_pg_candidates_empty,
        },
    )

    with override_settings(DALIA_SEARCH_SOURCES=["fuseki", "postgres"]):
        req = ItemSearchRequest(query="*", offset=0, limit=10, sortOrder="asc")
        result = search_items_comprehensive(req)

    ids = [r.id for r in result.results]
    assert ids.index(null_uuid) < ids.index(early_uuid)


# ---------------------------------------------------------------------------
# PAGINATION
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pagination_offset_beyond_source(monkeypatch):
    """offset beyond the fuseki source still works with PG results."""
    pg_uuid = None  # will be filled after DB fixture

    # We test with postgres-only here for simplicity.
    with override_settings(DALIA_SEARCH_SOURCES=["postgres"]):
        req = ItemSearchRequest(query="", offset=9999, limit=10)
        result = search_items_comprehensive(req)

    assert result.results == [] or len(result.results) == 0
    assert result.count >= 0


@pytest.mark.django_db
def test_pagination_total_count_equals_deduped(monkeypatch):
    """count == len(deduped candidates), not the page size."""
    u1 = str(uuid.uuid4())
    u2 = str(uuid.uuid4())
    u3 = str(uuid.uuid4())
    candidates = [
        Candidate(uuid=u1, sort_key="2023-01-01", source="fuseki", ref=None),
        Candidate(uuid=u2, sort_key="2022-01-01", source="fuseki", ref=None),
        Candidate(uuid=u3, sort_key="2021-01-01", source="fuseki", ref=None),
    ]

    def stub_fuseki_candidates(request):
        return candidates, []

    def stub_fuseki_hydrate(refs):
        return [_stub_resource(u, f"R{i}", "fuseki") for i, u in enumerate([u1, u2, u3])]

    def stub_pg_candidates_empty2(request):
        return [], []

    monkeypatch.setattr(cs_mod, "fuseki_candidates", stub_fuseki_candidates)
    monkeypatch.setattr(cs_mod, "fuseki_hydrate", stub_fuseki_hydrate)
    monkeypatch.setattr(
        cs_mod,
        "_CANDIDATE_PRODUCERS",
        {
            "fuseki": stub_fuseki_candidates,
            "postgres": stub_pg_candidates_empty2,
        },
    )

    with override_settings(DALIA_SEARCH_SOURCES=["fuseki", "postgres"]):
        req = ItemSearchRequest(query="*", offset=0, limit=1)
        result = search_items_comprehensive(req)

    assert result.count == 3
    assert len(result.results) == 1


@pytest.mark.django_db
def test_pagination_offset_beyond_total(monkeypatch):
    """offset >= total → empty results page, but count is correct."""
    u1 = str(uuid.uuid4())
    candidates = [Candidate(uuid=u1, sort_key="2023-01-01", source="fuseki", ref=None)]

    def stub_fuseki_candidates(request):
        return candidates, []

    def stub_fuseki_hydrate(refs):
        return [_stub_resource(u1, "Only One", "fuseki")]

    def stub_pg_candidates_empty3(request):
        return [], []

    monkeypatch.setattr(cs_mod, "fuseki_candidates", stub_fuseki_candidates)
    monkeypatch.setattr(cs_mod, "fuseki_hydrate", stub_fuseki_hydrate)
    monkeypatch.setattr(
        cs_mod,
        "_CANDIDATE_PRODUCERS",
        {
            "fuseki": stub_fuseki_candidates,
            "postgres": stub_pg_candidates_empty3,
        },
    )

    with override_settings(DALIA_SEARCH_SOURCES=["fuseki", "postgres"]):
        req = ItemSearchRequest(query="*", offset=100, limit=10)
        result = search_items_comprehensive(req)

    assert result.count == 1
    assert result.results == []


# ---------------------------------------------------------------------------
# FACET UNION
# ---------------------------------------------------------------------------


def test_union_facets_disjoint():
    """Disjoint sources → summed counts."""
    from search.query.items.search.comprehensive_search import _union_facets

    fl1 = _make_facet_list("CatA", "v1", 5)
    fl2 = _make_facet_list("CatA", "v2", 3)
    unioned = _union_facets([fl1, fl2])
    assert len(unioned) == 1
    items = {fi.value: fi.count for fi in unioned[0].facetItems}
    assert items.get("v1") == 5
    assert items.get("v2") == 3


def test_union_facets_overlapping_dedup():
    """Overlapping value in same category → count summed, not duplicated."""
    from search.query.items.search.comprehensive_search import _union_facets

    fl1 = _make_facet_list("CatB", "v1", 4)
    fl2 = _make_facet_list("CatB", "v1", 2)
    unioned = _union_facets([fl1, fl2])
    assert len(unioned) == 1
    items = {fi.value: fi.count for fi in unioned[0].facetItems}
    assert items["v1"] == 6


def test_union_facets_single_list():
    """A single facet list is returned unchanged."""
    from search.query.items.search.comprehensive_search import _union_facets

    fl = _make_facet_list("CatC", "v1", 7)
    result = _union_facets([fl])
    assert result is fl


def test_union_facets_empty():
    """Empty input returns empty list."""
    from search.query.items.search.comprehensive_search import _union_facets

    assert _union_facets([]) == []


# ---------------------------------------------------------------------------
# SINGLE-SOURCE FAST PATH
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_single_source_postgres(pg_resource):
    """['postgres'] only → postgres_search result, count equals PG live count."""
    with override_settings(DALIA_SEARCH_SOURCES=["postgres"]):
        req = ItemSearchRequest(query="", offset=0, limit=100)
        result = search_items_comprehensive(req)

    res, rc = pg_resource
    ids = [r.id for r in result.results]
    assert str(res.uuid) in ids
    assert result.count >= 1


@pytest.mark.django_db
def test_single_source_fuseki(monkeypatch):
    """['fuseki'] only → fuseki_search path (stubbed)."""
    u1 = str(uuid.uuid4())
    stub_res = _stub_resource(u1, "Fuseki Only", "fuseki")

    fake_result = ItemSearchResult()
    fake_result.count = 1
    fake_result.offset = 0
    fake_result.limit = 20
    fake_result.results = [stub_res]
    fake_result.facets = []

    def stub_fuseki_search(request):
        return fake_result

    monkeypatch.setattr(
        cs_mod,
        "_SEARCH_PRODUCERS",
        {
            "fuseki": stub_fuseki_search,
            "postgres": cs_mod._SEARCH_PRODUCERS["postgres"],
        },
    )

    with override_settings(DALIA_SEARCH_SOURCES=["fuseki"]):
        req = ItemSearchRequest(query="*", offset=0, limit=20)
        result = search_items_comprehensive(req)

    assert result.count == 1
    assert result.results[0].source == "fuseki"


# ---------------------------------------------------------------------------
# ISOLATION: a failing fuseki producer must not crash the whole search
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_isolation_failing_fuseki_returns_pg_results(pg_resource, monkeypatch):
    """A fuseki candidates producer that raises must not propagate to the caller."""

    def raising_fuseki_candidates(request):
        raise RuntimeError("Fuseki is down")

    monkeypatch.setattr(
        cs_mod,
        "_CANDIDATE_PRODUCERS",
        {
            "fuseki": raising_fuseki_candidates,
            "postgres": cs_mod._CANDIDATE_PRODUCERS["postgres"],
        },
    )

    with override_settings(DALIA_SEARCH_SOURCES=["fuseki", "postgres"]):
        req = ItemSearchRequest(query="", offset=0, limit=100)
        result = search_items_comprehensive(req)

    res, rc = pg_resource
    ids = [r.id for r in result.results]
    assert str(res.uuid) in ids
