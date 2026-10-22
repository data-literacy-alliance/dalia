import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from website.admin_groups import SEARCH_GROUP_NAME, WEBSITE_GROUP_NAME


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        username="root", email="root@example.org", password="pw-12345-xyz"
    )


def _app_list(client, path="/admin/"):
    response = client.get(path, HTTP_HOST="localhost")
    assert response.status_code == 200
    return response


def _groups(user):
    from django.contrib import admin
    from django.test import RequestFactory

    request = RequestFactory().get("/admin/")
    request.user = user
    return {
        app["name"]: [m["object_name"] for m in app["models"]]
        for app in admin.site.get_app_list(request)
    }


def test_superuser_sees_two_site_groups(superuser):
    groups = _groups(superuser)
    assert groups[WEBSITE_GROUP_NAME] == [
        "WebsitePage",
        "MediaImage",
        "EventCategory",
        "ContactFormSettings",
        "EmailProvider",
    ]
    assert groups[SEARCH_GROUP_NAME] == ["SearchPage"]
    assert "Pages" not in groups
    assert "Email" not in groups


def test_staff_without_mailing_perms_does_not_see_email_providers(db):
    user = get_user_model().objects.create_user(
        username="ed", email="ed@example.org", password="pw-12345-xyz", is_staff=True
    )
    user.user_permissions.add(Permission.objects.get(codename="view_websitepage"))
    groups = _groups(user)
    assert groups[WEBSITE_GROUP_NAME] == ["WebsitePage"]
    assert SEARCH_GROUP_NAME not in groups
    assert "EmailProvider" not in sum(groups.values(), [])


def test_admin_index_renders_group_names(superuser):
    client = Client()
    client.force_login(superuser)
    body = _app_list(client).content.decode()
    assert "Website \u2014 dalia.education" in body
    assert "Search portal \u2014 search.dalia.education" in body


def test_page_admins_state_their_site(superuser):
    client = Client()
    client.force_login(superuser)
    assert (
        "shown on dalia.education"
        in _app_list(client, "/admin/pages/websitepage/").content.decode()
    )
    assert (
        "search.dalia.education" in _app_list(client, "/admin/pages/searchpage/").content.decode()
    )
    assert _app_list(client, "/admin/pages/").status_code == 200
