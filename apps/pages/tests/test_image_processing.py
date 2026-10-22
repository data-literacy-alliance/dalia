import io

import pytest
from pages.image_processing import reencode_image
from PIL import Image, PngImagePlugin, UnidentifiedImageError

EXIF_ORIENTATION = 0x0112


def _exif_with_gps(orientation=1):
    exif = Image.Exif()
    exif[EXIF_ORIENTATION] = orientation
    exif[0x010F] = "SecretCam"  # Make
    gps = exif.get_ifd(0x8825)
    gps[1] = "N"
    gps[2] = (52.0, 31.0, 0.0)
    return exif


def _save(img, fmt, **kwargs):
    buf = io.BytesIO()
    img.save(buf, fmt, **kwargs)
    buf.seek(0)
    return buf


def test_jpeg_exif_gps_xmp_removed_and_orientation_applied():
    img = Image.new("RGB", (40, 20), "red")
    src = _save(img, "JPEG", exif=_exif_with_gps(6), xmp=b"<x:xmpmeta>secret</x:xmpmeta>")
    assert b"SecretCam" in src.getvalue() and b"xmpmeta" in src.getvalue()
    out = reencode_image(src, "JPEG")
    assert b"SecretCam" not in out and b"xmpmeta" not in out
    result = Image.open(io.BytesIO(out))
    assert result.format == "JPEG"
    assert result.size == (20, 40)  # rotated upright
    assert not result.getexif().get(0x8825)


def test_jpeg_icc_profile_kept():
    from PIL import ImageCms

    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    src = _save(Image.new("RGB", (8, 8), "blue"), "JPEG", icc_profile=icc)
    out = Image.open(io.BytesIO(reencode_image(src, "JPEG")))
    assert out.info.get("icc_profile")


def test_png_text_chunks_removed_icc_kept():
    from PIL import ImageCms

    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Author", "Secret Person")
    meta.add_text("XML:com.adobe.xmp", "<x:xmpmeta>s</x:xmpmeta>", zip=False)
    meta.add_itxt("Comment", "secret-itxt")
    meta.add_text("Zipped", "secret-ztxt", zip=True)
    src = _save(Image.new("RGB", (8, 8), "green"), "PNG", pnginfo=meta, icc_profile=icc)
    raw = src.getvalue()
    assert b"Secret Person" in raw and b"secret-itxt" in raw
    data = reencode_image(src, "PNG")
    for needle in (b"tEXt", b"iTXt", b"zTXt", b"Secret Person", b"xmpmeta", b"secret-itxt"):
        assert needle not in data
    out = Image.open(io.BytesIO(data))
    assert out.format == "PNG" and out.info.get("icc_profile")


def test_png_transparency_kept():
    img = Image.new("RGBA", (4, 4), (255, 0, 0, 0))
    out = Image.open(io.BytesIO(reencode_image(_save(img, "PNG"), "PNG")))
    assert out.convert("RGBA").getpixel((0, 0))[3] == 0


def test_gif_frame_count_and_loop_kept():
    frames = [Image.new("P", (6, 6), 0) for _ in range(3)]
    for i, frame in enumerate(frames):
        frame.putpalette([0, 0, 0, 255, 255, 255])
        frame.putpixel((i, i), 1)  # visibly distinct frames, else Pillow merges them
    src = _save(frames[0], "GIF", save_all=True, append_images=frames[1:], duration=120, loop=0)
    out = Image.open(io.BytesIO(reencode_image(src, "GIF")))
    assert out.format == "GIF"
    assert out.n_frames == 3
    assert out.info.get("loop") == 0


def test_webp_lossy_and_lossless_stay_webp():
    img = Image.new("RGB", (8, 8), "purple")
    lossy = reencode_image(_save(img, "WEBP", quality=80, exif=_exif_with_gps()), "WEBP")
    assert Image.open(io.BytesIO(lossy)).format == "WEBP"
    assert b"SecretCam" not in lossy
    lossless = reencode_image(_save(img, "WEBP", lossless=True), "WEBP")
    result = Image.open(io.BytesIO(lossless))
    assert result.format == "WEBP"
    assert result.convert("RGB").getpixel((0, 0)) == (128, 0, 128)


def test_output_format_equals_input_format():
    for fmt in ("JPEG", "PNG", "GIF", "WEBP"):
        src = _save(Image.new("RGB", (4, 4), "white"), fmt)
        assert Image.open(io.BytesIO(reencode_image(src, fmt))).format == fmt


def test_unsupported_format_rejected():
    with pytest.raises(ValueError):
        reencode_image(io.BytesIO(b""), "TIFF")


def test_format_mismatch_not_decoded():
    src = _save(Image.new("RGB", (4, 4)), "PNG")
    with pytest.raises(UnidentifiedImageError):
        reencode_image(src, "JPEG")


def test_animated_webp_keeps_frames_and_timing():
    src = io.BytesIO()
    frames = [Image.new("RGB", (8, 8), c) for c in ("red", "blue")]
    frames[0].save(src, "WEBP", save_all=True, append_images=frames[1:], duration=120, loop=3)
    out = reencode_image(io.BytesIO(src.getvalue()), "WEBP")
    with Image.open(io.BytesIO(out)) as img:
        assert img.format == "WEBP"
        assert img.n_frames == 2
        durations = []
        for index in range(img.n_frames):
            img.seek(index)
            img.load()
            durations.append(img.info.get("duration"))
        assert durations == [120, 120]
        assert img.info.get("loop") == 3
