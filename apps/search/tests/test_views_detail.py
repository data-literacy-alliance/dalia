"""Tests for ItemView PG detail fallback (apps/search/views.py)."""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from curation.models.resources import Resource, ResourceContent
from curation.models.vocabularies import Language
from search.views import ItemView
import search.views as views_mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def owner(db):
    User = get_user_model()
    return User.objects.create_user(
        username="view_owner",
        email="view_owner@example.com",
        password="x",
    )


@pytest.fixture
def published_resource(owner):
    """Published, active PG resource."""
    res = Resource.objects.create(
        owner=owner,
        title="Published Detail Res",
        is_published=True,
        is_removed=False,
    )
    en = Language.objects.create(label="EN View", code="en_view", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Published Detail Content",
        main_url="https://example.com/detail",
        description="Detail test.",
        is_active=True,
        created_by=owner,
        publication_date=datetime.date(2023, 1, 1),
    )
    rc.languages.set([en])
    return res, rc


@pytest.fixture
def unpublished_resource(owner):
    res = Resource.objects.create(
        owner=owner,
        title="Unpub View Res",
        is_published=False,
        is_removed=False,
    )
    en = Language.objects.create(label="EN Unpub", code="en_unpub", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Unpub Content",
        main_url="https://example.com/unpub",
        is_active=True,
        created_by=owner,
    )
    rc.languages.set([en])
    return res, rc


@pytest.fixture
def removed_resource(owner):
    res = Resource.objects.create(
        owner=owner,
        title="Removed View Res",
        is_published=True,
        is_removed=True,
    )
    en = Language.objects.create(label="EN Removed", code="en_removed", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Removed Content",
        main_url="https://example.com/removed",
        is_active=True,
        created_by=owner,
    )
    rc.languages.set([en])
    return res, rc


@pytest.fixture
def inactive_content_resource(owner):
    res = Resource.objects.create(
        owner=owner,
        title="Inactive View Res",
        is_published=True,
        is_removed=False,
    )
    en = Language.objects.create(label="EN Inact", code="en_inact", uri="", is_active=True)
    rc = ResourceContent.objects.create(
        resource=res,
        title="Inactive Content",
        main_url="https://example.com/inactive",
        is_active=True,
        created_by=owner,
    )
    # Force is_active to False after creation (bypasses auto-activate signal).
    ResourceContent.objects.filter(pk=rc.pk).update(is_active=False)
    rc.languages.set([en])
    return res, rc


# Stub for get_metadata_for_learning_resource returning None (Fuseki miss)
def _stub_get_metadata_none(resource_id):
    return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_detail_published_pg_returns_200(client, published_resource, monkeypatch):
    """A published PG resource with postgres enabled returns 200 with source=postgres."""
    res, rc = published_resource
    monkeypatch.setattr(views_mod, "get_metadata_for_learning_resource", _stub_get_metadata_none)

    url = reverse("search:item_detail", kwargs={"resource_id": res.uuid})
    with override_settings(DALIA_SEARCH_SOURCES=["postgres"]):
        response = client.get(url)

    assert response.status_code == 200
    assert response.data.get("source") == "postgres"
    assert response.data.get("title") == "Published Detail Content"


@pytest.mark.django_db
def test_detail_nonexistent_uuid_returns_404(client, monkeypatch):
    """A non-existent UUID returns 404."""
    import uuid as uuid_mod

    monkeypatch.setattr(views_mod, "get_metadata_for_learning_resource", _stub_get_metadata_none)

    nonexistent = uuid_mod.uuid4()
    url = reverse("search:item_detail", kwargs={"resource_id": nonexistent})
    with override_settings(DALIA_SEARCH_SOURCES=["postgres"]):
        response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_detail_unpublished_returns_404(client, unpublished_resource, monkeypatch):
    """An unpublished resource is excluded from PG hydrate → 404."""
    res, rc = unpublished_resource
    monkeypatch.setattr(views_mod, "get_metadata_for_learning_resource", _stub_get_metadata_none)

    url = reverse("search:item_detail", kwargs={"resource_id": res.uuid})
    with override_settings(DALIA_SEARCH_SOURCES=["postgres"]):
        response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_detail_removed_returns_404(client, removed_resource, monkeypatch):
    """A removed resource is excluded from PG hydrate → 404."""
    res, rc = removed_resource
    monkeypatch.setattr(views_mod, "get_metadata_for_learning_resource", _stub_get_metadata_none)

    url = reverse("search:item_detail", kwargs={"resource_id": res.uuid})
    with override_settings(DALIA_SEARCH_SOURCES=["postgres"]):
        response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_detail_inactive_content_returns_404(client, inactive_content_resource, monkeypatch):
    """A resource whose only content is inactive is excluded from PG hydrate → 404."""
    res, rc = inactive_content_resource
    monkeypatch.setattr(views_mod, "get_metadata_for_learning_resource", _stub_get_metadata_none)

    url = reverse("search:item_detail", kwargs={"resource_id": res.uuid})
    with override_settings(DALIA_SEARCH_SOURCES=["postgres"]):
        response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_detail_postgres_disabled_fuseki_miss_returns_404(client, published_resource, monkeypatch):
    """With postgres NOT in enabled sources and fuseki miss → 404."""
    res, rc = published_resource
    monkeypatch.setattr(views_mod, "get_metadata_for_learning_resource", _stub_get_metadata_none)

    url = reverse("search:item_detail", kwargs={"resource_id": res.uuid})
    with override_settings(DALIA_SEARCH_SOURCES=["fuseki"]):
        response = client.get(url)

    assert response.status_code == 404
