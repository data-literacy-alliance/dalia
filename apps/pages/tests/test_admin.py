import io
import os
import zipfile
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from pages import rendering
from pages.models import EventCategory, Page, PageBlock
from PIL import Image

pytestmark = pytest.mark.django_db

_REAL_RENDER = rendering.render_markdown


@pytest.fixture(autouse=True)
def isolated(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    monkeypatch.setattr("pages.rendering.render_markdown", lambda md: f"<p>{md}</p>")


@pytest.fixture
def client(client, admin_user):
    client.force_login(admin_user)
    return client


def png_bytes(color="red"):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, "PNG")
    return buf.getvalue()


def docx_bytes(with_main=True):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml" if with_main else "other.xml", "<w/>")
    return buf.getvalue()


def make_page(site="website", slug="p", language="en", docx=False, **kwargs):
    kwargs.setdefault("page_type", "legal" if site == "website" else "")
    kwargs.setdefault("title", slug if site == "website" else "")
    page = Page(site=site, slug=slug, language=language, **kwargs)
    if docx:
        page.docx_file.save("doc.docx", ContentFile(docx_bytes()), save=False)
    page.save()
    return page


def convert_url(page):
    model = "websitepage" if page.site == "website" else "searchpage"
    return reverse(f"admin:pages-{model}-convert", args=[page.pk])


def change_url(page):
    model = "websitepage" if page.site == "website" else "searchpage"
    return reverse(f"admin:pages_{model}_change", args=[page.pk])


