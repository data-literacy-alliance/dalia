"""Metadata-stripping image re-encoding (EXIF/XMP/PNG text chunks are dropped)."""

import io

from PIL import Image, ImageOps

JPEG_QUALITY = 90
SUPPORTED_FORMATS = ("JPEG", "PNG", "GIF", "WEBP")


def _icc(img):
    return img.info.get("icc_profile")


def _reencode_jpeg(img, out):
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L", "CMYK"):
        img = img.convert("RGB")
    kwargs = {"quality": JPEG_QUALITY, "optimize": True}
    if _icc(img):
        kwargs["icc_profile"] = _icc(img)
    img.save(out, "JPEG", **kwargs)


def _reencode_webp(img, out, lossless):
    animated = getattr(img, "n_frames", 1) > 1
    if not animated:  # exif_transpose returns a copy that would lose the frames
        img = ImageOps.exif_transpose(img)
    kwargs = {"lossless": True} if lossless else {"quality": JPEG_QUALITY}
    if animated:
        kwargs["save_all"] = True
        if "loop" in img.info:
            kwargs["loop"] = img.info["loop"]
        durations = []
        for index in range(img.n_frames):
            img.seek(index)
            img.load()  # frame info (duration) is filled on load
            durations.append(img.info.get("duration", 0))
        img.seek(0)
        img.load()
        kwargs["duration"] = durations
    if _icc(img):
        kwargs["icc_profile"] = _icc(img)
    img.save(out, "WEBP", **kwargs)


def _reencode_png(img, out):
    kwargs = {}
    if _icc(img):
        kwargs["icc_profile"] = _icc(img)
    if "transparency" in img.info:
        kwargs["transparency"] = img.info["transparency"]
    # A fresh save writes no tEXt/zTXt/iTXt chunks (``pnginfo`` is not passed).
    img.save(out, "PNG", **kwargs)


def _reencode_gif(img, out):
    kwargs = {"save_all": True}
    for key in ("duration", "loop", "transparency", "disposal"):
        if key in img.info:
            kwargs[key] = img.info[key]
    # Comment and application extensions (except looping) are not carried over.
    img.save(out, "GIF", **kwargs)


def _is_lossless_webp(img) -> bool:
    # Pillow does not expose this directly; VP8L chunk marks lossless streams.
    raw = getattr(img, "fp", None)
    try:
        pos = raw.tell()
        raw.seek(0)
        head = raw.read(32)
        raw.seek(pos)
    except (AttributeError, OSError, ValueError):
        return False
    return b"VP8L" in head


def reencode_image(file, fmt: str) -> bytes:
    """Return ``file`` re-encoded as ``fmt`` without any embedded metadata.

    ``fmt`` is a Pillow format name (JPEG, PNG, GIF, WEBP); the output format
    always equals the input format.
    """
    fmt = fmt.upper()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported image format: {fmt}")
    if hasattr(file, "seek"):
        file.seek(0)
    out = io.BytesIO()
    with Image.open(file, formats=[fmt]) as img:
        lossless = fmt == "WEBP" and _is_lossless_webp(img)  # needs the open file
        img.load()
        if fmt == "JPEG":
            _reencode_jpeg(img, out)
        elif fmt == "WEBP":
            _reencode_webp(img, out, lossless)
        elif fmt == "PNG":
            _reencode_png(img, out)
        else:
            _reencode_gif(img, out)
    return out.getvalue()
