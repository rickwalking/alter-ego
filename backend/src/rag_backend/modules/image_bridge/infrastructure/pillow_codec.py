"""Pillow ``ImageCodec`` (design sections 2.2 and 3.3).

``validate`` accepts PNG, JPEG or WEBP with each side 512-4096 px, checked
from the header before any pixel is decoded (no decompression bombs).
``normalize`` fits the image to exactly the requested size (``ImageOps.fit``,
LANCZOS) and encodes PNG, the artifact the OpenAI path produces.
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

from rag_backend.modules.image_bridge.constants import (
    ALLOWED_IMAGE_FORMATS,
    ERR_IMAGE_DIMENSIONS,
    ERR_IMAGE_FORMAT,
    ERR_IMAGE_UNREADABLE,
    MAX_IMAGE_SIDE,
    MIN_IMAGE_SIDE,
    OUTPUT_IMAGE_FORMAT,
)
from rag_backend.modules.image_bridge.domain.exceptions import (
    InvalidCallbackImageError,
)
from rag_backend.modules.image_bridge.domain.ports import NormalizeRequest

_RGB_MODES = frozenset({"RGB", "RGBA"})
_RGB = "RGB"


class PillowImageCodec:
    """Decode, validate and normalize callback images."""

    @staticmethod
    def validate(image: bytes) -> None:
        """Raise ``InvalidCallbackImageError`` unless the image is acceptable."""
        with _open(image) as img:
            if img.format not in ALLOWED_IMAGE_FORMATS:
                raise InvalidCallbackImageError(ERR_IMAGE_FORMAT.format(fmt=img.format))
            width, height = img.size
            if not _side_ok(width) or not _side_ok(height):
                raise InvalidCallbackImageError(
                    ERR_IMAGE_DIMENSIONS.format(width=width, height=height)
                )
            _load(img)

    @staticmethod
    def normalize(request: NormalizeRequest) -> bytes:
        """The image fitted to exactly ``width`` x ``height``, as PNG bytes."""
        with _open(request.image) as img:
            source = img if img.mode in _RGB_MODES else img.convert(_RGB)
            fitted = ImageOps.fit(
                source,
                (request.width, request.height),
                method=Image.Resampling.LANCZOS,
            )
            out = io.BytesIO()
            fitted.save(out, format=OUTPUT_IMAGE_FORMAT)
            return out.getvalue()


def _open(image: bytes) -> Image.Image:
    """``Image.open`` reads only the header, and the side check in ``validate`` runs
    before any pixel is decoded, so it doubles as the pixel cap.
    """
    try:
        return Image.open(io.BytesIO(image))
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise InvalidCallbackImageError(ERR_IMAGE_UNREADABLE) from exc


def _load(img: Image.Image) -> None:
    try:
        img.load()
    except (OSError, ValueError) as exc:
        raise InvalidCallbackImageError(ERR_IMAGE_UNREADABLE) from exc


def _side_ok(side: int) -> bool:
    return MIN_IMAGE_SIDE <= side <= MAX_IMAGE_SIDE