def inline_management(prefix="blocks", total=0):
    return {
        f"{prefix}-TOTAL_FORMS": str(total),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


def website_post(**overrides):
    data = {
        "page_type": "legal",
        "language": "en",
        "title": "Privacy",
        "slug": "privacy",
        "is_published": "on",
        "menu_order": "0",
        "content_md": "hello",
        **inline_management(),
    }
    data.update(overrides)
    return data


# -- changelists / forms ---------------------------------------------------------


def test_changelists_show_only_their_site(client):
    make_page("search", slug="search-only")
    make_page("website", slug="website-only")
    search = client.get(reverse("admin:pages_searchpage_changelist")).content.decode()
    website = client.get(reverse("admin:pages_websitepage_changelist")).content.decode()
    assert "search-only" in search and "website-only" not in search
    assert "website-only" in website and "search-only" not in website


def test_website_page_with_block_renders_html(client):
    data = website_post(
        **inline_management(total=1),
        **{
            "blocks-0-kind": "section",
            "blocks-0-body_md": "block text",
            "blocks-0-sort_order": "1",
        },
    )
    resp = client.post(reverse("admin:pages_websitepage_add"), data)
    assert resp.status_code == 302, getattr(resp, "context_data", resp.content[:300])
    page = Page.objects.get(slug="privacy")
    assert page.site == "website" and page.content_html == "<p>hello</p>"
    block = PageBlock.objects.get(page=page)
    assert block.body_html == "<p>block text</p>"


def test_render_error_is_form_error_and_nothing_saved(client, monkeypatch):
    def boom(md):
        raise rendering.RenderError("bad <b>markup</b>")

    monkeypatch.setattr("pages.rendering.render_markdown", boom)
    resp = client.post(reverse("admin:pages_websitepage_add"), website_post())
    assert resp.status_code == 200
    assert "Markdown could not be rendered" in resp.content.decode()
    assert "<b>markup</b>" not in resp.content.decode()
    assert not Page.objects.filter(slug="privacy").exists()


def test_block_render_error_is_form_error_and_nothing_saved(client, monkeypatch):
    def boom(md):
        if md == "bad":
            raise rendering.RenderError("nope")
        return md

    monkeypatch.setattr("pages.rendering.render_markdown", boom)
    data = website_post(
        content_md="fine",
        **inline_management(total=1),
        **{"blocks-0-kind": "section", "blocks-0-body_md": "bad", "blocks-0-sort_order": "0"},
    )
    resp = client.post(reverse("admin:pages_websitepage_add"), data)
    assert resp.status_code == 200
    assert not Page.objects.filter(slug="privacy").exists()


def test_plain_text_block_kinds_are_not_rendered(client, monkeypatch):
    def boom(md):
        raise rendering.RenderError("must not be called")

    monkeypatch.setattr("pages.rendering.render_markdown", boom)
    data = website_post(
        content_md="",
        **inline_management(total=1),
        **{"blocks-0-kind": "agenda", "blocks-0-body_md": "a\nb", "blocks-0-sort_order": "0"},
    )
    assert client.post(reverse("admin:pages_websitepage_add"), data).status_code == 302


def test_duplicate_slug_is_form_error(client):
    make_page("website", slug="privacy")
    resp = client.post(reverse("admin:pages_websitepage_add"), website_post())
    assert resp.status_code == 200
    assert "unique per language" in resp.content.decode()


def test_search_add_form_has_no_website_fields_and_forces_site(client):
    url = reverse("admin:pages_searchpage_add")
    html = client.get(url).content.decode()
    for name in ("page_type", "parent", "category", "is_published", "cover_image"):
        assert f'name="{name}"' not in html
    resp = client.post(url, {"slug": "about", "language": "en", "content_md": "x"})
    assert resp.status_code == 302
    assert Page.objects.get(slug="about").site == "search"


def test_inactive_category_not_offered_for_new_but_kept_for_existing(client):
    active = EventCategory.objects.create(name_en="Active", name_de="A", color="#112233")
    inactive = EventCategory.objects.create(
        name_en="Old", name_de="O", color="#112233", is_active=False
    )
    from pages.admin import WebsitePageForm
    from pages.models import WebsitePage

    new_ids = set(WebsitePageForm().fields["category"].queryset.values_list("pk", flat=True))
    assert new_ids == {active.pk}
    event = WebsitePage.objects.create(
        slug="ev",
        language="en",
        page_type="event",
        title="Ev",
        date="2026-01-01",
        category=inactive,
    )
    existing = WebsitePageForm(instance=event).fields["category"].queryset
    assert set(existing.values_list("pk", flat=True)) == {active.pk, inactive.pk}


def test_view_on_site_only_when_published():
    from django.contrib import admin
    from pages.models import WebsitePage

    model_admin = admin.site._registry[WebsitePage]
    published = make_page("website", slug="pub", is_published=True)
    draft = make_page("website", slug="draft", is_published=False)
    assert model_admin.view_on_site(published).endswith("/en/pub")
    assert model_admin.view_on_site(draft) is None


# -- docx upload validation --------------------------------------------------------


@pytest.mark.parametrize(
    "name,content",
    [
        ("a.docx", b"not a zip"),
        ("a.docx", docx_bytes(with_main=False)),
        ("a.doc", docx_bytes()),
    ],
)
def test_invalid_docx_upload_is_form_error(client, name, content):
    resp = client.post(
        reverse("admin:pages_searchpage_add"),
        {
            "slug": "up",
            "language": "en",
            "content_md": "",
            "docx_file": SimpleUploadedFile(name, content),
        },
    )
    assert resp.status_code == 200
    assert not Page.objects.filter(slug="up").exists()


def test_valid_docx_upload_accepted(client):
    resp = client.post(
        reverse("admin:pages_searchpage_add"),
        {
            "slug": "up",
            "language": "en",
            "content_md": "",
            "docx_file": SimpleUploadedFile("a.docx", docx_bytes()),
        },
    )
    assert resp.status_code == 302
    assert Page.objects.get(slug="up").docx_file


# -- convert view: access control ------------------------------------------------------


def test_convert_get_is_405(client):
    page = make_page("search", slug="s", docx=True)
    assert client.get(convert_url(page)).status_code == 405


def test_convert_post_without_csrf_is_403(admin_user):
    page = make_page("search", slug="s", docx=True)
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(admin_user)
    assert strict.post(convert_url(page)).status_code == 403


def test_convert_requires_change_permission(client):
    page = make_page("search", slug="s", docx=True)
    user = get_user_model().objects.create_user(
        username="viewer", email="v@example.com", password="x", is_staff=True
    )
    user.user_permissions.add(Permission.objects.get(codename="view_searchpage"))
    viewer = Client()
    viewer.force_login(user)
    assert viewer.post(convert_url(page)).status_code == 403


def test_convert_is_site_scoped(client):
    website = make_page("website", slug="w", docx=True)
    search = make_page("search", slug="s", docx=True)
    assert (
        client.post(reverse("admin:pages-searchpage-convert", args=[website.pk])).status_code == 404
    )
    assert (
        client.post(reverse("admin:pages-websitepage-convert", args=[search.pk])).status_code == 404
    )


def test_convert_redirects_to_change_url_ignoring_referer(client, monkeypatch):
    page = make_page("search", slug="s", docx=True)
    monkeypatch.setattr("pages.rendering.run_pandoc", lambda args, **kw: "md")
    resp = client.post(convert_url(page), HTTP_REFERER="https://evil.example/x")
    assert resp.status_code == 302
    assert resp["Location"] == change_url(page)


def test_permissions_are_per_proxy(client):
    user = get_user_model().objects.create_user(
        username="ed", email="e@example.com", password="x", is_staff=True
    )
    user.user_permissions.add(Permission.objects.get(codename="view_searchpage"))
    editor = Client()
    editor.force_login(user)
    assert editor.get(reverse("admin:pages_searchpage_changelist")).status_code == 200
    assert editor.get(reverse("admin:pages_websitepage_changelist")).status_code == 403


# -- convert view: extraction --------------------------------------------------------


class FakePandoc:
    """Replacement for run_pandoc that writes extracted media like pandoc would."""

    def __init__(self, markdown, files=None, symlinks=None, fail=None):
        self.markdown, self.files, self.symlinks, self.fail = (
            markdown,
            files or {},
            symlinks or {},
            fail,
        )
        self.calls = []
        self.tmp = None

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        extract = next(a for a in args if a.startswith("--extract-media="))
        self.tmp = Path(extract.split("=", 1)[1])
        if self.fail:
            raise self.fail
        for rel, data in self.files.items():
            target = self.tmp / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        for rel, dest in self.symlinks.items():
            target = self.tmp / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(dest)
        return self.markdown.replace("TMP", str(self.tmp))


def test_search_conversion_extracts_outside_media_root_and_rewrites(client, monkeypatch, settings):
    page = make_page("search", slug="s", docx=True)
    fake = FakePandoc(
        "![a](TMP/media/image1.png)\n\n![b](TMP/media/bad.emf)\n\n![c](TMP/media/link.png)\n",
        files={"media/image1.png": png_bytes(), "media/bad.emf": b"EMF"},
        symlinks={"media/link.png": "/etc/passwd"},
    )
    monkeypatch.setattr("pages.rendering.run_pandoc", fake)
    resp = client.post(convert_url(page))
    assert resp.status_code == 302
    args, kwargs = fake.calls[0]
    assert "--sandbox" in args and "-t" in args and args[args.index("-t") + 1] == "markdown"
    assert not str(fake.tmp).startswith(str(settings.MEDIA_ROOT))
    assert not fake.tmp.exists()
    page.refresh_from_db()
    assert page.converted_at is not None
    assert f"![a](/media/pages/media/{page.pk}/image1.png)" in page.content_md
    assert "bad.emf" not in page.content_md and "link.png" not in page.content_md
    stored = Path(settings.MEDIA_ROOT) / "pages" / "media" / str(page.pk)
    assert [p.name for p in stored.iterdir()] == ["image1.png"]
    assert oct(stored.stat().st_mode & 0o777) == "0o755"
    texts = [str(m) for m in get_messages(resp.wsgi_request)]
    assert any("bad.emf" in t for t in texts) and any("link.png" in t for t in texts)
    assert not [p for p in stored.parent.iterdir() if p.name.startswith(".")]


def test_search_reconversion_swaps_directory(client, monkeypatch, settings):
    page = make_page("search", slug="s", docx=True)
    stored = Path(settings.MEDIA_ROOT) / "pages" / "media" / str(page.pk)
    stored.mkdir(parents=True)
    (stored / "old.png").write_bytes(b"old")
    fake = FakePandoc("![a](TMP/media/new.png)", files={"media/new.png": png_bytes("blue")})
    monkeypatch.setattr("pages.rendering.run_pandoc", fake)
    client.post(convert_url(page))
    assert [p.name for p in stored.iterdir()] == ["new.png"]
    assert [p.name for p in stored.parent.iterdir()] == [str(page.pk)]


def test_traversal_symlink_dir_is_skipped(client, monkeypatch, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.png").write_bytes(png_bytes())
    page = make_page("search", slug="s", docx=True)
    fake = FakePandoc("![a](TMP/media/esc/x.png)", symlinks={"media/esc": str(outside)})
    monkeypatch.setattr("pages.rendering.run_pandoc", fake)
    client.post(convert_url(page))
    page.refresh_from_db()
    assert "x.png" not in page.content_md
    assert not (Path(os_media(page)) / "x.png").exists()


def os_media(page):
    from django.conf import settings

    return Path(settings.MEDIA_ROOT) / "pages" / "media" / str(page.pk)


def test_temp_dir_removed_when_pandoc_fails_and_stderr_is_escaped(client, monkeypatch):
    page = make_page("search", slug="s", docx=True)
    fake = FakePandoc("", fail=rendering.RenderError("<script>alert(1)</script>"))
    monkeypatch.setattr("pages.rendering.run_pandoc", fake)
    resp = client.post(convert_url(page), follow=True)
    assert fake.tmp is not None and not fake.tmp.exists()
    html = resp.content.decode()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    page.refresh_from_db()
    assert page.converted_at is None


def test_pandoc_error_text_truncated_to_300(client, monkeypatch):
    page = make_page("search", slug="s", docx=True)
    monkeypatch.setattr(
        "pages.rendering.run_pandoc", FakePandoc("", fail=rendering.RenderError("e" * 900))
    )
    resp = client.post(convert_url(page))
    texts = [str(m) for m in get_messages(resp.wsgi_request)]
    assert texts and "e" * 301 not in texts[0]


def test_website_conversion_uses_register_extracted_media(client, monkeypatch):
    page = make_page("website", slug="w", docx=True)
    fake = FakePandoc(
        "![a](TMP/media/image1.png)\n![b](TMP/media/bad.emf)\n",
        files={"media/image1.png": png_bytes(), "media/bad.emf": b"EMF"},
    )
    monkeypatch.setattr("pages.rendering.run_pandoc", fake)
    seen = {}

    def fake_register(obj, accepted, markdown, user):
        seen.update(obj=obj, accepted=accepted, markdown=markdown, user=user)
        return markdown.replace(str(fake.tmp) + "/media/image1.png", "/media/website/x.png"), [
            "review alt <b>"
        ]

    monkeypatch.setattr("pages.docx_media.register_extracted_media", fake_register)
    resp = client.post(convert_url(page))
    args, _ = fake.calls[0]
    assert args[args.index("-t") + 1] == rendering.MARKDOWN_READER
    assert [p.name for p in seen["accepted"]] == ["image1.png"]
    assert seen["obj"].pk == page.pk and seen["user"].is_superuser
    page.refresh_from_db()
    assert "![a](/media/website/x.png)" in page.content_md and "bad.emf" not in page.content_md
    assert page.content_html.startswith("<p>")
    msgs = [str(m) for m in get_messages(resp.wsgi_request)]
    assert any("review alt &lt;b&gt;" in m for m in msgs)
    assert not fake.tmp.exists()


def test_website_conversion_render_error_saves_nothing(client, monkeypatch):
    page = make_page("website", slug="w", docx=True, content_md="keep")
    monkeypatch.setattr("pages.rendering.run_pandoc", FakePandoc("# new"))

    def boom(md):
        raise rendering.RenderError("render failed")

    monkeypatch.setattr("pages.rendering.render_markdown", boom)
    client.post(convert_url(page))
    page.refresh_from_db()
    assert page.content_md == "keep" and page.converted_at is None


def test_convert_without_docx_warns(client):
    page = make_page("search", slug="s")
    resp = client.post(convert_url(page))
    assert resp.status_code == 302
    assert any("No DOCX" in str(m) for m in get_messages(resp.wsgi_request))


def test_change_form_has_post_convert_button(client):
    page = make_page("search", slug="s", docx=True)
    html = client.get(change_url(page)).content.decode()
    assert f'formaction="{convert_url(page)}"' in html and 'formmethod="post"' in html


# -- signals -----------------------------------------------------------------------


def test_search_page_delete_removes_media_dir_and_docx(client, django_capture_on_commit_callbacks):
    page = make_page("search", slug="s", docx=True)
    media = os_media(page)
    media.mkdir(parents=True)
    (media / "a.png").write_bytes(b"x")
    docx_path = Path(page.docx_file.path)
    assert docx_path.exists()
    with django_capture_on_commit_callbacks(execute=True):
        Page.objects.get(pk=page.pk).delete()
    assert not media.exists() and not docx_path.exists()


def test_docx_replaced_on_proxy_save_removes_old_file(client, django_capture_on_commit_callbacks):
    from pages.models import SearchPage

    page = make_page("search", slug="s", docx=True)
    old = Path(page.docx_file.path)
    proxy = SearchPage.objects.get(pk=page.pk)
    with django_capture_on_commit_callbacks(execute=True):
        proxy.docx_file.save("new.docx", ContentFile(docx_bytes()), save=True)
    assert not old.exists() and Path(proxy.docx_file.path).exists()
    assert os.path.dirname(old) == os.path.dirname(proxy.docx_file.path)


def test_website_conversion_orphan_images_removed_on_failure(client, monkeypatch, tmp_path):
    from pages.models import MediaImage

    page = make_page("website", slug="w", docx=True, content_md="keep")
    fake = FakePandoc("![a](TMP/media/image1.png)\n", files={"media/image1.png": png_bytes()})
    monkeypatch.setattr("pages.rendering.run_pandoc", fake)

    def boom(md):
        raise rendering.RenderError("render failed")

    monkeypatch.setattr("pages.rendering.render_markdown", boom)
    before = {p for p in tmp_path.rglob("*") if p.is_file()}
    client.post(convert_url(page))
    assert MediaImage.objects.count() == 0
    assert {p for p in tmp_path.rglob("*") if p.is_file()} == before
    page.refresh_from_db()
    assert page.content_md == "keep"


def test_website_conversion_success_keeps_image_files(client, monkeypatch, tmp_path):
    from pages.models import MediaImage

    page = make_page("website", slug="w", docx=True)
    fake = FakePandoc("![a](TMP/media/image1.png)\n", files={"media/image1.png": png_bytes()})
    monkeypatch.setattr("pages.rendering.run_pandoc", fake)
    client.post(convert_url(page))
    image = MediaImage.objects.get()
    assert (tmp_path / image.image.name).is_file()


def test_docx_conversion_has_no_leftover_markup(client, monkeypatch, tmp_path):
    import shutil
    import subprocess

    if not shutil.which("pandoc"):
        pytest.skip("pandoc not installed")
    src = tmp_path / "src"
    src.mkdir()
    (src / "img.png").write_bytes(png_bytes())
    (src / "in.md").write_text(
        "# Title {#bm}\n\nText with [under]{.underline} and ![alt](img.png){width=2in height=1in}.\n\n"
        '::: {custom-style="Fancy"}\nStyled paragraph\n:::\n'
    )
    subprocess.run(
        ["pandoc", "in.md", "-f", "markdown", "-t", "docx", "-o", "out.docx"],
        cwd=src,
        check=True,
    )
    page = make_page("website", slug="w", language="en")
    page.docx_file.save("doc.docx", ContentFile((src / "out.docx").read_bytes()), save=True)
    monkeypatch.setattr("pages.rendering.render_markdown", _REAL_RENDER)
    client.post(convert_url(page))
    page.refresh_from_db()
    assert page.converted_at is not None
    for text in (page.content_md, page.content_html):
        assert "{" not in text and ":::" not in text, text
    assert "Styled paragraph" in page.content_html and "under" in page.content_html


def test_replaced_docx_deleted_only_after_commit(django_capture_on_commit_callbacks):
    page = make_page("search", slug="s", docx=True)
    old_path = Path(page.docx_file.path)
    assert old_path.exists()
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        page.docx_file.save("new.docx", ContentFile(docx_bytes()), save=True)
    assert old_path.exists()  # still there before the commit
    for callback in callbacks:
        callback()
    assert not old_path.exists()
    assert Path(page.docx_file.path).exists()


def test_failed_save_keeps_old_docx(django_capture_on_commit_callbacks):
    from django.db import transaction

    page = make_page("search", slug="s", docx=True)
    old_path = Path(page.docx_file.path)
    page.docx_file = ContentFile(docx_bytes(), name="other.docx")
    with django_capture_on_commit_callbacks(execute=True):
        try:
            with transaction.atomic():
                page.save()
                raise RuntimeError("rollback")
        except RuntimeError:
            pass
    assert old_path.exists()
