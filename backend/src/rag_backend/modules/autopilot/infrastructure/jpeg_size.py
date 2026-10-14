"""JPEG width and height from the SOF marker.

Pillow is not a dependency. The runner only needs the dimensions of a
baseline or progressive JPEG, which sit in the SOF segment.
"""

from __future__ import annotations

from dataclasses import dataclass

_SOI = b"\xff\xd8"
_MARKER = 0xFF
_SOF_MARKERS = frozenset({0xC0, 0xC1, 0xC2})
_STANDALONE = frozenset({0xD8, 0xD9, 0x01})
_LENGTH_BYTES = 2
_HEIGHT_OFFSET = 3
_WIDTH_OFFSET = 5
_MIN_SOF = 9


@dataclass(frozen=True, kw_only=True)
class JpegSize:
    """Pixel size of one JPEG."""

    width: int
    height: int


def jpeg_size(payload: bytes) -> JpegSize | None:
    """Return the SOF size, or None when the bytes are not a sized JPEG."""
    if not payload.startswith(_SOI):
        return None
    return _scan(payload, len(_SOI))


def _scan(payload: bytes, index: int) -> JpegSize | None:
    while index + 1 < len(payload):
        if payload[index] != _MARKER:
            return None
        marker = payload[index + 1]
        index += 2
        if marker in _STANDALONE:
            continue
        found = _segment(payload, index, marker)
        if isinstance(found, JpegSize):
            return found
        if found is None:
            return None
        index = found
    return None


def _segment(payload: bytes, index: int, marker: int) -> JpegSize | int | None:
    if index + _LENGTH_BYTES > len(payload):
        return None
    length = int.from_bytes(payload[index : index + _LENGTH_BYTES], "big")
    if length < _LENGTH_BYTES or index + length > len(payload):
        return None
    if marker in _SOF_MARKERS:
        return _sof(payload, index, length)
    return index + length


def _sof(payload: bytes, index: int, length: int) -> JpegSize | None:
    if length < _MIN_SOF or index + _WIDTH_OFFSET + 2 > len(payload):
        return None
    height_at = index + _HEIGHT_OFFSET
    width_at = index + _WIDTH_OFFSET
    height = int.from_bytes(payload[height_at:width_at], "big")
    width = int.from_bytes(payload[width_at : width_at + 2], "big")
    return JpegSize(width=width, height=height)
