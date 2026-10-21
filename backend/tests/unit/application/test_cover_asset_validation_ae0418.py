"""GrokBot cover upload validation (ADR-0024).

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
  Upload: POST /api/autopilot/assets (image rules)
"""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from rag_backend.application.services.carousel.cover_asset_validation import (
    CoverImageUpload,
    centre_crop_box,
    validate_cover_image,
)
from rag_backend.domain.models.slide_cover import CoverAssetError

_EXIF_ORIENTATION = 0x0112
_EXIF_ARTIST = 0x013B


def _bytes(size: tuple[int, int], fmt: str = "PNG", mode: str = "RGB") -> bytes:
    buffer = BytesIO()
    Image.new(mode, size, (10, 20, 30, 128)[: len(mode)]).save(buffer, format=fmt)
    return buffer.getvalue()


def _code(content: bytes, kind: str = "ai_image") -> str:
    with pytest.raises(CoverAssetError) as raised:
        validate_cover_image(CoverImageUpload(content=content, kind=kind))
    return raised.value.code


@pytest.mark.parametrize(
    ("size", "box"),
    [
        ((1080, 1350), (0, 0, 1080, 1350)),
        ((2000, 1350), (460, 0, 1540, 1350)),
        ((1080, 2000), (0, 325, 1080, 1675)),
        ((1200, 1200), (120, 0, 1080, 1200)),
    ],
)
def test_centre_crop_box(size: tuple[int, int], box: tuple[int, int, int, int]) -> None:
    assert centre_crop_box(*size) == box


def test_ai_image_is_cropped_and_scaled_to_the_slide() -> None:
    normalized = validate_cover_image(
        CoverImageUpload(content=_bytes((2160, 2700), "JPEG"), kind="ai_image")
    )
    assert (normalized.width, normalized.height) == (1080, 1350)
    assert normalized.media_type == "image/webp"
    assert normalized.relative_path == (
        f"assets/creators/{normalized.content_sha256}.webp"
    )
    with Image.open(BytesIO(normalized.webp_bytes)) as decoded:
        assert decoded.format == "WEBP"
        assert decoded.size == (1080, 1350)


def test_ai_image_too_small_after_the_crop() -> None:
    assert _code(_bytes((1200, 1200))) == "asset_too_small"
    assert _code(_bytes((1079, 1350))) == "asset_too_small"


def test_screenshot_keeps_its_aspect_and_alpha() -> None:
    normalized = validate_cover_image(
        CoverImageUpload(content=_bytes((800, 400), mode="RGBA"), kind="screenshot")
    )
    assert (normalized.width, normalized.height) == (800, 400)
    with Image.open(BytesIO(normalized.webp_bytes)) as decoded:
        assert decoded.mode == "RGBA"


def test_screenshot_needs_600_pixels_of_width() -> None:
    assert _code(_bytes((599, 2000)), "screenshot") == "asset_too_small"
    ok = validate_cover_image(
        CoverImageUpload(content=_bytes((600, 300)), kind="screenshot")
    )
    assert ok.width == 600


def test_size_and_dimension_limits() -> None:
    assert _code(b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024)) == "asset_too_large"
    assert _code(_bytes((4097, 100)), "screenshot") == "asset_too_large"
    assert _code(_bytes((4096, 4000)), "screenshot") == "asset_too_large"


def test_only_real_png_or_jpeg_bytes() -> None:
    assert _code(_bytes((1080, 1350), "WEBP")) == "asset_type_unsupported"
    assert _code(_bytes((1080, 1350), "GIF", mode="L")) == "asset_type_unsupported"
    assert _code(b"") == "asset_type_unsupported"
    assert _code(b"\x89PNG\r\n\x1a\n" + b"broken") == "asset_type_unsupported"


def test_decompression_bomb_is_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    from PIL import Image as PilImage

    def _bomb(*_args: object, **_kwargs: object) -> None:
        raise PilImage.DecompressionBombError("bomb")

    monkeypatch.setattr(PilImage, "open", _bomb)
    assert _code(_bytes((1080, 1350))) == "asset_too_large"


def test_metadata_is_stripped() -> None:
    image = Image.new("RGB", (1080, 1350), (1, 2, 3))
    exif = image.getexif()
    exif[_EXIF_ARTIST] = "secret camera owner"
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    normalized = validate_cover_image(
        CoverImageUpload(content=buffer.getvalue(), kind="ai_image")
    )
    assert b"secret camera owner" not in normalized.webp_bytes
    with Image.open(BytesIO(normalized.webp_bytes)) as decoded:
        assert not decoded.getexif()
