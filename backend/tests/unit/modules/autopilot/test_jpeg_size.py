"""JPEG SOF dimension parser (AE-0354)."""

from __future__ import annotations

from rag_backend.domain.constants.carousel import CAROUSEL_HEIGHT, CAROUSEL_WIDTH
from rag_backend.modules.autopilot.infrastructure.jpeg_size import jpeg_size

# SOF0: length 11, precision 8, height 1350 (0x0546), width 1080 (0x0438).
_JPEG = bytes([
    0xFF,
    0xD8,
    0xFF,
    0xC0,
    0x00,
    0x0B,
    0x08,
    0x05,
    0x46,
    0x04,
    0x38,
    0x01,
    0x01,
    0x11,
    0x00,
    0xFF,
    0xD9,
])


def test_baseline_sof_reports_carousel_dimensions() -> None:
    size = jpeg_size(_JPEG)
    assert size is not None
    assert size.width == CAROUSEL_WIDTH
    assert size.height == CAROUSEL_HEIGHT


def test_non_jpeg_and_truncated_marker_are_none() -> None:
    assert jpeg_size(b"not a jpeg") is None
    assert jpeg_size(b"\xff\xd8\xff") is None
