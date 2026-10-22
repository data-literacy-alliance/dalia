"""Collect, validate and register images extracted from a DOCX by pandoc."""

import hashlib
import os
import re
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from pages.image_processing import reencode_image
from pages.models import MediaImage
from pages.validators import ALLOWED_IMAGE_FORMATS, validate_image_upload

SKIP_MARKER = ": skipped ("
ALT_REVIEW_WARNING = (
    "Images were taken from the document. Please review the generated alt texts "
    "(English and German) in the image library."
)
# ![alt](target "title"){attrs}  (pandoc appends {width=.. height=..} attribute blocks)
_IMAGE_REF = re.compile(
    r"!\[(?P<alt>(?:[^\[\]\\]|\\.)*)\]\(\s*<?(?P<target>[^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)"
    r"(?P<attrs>\{[^}]*\})?"
)


def _natural_key(name: str):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name)]


def _skip(rel: str, reason: str) -> str:
    return f"{rel}{SKIP_MARKER}{reason})"


def _check_file(path: str, real_root: str, rel: str) -> str | None:
    """Return a skip reason, or None when the file is acceptable."""
    if os.path.islink(path):
        return "symbolic link"
    real = os.path.realpath(path)
    if os.path.commonpath([real, real_root]) != real_root:
        return "outside the extraction directory"
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if ext not in ALLOWED_IMAGE_FORMATS:
        return f"unsupported file type .{ext}" if ext else "unsupported file type"
    try:
        with open(real, "rb") as fh:
            validate_image_upload(fh, os.path.basename(path))
    except ValidationError as exc:
        return "; ".join(exc.messages)
    except OSError:
        return "file could not be read"
    return None


def collect_extracted_images(tmp_dir) -> tuple[list[Path], list[str]]:
    """Walk ``tmp_dir`` (never following symlinks) and return (accepted files, warnings)."""
    root = str(tmp_dir)
    real_root = os.path.realpath(root)
    accepted: list[Path] = []
    warnings: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort(key=_natural_key)
        for dirname in list(dirnames):
            full = os.path.join(dirpath, dirname)
            if os.path.islink(full):
                dirnames.remove(dirname)
                warnings.append(_skip(os.path.relpath(full, root), "symbolic link"))
        for filename in sorted(filenames, key=_natural_key):
            full = os.path.join(dirpath, filename)
            rel = os.path.relpath(full, root)
            reason = _check_file(full, real_root, rel)
            if reason:
                warnings.append(_skip(rel, reason))
            else:
                accepted.append(Path(full))
    return accepted, warnings


def _skipped_path(entry: str) -> str:
    """Accept either a bare relative path or a warning produced by ``collect_extracted_images``."""
    return entry.split(SKIP_MARKER, 1)[0].replace("\\", "/")


def strip_image_refs(markdown: str, skipped_names) -> str:
    """Remove Markdown image references whose target ends with a skipped file's relative path."""
    skipped = [p for p in (_skipped_path(s) for s in skipped_names) if p]
    if not skipped:
        return markdown

    def _replace(match):
        target = match.group("target").replace("\\", "/")
        for rel in skipped:
            if target == rel or target.endswith("/" + rel):
                return ""
        return match.group(0)

    return _IMAGE_REF.sub(_replace, markdown)


def _tail(path: Path) -> str:
    return "/".join(path.parts[-2:])


def _matches(target: str, path: Path) -> bool:
    target = target.replace("\\", "/")
    return target == str(path) or target == _tail(path) or target.endswith("/" + _tail(path))


def _alt_from_markdown(markdown: str, path: Path) -> str:
    for match in _IMAGE_REF.finditer(markdown):
        if _matches(match.group("target"), path) and match.group("alt").strip():
            return match.group("alt").strip()
    return ""


def _reencoded_sha256(path: Path) -> str:
    with open(path, "rb") as fh:
        fmt = validate_image_upload(fh, path.name)
        return hashlib.sha256(reencode_image(fh, fmt)).hexdigest()


def _create_image(page, path: Path, n: int, alt: str, user) -> MediaImage:
    base_title = f"{page.title} image {n}"
    title = base_title if len(base_title) <= 200 else f"image {n}"
    alt = (alt or title)[:300]
    image = MediaImage(
        title=title,
        alt_en=alt,
        alt_de=alt,
        first_used_on=page,
        uploaded_by=user if getattr(user, "is_authenticated", False) else None,
    )
    image._upload_stem = f"{page.slug}-image-{n}"
    # A copy of the bytes: the model re-encodes and stores its own file.
    image.image = ContentFile(path.read_bytes(), name=f"image.{path.suffix.lstrip('.').lower()}")
    image.save()
    return image


def _rewrite_refs(markdown: str, path: Path, url: str) -> str:
    def _replace(match):
        if not _matches(match.group("target"), path):
            return match.group(0)
        # Drop a trailing {attrs} block: the website reader does not parse it.
        text = match.group(0)
        if match.group("attrs"):
            text = text[: match.start("attrs") - match.start(0)]
        return text.replace(match.group("target"), url, 1)

    return _IMAGE_REF.sub(_replace, markdown)


def register_extracted_media(page, accepted_files, markdown, user) -> tuple[str, list[str]]:
    """Create/reuse ``MediaImage`` rows for ``accepted_files`` and rewrite the Markdown paths."""
    warnings: list[str] = []
    registered = False
    for n, path in enumerate(accepted_files, start=1):
        path = Path(path)
        alt = _alt_from_markdown(markdown, path)
        try:
            digest = _reencoded_sha256(path)
            image = MediaImage.objects.filter(first_used_on=page, sha256=digest).first()
            if image is None:
                image = _create_image(page, path, n, alt, user)
        except (ValidationError, OSError) as exc:
            reason = "; ".join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
            warnings.append(_skip(_tail(path), reason))
            markdown = strip_image_refs(markdown, [_tail(path)])
            continue
        markdown = _rewrite_refs(markdown, path, image.image.url)
        registered = True
    if registered:
        warnings.append(ALT_REVIEW_WARNING)
    return markdown, warnings
