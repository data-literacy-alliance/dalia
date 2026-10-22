import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from pages.admin_event_category import EventCategoryAdmin
from pages.models import EventCategory, WebsitePage

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(client):
    user = get_user_model().objects.create_superuser(
        username="s16admin", email="s16admin@example.com", password="x"
    )
    client.force_login(user)
    return client


@pytest.fixture
def category():
    return EventCategory.objects.create(name_en="Workshop", name_de="Workshop DE", color="#FF7B42")


def test_changelist_renders_badge_and_count(staff_client, category):
    resp = staff_client.get(reverse("admin:pages_eventcategory_changelist"))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "background-color: #FF7B42" in html
    assert "Workshop DE" in html


def test_events_count_bold_when_used(category):
    ma = EventCategoryAdmin(EventCategory, admin.site)
    assert ma.events_count(category) == 0
    WebsitePage.objects.create(
        slug="ev1", language="en", site="website", page_type="event", category=category
    )
    assert str(ma.events_count(category)) == "<strong>1</strong>"


def test_actions_toggle_is_active(staff_client, category):
    url = reverse("admin:pages_eventcategory_changelist")
    staff_client.post(url, {"action": "deactivate_categories", "_selected_action": [category.pk]})
    category.refresh_from_db()
    assert category.is_active is False
    staff_client.post(url, {"action": "activate_categories", "_selected_action": [category.pk]})
    category.refresh_from_db()
    assert category.is_active is True


def test_invalid_colour_rejected_in_add_form(staff_client):
    url = reverse("admin:pages_eventcategory_add")
    resp = staff_client.post(
        url, {"name_en": "Bad", "name_de": "Bad", "color": "red", "order": 0, "is_active": "on"}
    )
    assert resp.status_code == 200
    assert not EventCategory.objects.filter(name_en="Bad").exists()


def test_valid_colour_saved(staff_client):
    url = reverse("admin:pages_eventcategory_add")
    staff_client.post(
        url,
        {"name_en": "Good", "name_de": "Gut", "color": "#00AA11", "order": 1, "is_active": "on"},
    )
    assert EventCategory.objects.filter(name_en="Good").exists()


def test_delete_blocked_while_used(staff_client, category):
    WebsitePage.objects.create(
        slug="ev2", language="en", site="website", page_type="event", category=category
    )
    url = reverse("admin:pages_eventcategory_delete", args=[category.pk])
    resp = staff_client.post(url, {"post": "yes"})
    assert resp.status_code == 200
    assert EventCategory.objects.filter(pk=category.pk).exists()
