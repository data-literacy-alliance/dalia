"""Tests for search.query.items.search.producers.postgres_producer."""

import datetime
import uuid

import pytest
from django.contrib.auth import get_user_model

from curation.models.communities import Community
from curation.models.profiles import Organization, Person
from curation.models.relations import (
    RelationType,
    RelationTypeCategory,
    ResourceCommunityRelation,
)
from curation.models.resources import Resource, ResourceContent
from curation.models.vocabularies import (
    Discipline,
    FileFormat,
    Language,
    License,
    LearningResourceType,
    TargetGroup,
)
from search.api_models.api_models import ItemSearchRequest, SelectedFacet
from search.query.items.search.producers.postgres_producer import postgres_search
from search.query.items.facets.facet_objects import (
    DISCIPLINE_FACET,
    LANGUAGE_FACET,
    LICENSE_FACET,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def owner(db):
    User = get_user_model()
    return User.objects.create_user(
        username="testowner_pp",
        email="owner_pp@example.com",
        password="x",
    )


@pytest.fixture
def live_resource(owner):
    """A published, active Resource + ResourceContent pair."""
    res = Resource.objects.create(
        owner=owner,
        title="Live Resource",
        is_published=True,
        is_removed=False,
    )
    en = Language.objects.create(label="English Test Lang", code="en_t", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Live Content",
        main_url="https://example.com/live",
        description="A live resource for testing.",
        is_active=True,
        created_by=owner,
        publication_date=datetime.date(2023, 6, 15),
    )
    rc.languages.set([en])
    return res, rc, en


@pytest.fixture
def relation_type(db):
    cat = RelationTypeCategory.objects.create(name="Test Cat PP")
    return RelationType.objects.create(code="related_pp", label="Related PP", category=cat)


# ---------------------------------------------------------------------------
# Live filter tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_live_filter_includes_published_active(live_resource):
    """A published+active content appears in results."""
    req = ItemSearchRequest(query="", offset=0, limit=20)
    result = postgres_search(req)
    res, rc, _ = live_resource
    ids = [r.id for r in result.results]
    assert str(res.uuid) in ids


@pytest.mark.django_db
def test_live_filter_excludes_unpublished(owner):
    """is_published=False resource is excluded."""
    res = Resource.objects.create(owner=owner, title="Unpub", is_published=False, is_removed=False)
    en = Language.objects.create(label="EN2", code="en2", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Unpub RC",
        main_url="https://example.com/u",
        is_active=True,
        created_by=owner,
    )
    rc.languages.set([en])
    req = ItemSearchRequest(query="", offset=0, limit=100)
    result = postgres_search(req)
    ids = [r.id for r in result.results]
    assert str(res.uuid) not in ids


@pytest.mark.django_db
def test_live_filter_excludes_removed(owner):
    """is_removed=True resource is excluded."""
    res = Resource.objects.create(owner=owner, title="Removed", is_published=True, is_removed=True)
    en = Language.objects.create(label="EN3", code="en3", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Removed RC",
        main_url="https://example.com/r",
        is_active=True,
        created_by=owner,
    )
    rc.languages.set([en])
    req = ItemSearchRequest(query="", offset=0, limit=100)
    result = postgres_search(req)
    ids = [r.id for r in result.results]
    assert str(res.uuid) not in ids


@pytest.mark.django_db
def test_live_filter_excludes_inactive_content(owner):
    """is_active=False content is excluded."""
    res = Resource.objects.create(
        owner=owner, title="Inactive", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN4", code="en4", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Inactive RC",
        main_url="https://example.com/i",
        is_active=True,
        created_by=owner,
    )
    # Force is_active to False via update (bypasses the auto-activate signal
    # which fires on post_save and sets is_active=True for the first RC).
    ResourceContent.objects.filter(pk=rc.pk).update(is_active=False)
    rc.languages.set([en])
    req = ItemSearchRequest(query="", offset=0, limit=100)
    result = postgres_search(req)
    ids = [r.id for r in result.results]
    assert str(res.uuid) not in ids


# ---------------------------------------------------------------------------
# Mapping tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_mapping_id_is_resource_uuid(live_resource):
    """result.id must equal str(resource.uuid), not content.uuid."""
    req = ItemSearchRequest(query="", offset=0, limit=20)
    result = postgres_search(req)
    res, rc, _ = live_resource
    matched = [r for r in result.results if r.id == str(res.uuid)]
    assert len(matched) == 1


@pytest.mark.django_db
def test_mapping_source_is_postgres(live_resource):
    """source field must be 'postgres'."""
    req = ItemSearchRequest(query="", offset=0, limit=20)
    result = postgres_search(req)
    res, rc, _ = live_resource
    matched = next(r for r in result.results if r.id == str(res.uuid))
    assert matched.source == "postgres"


@pytest.mark.django_db
def test_mapping_title_and_description(live_resource):
    """Title and description are mapped correctly."""
    req = ItemSearchRequest(query="", offset=0, limit=20)
    result = postgres_search(req)
    res, rc, _ = live_resource
    matched = next(r for r in result.results if r.id == str(res.uuid))
    assert matched.title == "Live Content"
    assert matched.description == "A live resource for testing."


@pytest.mark.django_db
def test_mapping_publication_date(live_resource):
    """publication_date is mapped as an ISO date string."""
    req = ItemSearchRequest(query="", offset=0, limit=20)
    result = postgres_search(req)
    res, rc, _ = live_resource
    matched = next(r for r in result.results if r.id == str(res.uuid))
    assert matched.publication_date == "2023-06-15"


@pytest.mark.django_db
def test_mapping_person_author(owner):
    """PersonAuthor fields are mapped correctly."""
    res = Resource.objects.create(
        owner=owner, title="Auth Resource", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN Auth", code="en_auth", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Auth Content",
        main_url="https://example.com/auth",
        is_active=True,
        created_by=owner,
    )
    rc.languages.set([en])
    person = Person.objects.create(first_name="Ada", last_name="Lovelace", orcid="", is_active=True)
    rc.people.set([person])

    req = ItemSearchRequest(query="", offset=0, limit=100)
    result = postgres_search(req)
    matched = next(r for r in result.results if r.id == str(res.uuid))
    assert matched.authors is not None
    assert len(matched.authors) >= 1
    from search.api_models.api_models import PersonAuthor

    person_authors = [a for a in matched.authors if isinstance(a, PersonAuthor)]
    assert any(a.firstname == "Ada" and a.lastname == "Lovelace" for a in person_authors)


@pytest.mark.django_db
def test_mapping_org_author(owner):
    """OrganizationAuthor is mapped correctly."""
    res = Resource.objects.create(
        owner=owner, title="Org Resource", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN Org", code="en_org", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Org Content",
        main_url="https://example.com/org",
        is_active=True,
        created_by=owner,
    )
    rc.languages.set([en])
    org = Organization.objects.create(name="Test Org", is_active=True)
    rc.organizations.set([org])

    req = ItemSearchRequest(query="", offset=0, limit=100)
    result = postgres_search(req)
    matched = next(r for r in result.results if r.id == str(res.uuid))
    assert matched.authors is not None
    from search.api_models.api_models import OrganizationAuthor

    org_authors = [a for a in matched.authors if isinstance(a, OrganizationAuthor)]
    assert any(a.name == "Test Org" for a in org_authors)


@pytest.mark.django_db
def test_mapping_language_labels(live_resource):
    """languages list contains language display labels."""
    req = ItemSearchRequest(query="", offset=0, limit=20)
    result = postgres_search(req)
    res, rc, en = live_resource
    matched = next(r for r in result.results if r.id == str(res.uuid))
    assert matched.languages is not None
    assert en.label in matched.languages


@pytest.mark.django_db
def test_mapping_keywords(owner):
    """keywords are mapped to the tags list."""
    res = Resource.objects.create(
        owner=owner, title="Tag Resource", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN Tag", code="en_tag", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Tag Content",
        main_url="https://example.com/tag",
        is_active=True,
        created_by=owner,
    )
    rc.languages.set([en])
    rc.keywords.add("python", "testing")

    req = ItemSearchRequest(query="", offset=0, limit=100)
    result = postgres_search(req)
    matched = next(r for r in result.results if r.id == str(res.uuid))
    assert "python" in matched.tags
    assert "testing" in matched.tags


# ---------------------------------------------------------------------------
# Empty / optional fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_empty_m2m_no_raise(owner):
    """A resource with no authors/keywords/vocabs must map without raising."""
    res = Resource.objects.create(
        owner=owner, title="Empty Resource", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN Empty", code="en_empty", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Empty Content",
        main_url="https://example.com/empty",
        is_active=True,
        created_by=owner,
        publication_date=None,
    )
    rc.languages.set([en])

    req = ItemSearchRequest(query="", offset=0, limit=100)
    result = postgres_search(req)
    ids = [r.id for r in result.results]
    assert str(res.uuid) in ids
    matched = next(r for r in result.results if r.id == str(res.uuid))
    assert matched.publication_date is None


# ---------------------------------------------------------------------------
# Date filters
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_date_after_includes_correct(owner):
    """datePublished_after includes items on or after that date."""
    res = Resource.objects.create(
        owner=owner, title="Date Res", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN Date", code="en_date", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Date Content",
        main_url="https://example.com/date",
        is_active=True,
        created_by=owner,
        publication_date=datetime.date(2022, 1, 1),
    )
    rc.languages.set([en])

    req = ItemSearchRequest(query="", offset=0, limit=100, datePublished_after="2022-01-01")
    result = postgres_search(req)
    ids = [r.id for r in result.results]
    assert str(res.uuid) in ids


@pytest.mark.django_db
def test_date_after_excludes_earlier(owner):
    """datePublished_after excludes items before that date."""
    res = Resource.objects.create(owner=owner, title="Old Res", is_published=True, is_removed=False)
    en = Language.objects.create(label="EN Old", code="en_old", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Old Content",
        main_url="https://example.com/old",
        is_active=True,
        created_by=owner,
        publication_date=datetime.date(2020, 1, 1),
    )
    rc.languages.set([en])

    req = ItemSearchRequest(query="", offset=0, limit=100, datePublished_after="2022-01-01")
    result = postgres_search(req)
    ids = [r.id for r in result.results]
    assert str(res.uuid) not in ids


@pytest.mark.django_db
def test_date_before_includes_correct(owner):
    """datePublished_before includes items on or before that date."""
    res = Resource.objects.create(
        owner=owner, title="Before Res", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN Before", code="en_before", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Before Content",
        main_url="https://example.com/before",
        is_active=True,
        created_by=owner,
        publication_date=datetime.date(2021, 5, 10),
    )
    rc.languages.set([en])

    req = ItemSearchRequest(query="", offset=0, limit=100, datePublished_before="2021-12-31")
    result = postgres_search(req)
    ids = [r.id for r in result.results]
    assert str(res.uuid) in ids


@pytest.mark.django_db
def test_invalid_date_is_ignored(live_resource):
    """An invalid date string is fail-open: all live results are returned."""
    req = ItemSearchRequest(query="", offset=0, limit=100, datePublished_after="not-a-date")
    result = postgres_search(req)
    res, rc, _ = live_resource
    ids = [r.id for r in result.results]
    assert str(res.uuid) in ids


# ---------------------------------------------------------------------------
# Facet filters
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_facet_filter_discipline(owner):
    """Selecting a discipline facet filters to resources with that discipline."""
    known_uri = "https://w3id.org/kim/hochschulfaechersystematik/n4"
    disc = Discipline.objects.create(label="Math Sciences Test", uri=known_uri, is_active=True)

    res_with = Resource.objects.create(
        owner=owner, title="With Disc", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN Disc", code="en_disc", uri="", is_active=True)
    rc_with = ResourceContent.objects.create(
        resource=res_with,
        title="With Disc RC",
        main_url="https://example.com/disc",
        is_active=True,
        created_by=owner,
    )
    rc_with.languages.set([en])
    rc_with.disciplines.set([disc])

    res_without = Resource.objects.create(
        owner=owner, title="Without Disc", is_published=True, is_removed=False
    )
    en2 = Language.objects.create(label="EN Disc2", code="en_disc2", uri="", is_active=True)
    rc_without = ResourceContent.objects.create(
        resource=res_without,
        title="Without Disc RC",
        main_url="https://example.com/nodisc",
        is_active=True,
        created_by=owner,
    )
    rc_without.languages.set([en2])

    facet_key = str(DISCIPLINE_FACET.key)
    req = ItemSearchRequest(
        query="",
        offset=0,
        limit=100,
        selectedFacets=[SelectedFacet(key=facet_key, selected=[known_uri])],
    )
    result = postgres_search(req)
    ids = [r.id for r in result.results]
    assert str(res_with.uuid) in ids
    assert str(res_without.uuid) not in ids


@pytest.mark.django_db
def test_facet_filter_distinct_no_row_multiplication(owner):
    """Filtering by a multi-value M2M facet must not duplicate rows."""
    known_uri_1 = "https://w3id.org/kim/hochschulfaechersystematik/n4"
    known_uri_2 = "https://w3id.org/kim/hochschulfaechersystematik/n1"
    disc1 = Discipline.objects.create(label="Disc Filter 1", uri=known_uri_1, is_active=True)
    disc2 = Discipline.objects.create(label="Disc Filter 2", uri=known_uri_2, is_active=True)

    res = Resource.objects.create(
        owner=owner, title="Multi Disc", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN MDisc", code="en_mdisc", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Multi Disc RC",
        main_url="https://example.com/mdisc",
        is_active=True,
        created_by=owner,
    )
    rc.languages.set([en])
    rc.disciplines.set([disc1, disc2])

    facet_key = str(DISCIPLINE_FACET.key)
    req = ItemSearchRequest(
        query="",
        offset=0,
        limit=100,
        selectedFacets=[SelectedFacet(key=facet_key, selected=[known_uri_1, known_uri_2])],
    )
    result = postgres_search(req)
    # This resource must appear exactly once.
    matching = [r for r in result.results if r.id == str(res.uuid)]
    assert len(matching) == 1


# ---------------------------------------------------------------------------
# Full-text search (search_vector generated column)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fts_match_by_title(owner):
    """A resource whose title contains the search term is returned."""
    res = Resource.objects.create(
        owner=owner, title="FTS Resource", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN FTS", code="en_fts", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Quantum Entanglement Tutorial",
        main_url="https://example.com/quantum",
        description="",
        is_active=True,
        created_by=owner,
    )
    rc.languages.set([en])

    req = ItemSearchRequest(query="quantum", offset=0, limit=100)
    result = postgres_search(req)
    ids = [r.id for r in result.results]
    assert str(res.uuid) in ids


@pytest.mark.django_db
def test_fts_no_match_returns_empty(owner):
    """A search term that matches no content returns zero results for that term."""
    res = Resource.objects.create(
        owner=owner, title="FTS NoMatch", is_published=True, is_removed=False
    )
    en = Language.objects.create(label="EN FTS NM", code="en_fts_nm", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Completely Irrelevant Topic Xyzzy",
        main_url="https://example.com/xyzzy",
        description="",
        is_active=True,
        created_by=owner,
    )
    rc.languages.set([en])

    req = ItemSearchRequest(query="zzz_nomatch_token_99999", offset=0, limit=100)
    result = postgres_search(req)
    assert result.count == 0
    assert result.results == []


@pytest.mark.django_db
def test_fts_browse_all_empty_string(live_resource):
    """Empty query string returns all live results (browse-all mode)."""
    req = ItemSearchRequest(query="", offset=0, limit=100)
    result = postgres_search(req)
    res, rc, _ = live_resource
    ids = [r.id for r in result.results]
    assert str(res.uuid) in ids


@pytest.mark.django_db
def test_fts_browse_all_star(live_resource):
    """'*' query returns all live results (browse-all mode)."""
    req = ItemSearchRequest(query="*", offset=0, limit=100)
    result = postgres_search(req)
    res, rc, _ = live_resource
    ids = [r.id for r in result.results]
    assert str(res.uuid) in ids


@pytest.mark.django_db
def test_fts_browse_all_whitespace(live_resource):
    """Whitespace-only query returns all live results (browse-all mode)."""
    req = ItemSearchRequest(query="   ", offset=0, limit=100)
    result = postgres_search(req)
    res, rc, _ = live_resource
    ids = [r.id for r in result.results]
    assert str(res.uuid) in ids


@pytest.mark.django_db
def test_fts_excludes_non_matching(owner):
    """A term that matches one resource must not return a non-matching resource."""
    res_match = Resource.objects.create(
        owner=owner, title="Match", is_published=True, is_removed=False
    )
    res_no = Resource.objects.create(
        owner=owner, title="NoMatch", is_published=True, is_removed=False
    )
    en1 = Language.objects.create(label="EN FE1", code="en_fe1", uri="", is_active=True)
    en2 = Language.objects.create(label="EN FE2", code="en_fe2", uri="", is_active=True)
    rc_match = ResourceContent.objects.create(
        resource=res_match,
        title="Photosynthesis Deep Dive",
        main_url="https://example.com/photo",
        description="",
        is_active=True,
        created_by=owner,
    )
    rc_match.languages.set([en1])
    rc_no = ResourceContent.objects.create(
        resource=res_no,
        title="Completely Unrelated Topic",
        main_url="https://example.com/nophoto",
        description="",
        is_active=True,
        created_by=owner,
    )
    rc_no.languages.set([en2])

    req = ItemSearchRequest(query="photosynthesis", offset=0, limit=100)
    result = postgres_search(req)
    ids = [r.id for r in result.results]
    assert str(res_match.uuid) in ids
    assert str(res_no.uuid) not in ids


# ---------------------------------------------------------------------------
# Facets structure
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_facets_length_is_9(live_resource):
    """postgres_search always returns exactly 9 facet categories."""
    req = ItemSearchRequest(query="", offset=0, limit=20)
    result = postgres_search(req)
    assert len(result.facets) == 9
