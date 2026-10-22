import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from pages import validators
from pages.validators import validate_image_upload
from PIL import Image


def _image_bytes(fmt, size=(8, 8)):
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, format=fmt)
    return buf.getvalue()


def _upload(name, data):
    return SimpleUploadedFile(name, data)


@pytest.mark.parametrize(
    "name,fmt,pil",
    [
        ("a.png", "PNG", "PNG"),
        ("a.JPG", "JPEG", "JPEG"),
        ("a.jpeg", "JPEG", "JPEG"),
        ("a.gif", "GIF", "GIF"),
        ("a.webp", "WEBP", "WEBP"),
    ],
)
def test_valid_images_return_format(name, fmt, pil):
    assert validate_image_upload(_upload(name, _image_bytes(pil)), name) == fmt


def test_svg_rejected():
    with pytest.raises(ValidationError):
        validate_image_upload(_upload("a.svg", b"<svg/>"), "a.svg")


def test_png_renamed_jpg_rejected():
    with pytest.raises(ValidationError, match="extension"):
        validate_image_upload(_upload("a.jpg", _image_bytes("PNG")), "a.jpg")


def test_non_image_renamed_png_rejected():
    with pytest.raises(ValidationError):
        validate_image_upload(_upload("a.png", b"not an image"), "a.png")


def test_tiff_renamed_png_rejected_by_formats_restriction():
    with pytest.raises(ValidationError):
        validate_image_upload(_upload("a.png", _image_bytes("TIFF")), "a.png")


def test_oversized_file_rejected(monkeypatch):
    monkeypatch.setattr(validators, "MAX_IMAGE_BYTES", 10)
    with pytest.raises(ValidationError, match="larger"):
        validate_image_upload(_upload("a.png", _image_bytes("PNG")), "a.png")


def test_side_above_limit_rejected():
    data = _image_bytes("PNG", (10_001, 1))
    with pytest.raises(ValidationError, match="dimensions"):
        validate_image_upload(_upload("a.png", data), "a.png")


def test_pixel_count_above_limit_rejected():
    data = _image_bytes("PNG", (9_000, 5_000))  # 45 MP, each side <= 10 000
    with pytest.raises(ValidationError, match="dimensions"):
        validate_image_upload(_upload("a.png", data), "a.png")


def test_file_pointer_reset_after_validation():
    f = _upload("a.png", _image_bytes("PNG"))
    validate_image_upload(f, "a.png")
    assert f.tell() == 0


def test_markdown_limit_constant():
    assert validators.MAX_MARKDOWN_CHARS == 500_000
