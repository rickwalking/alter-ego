"""Pillow validation and normalization (design 2.2 and 3.3).

Gherkin: tests/features/image_bridge.feature
  Scenario: Grok Bot returns an image (written at the requested size)
  Scenario: Invalid image
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from rag_backend.modules.image_bridge.domain.exceptions import (
    InvalidCallbackImageError,
)
from rag_backend.modules.image_bridge.domain.ports import NormalizeRequest
from rag_backend.modules.image_bridge.infrastructure.pillow_codec import (
    PillowImageCodec,
)
from tests.unit.modules.image_bridge.support import png_bytes

codec = PillowImageCodec()


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_allowed_formats_validate(fmt: str) -> None:
    codec.validate(png_bytes((1122, 1402), fmt))


@pytest.mark.parametrize("size", [(512, 512), (4096, 600)])
def test_sides_at_the_bounds_validate(size: tuple[int, int]) -> None:
    codec.validate(png_bytes(size))


@pytest.mark.parametrize("size", [(511, 1024), (1024, 4097), (100, 100)])
def test_sides_out_of_bounds_are_rejected(size: tuple[int, int]) -> None:
    with pytest.raises(InvalidCallbackImageError, match="512-4096"):
        codec.validate(png_bytes(size))


def test_other_formats_are_rejected() -> None:
    with pytest.raises(InvalidCallbackImageError, match="GIF"):
        codec.validate(png_bytes((600, 600), "GIF"))


@pytest.mark.parametrize("data", [b"", b"not an image", b"\x89PNG\r\n\x1a\n"])
def test_garbage_is_rejected(data: bytes) -> None:
    with pytest.raises(InvalidCallbackImageError):
        codec.validate(data)


def test_truncated_image_is_rejected_on_load() -> None:
    data = png_bytes((800, 800), "JPEG")
    with pytest.raises(InvalidCallbackImageError):
        codec.validate(data[: len(data) // 3])


def test_header_claiming_a_huge_image_is_rejected_before_decoding() -> None:
    """A tiny file whose header claims 20000x20000 never gets decoded.

    The IHDR width/height live at bytes 16..24 of a PNG.
    """
    data = bytearray(png_bytes((600, 600)))
    data[16:24] = (20000).to_bytes(4, "big") + (20000).to_bytes(4, "big")
    with pytest.raises(InvalidCallbackImageError):
        codec.validate(bytes(data))


@pytest.mark.parametrize("source", [(1122, 1402), (2048, 512), (1536, 1024)])
def test_normalize_fits_exactly_the_requested_size_as_png(
    source: tuple[int, int],
) -> None:
    out = codec.normalize(NormalizeRequest(png_bytes(source, "JPEG"), 1536, 1024))
    with Image.open(io.BytesIO(out)) as img:
        assert img.format == "PNG"
        assert img.size == (1536, 1024)


@pytest.mark.parametrize("mode", ["L", "P", "RGBA", "CMYK"])
def test_normalize_handles_any_colour_mode(mode: str) -> None:
    buffer = io.BytesIO()
    fmt = "JPEG" if mode == "CMYK" else "PNG"
    Image.new(mode, (700, 900)).save(buffer, format=fmt)
    out = codec.normalize(NormalizeRequest(buffer.getvalue(), 1536, 1024))
    with Image.open(io.BytesIO(out)) as img:
        assert img.size == (1536, 1024)
        assert img.mode in {"RGB", "RGBA"}
