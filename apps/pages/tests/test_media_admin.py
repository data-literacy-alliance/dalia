import io

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from pages.models import MediaImage, Page
from PIL import Image

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def isolated(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    monkeypatch.setattr("pages.rendering.render_markdown", lambda md: f"<p>{md}</p>")


@pytest.fixture
def client(client, admin_user):
    client.force_login(admin_user)
    return client


def png_bytes(color="red", size=(8, 8)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def make_image(title="Logo", color="red", name="x.png"):
    img = MediaImage(title=title, alt_en="alt en", alt_de="alt de")
    img.image = ContentFile(png_bytes(color), name=name)
    img.save()
    return img


def make_page(**kwargs):
    return Page.objects.create(
        site="website", slug="p", language="en", page_type="legal", title="P", **kwargs
    )


def test_changelist_thumbnail_and_search(client):
    make_image("Alpha logo")
    make_image("Beta", "blue")
    url = reverse("admin:pages_mediaimage_changelist")
    html = client.get(url).content.decode()
    assert 'style="max-height:60px"' in html and "alpha-logo" in html
    html = client.get(url, {"q": "Alpha"}).content.decode()
    assert "Alpha logo" in html and "Beta" not in html
    assert "Alpha logo" in client.get(url, {"q": "alpha-logo"}).content.decode()


def test_change_form_snippets_and_readonly_image(client):
    image = make_image()
    response = client.get(reverse("admin:pages_mediaimage_change", args=[image.pk]))
    html = response.content.decode()
    assert f"![alt en]({image.image.url})" in html
    assert f"![alt de]({image.image.url})" in html
    assert "navigator.clipboard" in html
    assert "image" not in response.context["adminform"].form.fields
    assert "Not used yet" in html


def test_add_form_help_and_upload_sets_uploaded_by(client, admin_user):
    url = reverse("admin:pages_mediaimage_add")
    assert "do not upload confidential images" in client.get(url).content.decode()
    response = client.post(
        url,
        {
            "image": SimpleUploadedFile("up.png", png_bytes()),
            "title": "Up",
            "alt_en": "a",
            "alt_de": "b",
        },
    )
    assert response.status_code == 302
    image = MediaImage.objects.get()
    assert image.uploaded_by == admin_user and len(image.sha256) == 64


def test_svg_upload_rejected(client):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>1</script></svg>'
    response = client.post(
        reverse("admin:pages_mediaimage_add"),
        {"image": SimpleUploadedFile("x.svg", svg), "title": "S", "alt_en": "a", "alt_de": "b"},
    )
    assert response.status_code == 200
    assert not MediaImage.objects.exists()


def test_used_on_links_and_delete_blocked_for_cover(client):
    image = make_image()
    page = make_page(cover_image=image)
    change = reverse("admin:pages_mediaimage_change", args=[image.pk])
    html = client.get(change).content.decode()
    assert page.title in html and "cannot be deleted" in html
    delete = reverse("admin:pages_mediaimage_delete", args=[image.pk])
    assert client.post(delete, {"post": "yes"}).status_code in (403, 302)
    assert MediaImage.objects.filter(pk=image.pk).exists()


@pytest.mark.parametrize("via", ["cover", "block", "content_md", "body_md"])
def test_in_use_blocks_single_and_bulk_delete(client, via):
    from pages.models import PageBlock

    image = make_image()
    if via == "cover":
        make_page(cover_image=image)
    elif via == "content_md":
        make_page(content_md=f"![a]({image.image.url})")
    else:
        page = make_page()
        if via == "block":
            PageBlock.objects.create(page=page, kind="partner_logo", image=image)
        else:
            PageBlock.objects.create(page=page, kind="section", body_md=image.image.url)
    delete = reverse("admin:pages_mediaimage_delete", args=[image.pk])
    client.post(delete, {"post": "yes"})
    assert MediaImage.objects.filter(pk=image.pk).exists()
    changelist = reverse("admin:pages_mediaimage_changelist")
    response = client.post(
        changelist,
        {"action": "delete_selected", "_selected_action": [image.pk], "post": "yes"},
        follow=True,
    )
    assert MediaImage.objects.filter(pk=image.pk).exists()
    assert "Nothing was deleted" in response.content.decode()


def test_bulk_delete_refuses_all_when_one_in_use(client):
    used, unused = make_image("Used"), make_image("Free", "blue")
    make_page(cover_image=used)
    client.post(
        reverse("admin:pages_mediaimage_changelist"),
        {"action": "delete_selected", "_selected_action": [used.pk, unused.pk], "post": "yes"},
    )
    assert MediaImage.objects.count() == 2


def test_delete_queryset_direct_refuses(admin_user, rf):
    from django.contrib import admin

    used = make_image("Used")
    make_page(cover_image=used)
    request = rf.post("/")
    request.user = admin_user
    request._messages = type("M", (), {"add": lambda *a, **k: None})()
    model_admin = admin.site._registry[MediaImage]
    model_admin.delete_queryset(request, MediaImage.objects.all())
    assert MediaImage.objects.exists()


def test_unused_delete_removes_file_after_commit(client, django_capture_on_commit_callbacks):
    image = make_image()
    name = image.image.name
    storage = image.image.storage
    assert storage.exists(name)
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        response = client.post(
            reverse("admin:pages_mediaimage_delete", args=[image.pk]), {"post": "yes"}
        )
    assert response.status_code == 302
    assert not MediaImage.objects.exists()
    assert storage.exists(name)  # still there until the transaction commits
    for callback in callbacks:
        callback()
    assert not storage.exists(name)


def test_autocomplete_endpoint_returns_images(client):
    make_image("Findable logo")
    make_image("Other", "blue")
    response = client.get(
        reverse("admin:autocomplete"),
        {
            "term": "Findable",
            "app_label": "pages",
            "model_name": "page",
            "field_name": "cover_image",
        },
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["text"] for r in results] == ["Findable logo"]


def test_changelist_query_count_does_not_grow_with_images(client):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    url = reverse("admin:pages_mediaimage_changelist")

    def add(i):
        image = MediaImage(title=f"Img {i}", alt_en="a", alt_de="b")
        image.image = ContentFile(png_bytes("red", (8 + i, 8)), name=f"i{i}.png")
        image.save()
        Page.objects.create(
            site="website",
            slug=f"p{i}",
            language="en",
            page_type="legal",
            title="P",
            cover_image=image,
        )

    def count_queries():
        with CaptureQueriesContext(connection) as ctx:
            assert client.get(url).status_code == 200
        return len(ctx)

    for i in range(2):
        add(i)
    few = count_queries()
    for i in range(2, 10):
        add(i)
    assert count_queries() == few
