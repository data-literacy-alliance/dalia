import io

import pytest
from django.core.files.base import ContentFile
from pages.media_usage import find_usages, is_in_use
from pages.models import MediaImage, Page, PageBlock
from PIL import Image

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def isolated(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    monkeypatch.setattr("pages.rendering.render_markdown", lambda md: f"<p>{md}</p>")


def png_bytes(color="red"):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, "PNG")
    return buf.getvalue()


def make_image(title="Logo", color="red"):
    img = MediaImage(title=title, alt_en="a", alt_de="b")
    img.image = ContentFile(png_bytes(color), name="x.png")
    img.save()
    return img


def make_page(slug="p", **kwargs):
    return Page.objects.create(
        site="website", slug=slug, language="en", page_type="legal", title=slug, **kwargs
    )


def test_unused_image():
    image = make_image()
    assert find_usages(image) == []
    assert not is_in_use(image)


def test_cover_fk():
    image = make_image()
    page = make_page(cover_image=image)
    assert find_usages(image) == [page]
    assert is_in_use(image)


def test_block_fk():
    image = make_image()
    page = make_page()
    PageBlock.objects.create(page=page, kind="partner_logo", image=image)
    assert find_usages(image) == [page]


def test_content_md_url():
    image = make_image()
    page = make_page(content_md=f"text ![a]({image.image.url}) more")
    assert find_usages(image) == [page]


def test_block_body_md_url():
    image = make_image()
    page = make_page()
    PageBlock.objects.create(page=page, kind="section", body_md=f"![a]({image.image.url})")
    assert find_usages(image) == [page]


def test_search_site_page_counts_too():
    image = make_image()
    page = Page.objects.create(site="search", slug="s", language="en", content_md=image.image.url)
    assert find_usages(image) == [page]


def test_distinct_pages():
    image = make_image()
    page = make_page(cover_image=image, content_md=image.image.url)
    PageBlock.objects.create(page=page, kind="partner_logo", image=image)
    PageBlock.objects.create(page=page, kind="funder_logo", image=image)
    assert find_usages(image) == [page]


def test_other_image_not_matched():
    one, two = make_image("One", "red"), make_image("Two", "blue")
    make_page(cover_image=one)
    assert not is_in_use(two)


def test_usage_counts_match_find_usages_in_constant_queries(django_assert_num_queries):
    from pages.media_usage import usage_counts

    a, b, c = make_image("A", "red"), make_image("B", "blue"), make_image("C", "green")
    page1 = make_page("p1", cover_image=a, content_md=f"![x]({b.image.url})")
    page2 = make_page("p2")
    PageBlock.objects.create(page=page2, kind="section", sort_order=0, image=a)
    PageBlock.objects.create(page=page2, kind="section", sort_order=1, body_md=b.image.url)
    PageBlock.objects.create(page=page1, kind="section", sort_order=0, image=a)
    images = [a, b, c]
    with django_assert_num_queries(4):
        counts = usage_counts(images)
    assert counts == {img.pk: len(find_usages(img)) for img in images}
    assert counts == {a.pk: 2, b.pk: 2, c.pk: 0}
