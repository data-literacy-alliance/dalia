import io
import os
from pathlib import Path

import pytest
from pages.docx_media import (
    collect_extracted_images,
    register_extracted_media,
    strip_image_refs,
)
from pages.models import MediaImage, Page
from PIL import Image


@pytest.fixture(autouse=True)
def isolated(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path / "media"
    monkeypatch.setattr("pages.rendering.render_markdown", lambda md: f"<p>{md}</p>")


@pytest.fixture
def tmp(tmp_path):
    root = tmp_path / "extract"
    (root / "media").mkdir(parents=True)
    return root


def write_png(path, color="red", size=(8, 8)):
    Image.new("RGB", size, color).save(path, "PNG")
    return path


def names(files, root):
    return [str(p.relative_to(root)) for p in files]


def test_collect_accepts_in_order(tmp):
    write_png(tmp / "media" / "image10.png")
    write_png(tmp / "media" / "image2.png")
    write_png(tmp / "media" / "image1.png")
    files, warnings = collect_extracted_images(tmp)
    assert names(files, tmp) == ["media/image1.png", "media/image2.png", "media/image10.png"]
    assert warnings == []


def test_collect_skips_symlink_to_passwd(tmp):
    os.symlink("/etc/passwd", tmp / "media" / "image1.png")
    files, warnings = collect_extracted_images(tmp)
    assert files == [] and "media/image1.png" in warnings[0] and "symbolic link" in warnings[0]


def test_collect_skips_symlink_to_valid_image_outside(tmp, tmp_path):
    outside = write_png(tmp_path / "outside.png")
    os.symlink(outside, tmp / "media" / "image1.png")
    files, warnings = collect_extracted_images(tmp)
    assert files == [] and len(warnings) == 1


def test_collect_skips_symlinked_directory(tmp, tmp_path):
    outside = tmp_path / "other"
    outside.mkdir()
    write_png(outside / "a.png")
    os.symlink(outside, tmp / "media" / "linked")
    files, warnings = collect_extracted_images(tmp)
    assert files == [] and "media/linked" in warnings[0]


def test_collect_skips_dotdot_escape(tmp, tmp_path):
    # A path reaching outside through "../" is rejected by the realpath check.
    from pages import docx_media

    outside = write_png(tmp_path / "outside.png")
    reason = docx_media._check_file(
        str(tmp / "media" / ".." / ".." / "outside.png"), os.path.realpath(tmp), "x"
    )
    assert outside.exists() and reason == "outside the extraction directory"


def test_collect_skips_emf_and_bad_content(tmp):
    (tmp / "media" / "image1.emf").write_bytes(b"\x01\x00\x00\x00")
    buf = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buf, "TIFF")
    (tmp / "media" / "image2.png").write_bytes(buf.getvalue())  # TIFF renamed .png
    files, warnings = collect_extracted_images(tmp)
    assert files == [] and len(warnings) == 2
    assert "unsupported" in warnings[0]


def test_collect_skips_oversized(tmp):
    big = tmp / "media" / "image1.png"
    big.write_bytes(b"\x89PNG" + b"0" * (5 * 1024 * 1024 + 1))
    huge = write_png(tmp / "media" / "image2.png", size=(10_001, 2))
    files, warnings = collect_extracted_images(tmp)
    assert huge.exists() and files == [] and len(warnings) == 2


def test_strip_image_refs():
    md = (
        'a ![x](/tmp/q/media/image1.png){width="1in"} b ![y](/tmp/q/media/image2.png) c '
        "![z](media/image1.png.bak)"
    )
    out = strip_image_refs(md, ["media/image1.png"])
    assert "image1.png)" not in out.replace("image1.png.bak)", "")
    assert "![y](/tmp/q/media/image2.png)" in out and "{width" not in out
    assert "![z](media/image1.png.bak)" in out


def test_strip_accepts_collect_warnings(tmp):
    os.symlink("/etc/passwd", tmp / "media" / "image1.png")
    _, warnings = collect_extracted_images(tmp)
    assert strip_image_refs("![a](media/image1.png) ok", warnings) == " ok"


@pytest.mark.django_db
class TestRegister:
    def page(self):
        return Page.objects.create(
            site="website", slug="my-page", language="en", page_type="legal", title="My Page"
        )

    def test_registers_names_alt_and_rewrites(self, tmp, django_user_model):
        user = django_user_model.objects.create_user("u", "u@x.org", "pw")
        page = self.page()
        write_png(tmp / "media" / "image1.png")
        files, _ = collect_extracted_images(tmp)
        md = f'![A nice logo]({tmp}/media/image1.png){{width="2in"}}'
        out, warnings = register_extracted_media(page, files, md, user)
        image = MediaImage.objects.get()
        assert image.image.name.endswith("/my-page-image-1.png")
        assert out.startswith(f"![A nice logo]({image.image.url})")
        assert image.alt_en == image.alt_de == "A nice logo"
        assert image.title == "My Page image 1"
        assert image.first_used_on == page and image.uploaded_by == user
        assert len(warnings) == 1 and "alt" in warnings[0]
        assert Path(image.image.path).exists()

    def test_dedupe_on_reimport(self, tmp):
        page = self.page()
        write_png(tmp / "media" / "image1.png")
        files, _ = collect_extracted_images(tmp)
        md = f"![]({tmp}/media/image1.png)"
        first, _ = register_extracted_media(page, files, md, None)
        second, _ = register_extracted_media(page, files, md, None)
        assert MediaImage.objects.count() == 1 and first == second
        assert MediaImage.objects.get().alt_en == "My Page image 1"  # falls back to title

    def test_distinct_images_get_numbered_names(self, tmp):
        page = self.page()
        write_png(tmp / "media" / "image1.png", "red")
        write_png(tmp / "media" / "image2.png", "blue")
        files, _ = collect_extracted_images(tmp)
        register_extracted_media(page, files, "", None)
        got = sorted(i.image.name.rsplit("/", 1)[-1] for i in MediaImage.objects.all())
        assert got == ["my-page-image-1.png", "my-page-image-2.png"]

    def test_skipped_references_removed_end_to_end(self, tmp):
        page = self.page()
        write_png(tmp / "media" / "image1.png")
        (tmp / "media" / "image2.emf").write_bytes(b"x")
        files, skipped = collect_extracted_images(tmp)
        md = f"![a]({tmp}/media/image1.png) ![b]({tmp}/media/image2.emf)"
        md = strip_image_refs(md, skipped)
        out, _ = register_extracted_media(page, files, md, None)
        assert "image2.emf" not in out and "/media/website/" in out
