"""Validators and limits shared by the pages models and admin."""

import os

from django.core.exceptions import ValidationError
from PIL import Image

MAX_MARKDOWN_CHARS = 500_000

ALLOWED_IMAGE_FORMATS = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "gif": "GIF",
    "webp": "WEBP",
}
# Only these decoders are ever tried by Pillow (no TIFF/PSD/... detection).
PILLOW_DECODERS = ["JPEG", "PNG", "GIF", "WEBP"]
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_SIDE = 10_000


def _file_size(file) -> int:
    size = getattr(file, "size", None)
    if size is not None:
        return size
    pos = file.tell()
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(pos)
    return size


def validate_image_upload(file, filename: str) -> str:
    """Validate an uploaded image and return its Pillow format name.

    Rejects unknown extensions (incl. SVG), files above 5 MB, content that is
    not decodable by the allowed decoders, extension/format mismatches and
    images above the pixel limits. Dimensions come from the header only.
    """
    ext = os.path.splitext(filename or "")[1].lstrip(".").lower()
    expected = ALLOWED_IMAGE_FORMATS.get(ext)
    if expected is None:
        allowed = ", ".join(sorted(ALLOWED_IMAGE_FORMATS))
        raise ValidationError(f"Unsupported image type. Allowed extensions: {allowed}.")

    if _file_size(file) > MAX_IMAGE_BYTES:
        raise ValidationError(f"Image is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB.")

    try:
        file.seek(0)
        with Image.open(file, formats=PILLOW_DECODERS) as img:
            fmt = img.format
            width, height = img.size
        file.seek(0)
        with Image.open(file, formats=PILLOW_DECODERS) as img:
            img.verify()
    except ValidationError:
        raise
    except Exception as exc:  # Pillow raises many types, incl. DecompressionBombError
        raise ValidationError("The file is not a valid image.") from exc
    finally:
        try:
            file.seek(0)
        except Exception:  # noqa: S110 - file may already be closed
            pass

    if fmt != expected:
        raise ValidationError("The image content does not match its file extension.")
    if width * height > MAX_IMAGE_PIXELS or max(width, height) > MAX_IMAGE_SIDE:
        raise ValidationError(
            f"Image dimensions are too large (max {MAX_IMAGE_PIXELS:,} pixels, "
            f"{MAX_IMAGE_SIDE:,} px per side)."
        )
    return fmt


def validate_image_field(file) -> None:
    """Field validator wrapper for ``MediaImage.image``."""
    validate_image_upload(file, getattr(file, "name", "") or "")
