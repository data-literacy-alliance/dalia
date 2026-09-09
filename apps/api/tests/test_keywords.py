"""
Tests: keywords persist through the ResourceContent API.

Covers ResourceContentReadSerializer.get_keywords (SerializerMethodField)
and ResourceContentWriteSerializer.create / .update (taggit integration).

Endpoint: /api/curation/resource-contents/  (basename 'curation-resourcecontents')
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from curation.models.resources import Resource, ResourceContent
from curation.models.vocabularies import Language

User = get_user_model()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="kw_tester",
        password="pass",
        email="kw@test.com",
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def language(db):
    return Language.objects.create(label="English", code="en", is_active=True)


# Endpoint under test — verified with:
#   python manage.py shell -c "from django.urls import reverse; print(reverse('curation-resourcecontents-list'))"
ENDPOINT = "/api/curation/resource-contents/"


def rc_payload(language, **overrides):
    """Minimum valid payload for ResourceContent POST."""
    payload = {
        "title": "Test Resource",
        "main_url": "https://example.com/test",
        "languages": [language.pk],
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Test 1 — POST with keywords saves them
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_with_keywords_saves_them(auth_client, language):
    """POST with keywords stores tags and returns them sorted."""
    data = rc_payload(language, keywords=["chemistry", "FAIR data"])
    response = auth_client.post(ENDPOINT, data, format="json")

    assert response.status_code == 201, response.data

    resp_keywords = response.data.get("keywords", [])
    assert resp_keywords == ["FAIR data", "chemistry"], (
        f"Expected sorted keywords in response, got {resp_keywords}"
    )

    rc = ResourceContent.objects.last()
    assert set(rc.keywords.names()) == {"chemistry", "FAIR data"}, (
        f"Expected tags on instance, got {set(rc.keywords.names())}"
    )


# ---------------------------------------------------------------------------
# Test 2 — POST without keywords → empty list in response
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_without_keywords_returns_empty_list(auth_client, language):
    """POST omitting 'keywords' key returns an empty keyword list."""
    data = rc_payload(language)
    response = auth_client.post(ENDPOINT, data, format="json")

    assert response.status_code == 201, response.data
    assert response.data.get("keywords") == [], (
        f"Expected [] when keywords omitted, got {response.data.get('keywords')}"
    )


# ---------------------------------------------------------------------------
# Test 3 — POST with empty keywords list → no tags
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_with_empty_keywords_list_stores_no_tags(auth_client, language):
    """POST with keywords=[] creates the object with zero tags."""
    data = rc_payload(language, keywords=[])
    response = auth_client.post(ENDPOINT, data, format="json")

    assert response.status_code == 201, response.data
    assert response.data.get("keywords") == [], (
        f"Expected empty keywords list, got {response.data.get('keywords')}"
    )

    rc = ResourceContent.objects.last()
    assert rc.keywords.count() == 0, f"Expected 0 tags on instance, got {rc.keywords.count()}"


# ---------------------------------------------------------------------------
# Test 4 — GET response includes keywords
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_includes_keywords(auth_client, user, language):
    """GET on a detail URL returns tags set via the ORM, sorted alphabetically."""
    resource = Resource.objects.create(owner=user, title="KW GET Test")
    rc = ResourceContent.objects.create(
        resource=resource,
        title="KW GET Content",
        main_url="https://example.com/kw-get",
        created_by=user,
    )
    rc.languages.set([language])
    rc.keywords.set(["python", "open access"])

    response = auth_client.get(f"{ENDPOINT}{rc.uuid}/")

    assert response.status_code == 200, response.data
    resp_keywords = response.data.get("keywords", [])
    assert resp_keywords == ["open access", "python"], (
        f"Expected sorted keywords in GET response, got {resp_keywords}"
    )


# ---------------------------------------------------------------------------
# Test 5 — PATCH updates keywords
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_patch_updates_keywords(auth_client, language):
    """PATCH with a new keywords list replaces the existing tags."""
    create_resp = auth_client.post(ENDPOINT, rc_payload(language, keywords=["old"]), format="json")
    assert create_resp.status_code == 201, create_resp.data

    uuid = create_resp.data["uuid"]
    patch_resp = auth_client.patch(
        f"{ENDPOINT}{uuid}/",
        {"keywords": ["new1", "new2"]},
        format="json",
    )

    assert patch_resp.status_code == 200, patch_resp.data
    resp_keywords = sorted(patch_resp.data.get("keywords", []))
    assert resp_keywords == ["new1", "new2"], (
        f"Expected updated keywords in PATCH response, got {resp_keywords}"
    )

    rc = ResourceContent.objects.get(uuid=uuid)
    assert set(rc.keywords.names()) == {"new1", "new2"}, (
        f"Expected updated tags on instance, got {set(rc.keywords.names())}"
    )


# ---------------------------------------------------------------------------
# Test 6 — PATCH without keywords key does NOT clear existing keywords
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_patch_without_keywords_preserves_existing_tags(auth_client, language):
    """PATCH omitting 'keywords' must not wipe the existing tags."""
    create_resp = auth_client.post(ENDPOINT, rc_payload(language, keywords=["kept"]), format="json")
    assert create_resp.status_code == 201, create_resp.data

    uuid = create_resp.data["uuid"]
    patch_resp = auth_client.patch(
        f"{ENDPOINT}{uuid}/",
        {"title": "Updated Title"},
        format="json",
    )

    assert patch_resp.status_code == 200, patch_resp.data

    rc = ResourceContent.objects.get(uuid=uuid)
    assert "kept" in rc.keywords.names(), (
        f"Expected 'kept' tag to survive title-only PATCH, got {set(rc.keywords.names())}"
    )


# ---------------------------------------------------------------------------
# Test 7 — PUT with empty keywords clears all tags
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_put_with_empty_keywords_clears_all_tags(auth_client, language):
    """PUT the full payload back with keywords=[] removes all existing tags."""
    create_resp = auth_client.post(ENDPOINT, rc_payload(language, keywords=["old"]), format="json")
    assert create_resp.status_code == 201, create_resp.data

    uuid = create_resp.data["uuid"]
    rc = ResourceContent.objects.get(uuid=uuid)

    # Re-assemble a full PUT payload from the created object, overriding keywords with []
    put_payload = rc_payload(language, keywords=[])
    put_payload["resource"] = rc.resource.pk

    put_resp = auth_client.put(
        f"{ENDPOINT}{uuid}/",
        put_payload,
        format="json",
    )

    assert put_resp.status_code == 200, put_resp.data

    rc.refresh_from_db()
    assert rc.keywords.count() == 0, (
        f"Expected 0 tags after PUT with empty keywords, got {rc.keywords.count()}"
    )
