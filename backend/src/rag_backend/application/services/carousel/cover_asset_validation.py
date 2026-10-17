"""Validate and normalise a GrokBot slide-1 cover upload (AE-0418, ADR-0024).

The real bytes decide the format (PNG or JPEG only, never the declared type).
An ``ai_image`` is centre-cropped to 4:5 and must be at least 1080x1350 after
the crop; it is then scaled to exactly 1080x1350, the slide size. A
``screenshot`` keeps its aspect and needs 600 px of width. Both are bounded by
the creator-asset maxima and re-encoded to WebP, which drops EXIF and every
other metadata block.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from rag_backend.application.services.carousel.creator_asset_validation import (
    NormalizedCreatorAsset,
)
from rag_backend.domain.constants.carousel import IMAGE_FORMAT_WEBP
from rag_backend.domain.constants.creator_asset import (
    CREATOR_ASSET_JPEG_MAGIC,
    CREATOR_ASSET_MAX_BYTES,
    CREATOR_ASSET_MAX_DIMENSION,
    CREATOR_ASSET_MAX_PIXELS,
    CREATOR_ASSET_MEDIA_TYPE_WEBP,
    CREATOR_ASSET_PNG_MAGIC,
    build_staged_creator_asset_relative_path,
)
from rag_backend.domain.constants.slide_cover import (
    COVER_AI_MIN_HEIGHT,
    COVER_AI_MIN_WIDTH,
    COVER_AI_RATIO_HEIGHT,
    COVER_AI_RATIO_WIDTH,
    COVER_KIND_AI_IMAGE,
    COVER_SCREENSHOT_MIN_WIDTH,
    ERR_COVER_ASSET_TOO_LARGE,
    ERR_COVER_ASSET_TOO_SMALL,
    ERR_COVER_ASSET_TYPE_UNSUPPORTED,
)
from rag_backend.domain.models.slide_cover import CoverAssetError

if TYPE_CHECKING:
    from PIL.Image import Image as PilImage

_WEBP_QUALITY = 90
_WEBP_METHOD = 6
_MODE_RGB = "RGB"
_MODE_RGBA = "RGBA"
_ALPHA_MODES: frozenset[str] = frozenset({"RGBA", "LA", "PA", "RGBa", "La"})
_TRANSPARENCY_KEY = "transparency"


@dataclass(frozen=True)
class CoverImageUpload:
    """The uploaded bytes and the cover kind (already a known kind)."""

    content: bytes
    kind: str


def validate_cover_image(upload: CoverImageUpload) -> NormalizedCreatorAsset:
    """The re-encoded WebP of a valid cover; raises ``CoverAssetError``."""
    _check_bytes(upload.content)
    image = _decoded(upload.content)
    shaped = _shaped(image, upload.kind)
    return _normalized(shaped)


def _check_bytes(content: bytes) -> None:
    if len(content) > CREATOR_ASSET_MAX_BYTES:
        raise CoverAssetError(ERR_COVER_ASSET_TOO_LARGE)
    if not content.startswith((CREATOR_ASSET_JPEG_MAGIC, CREATOR_ASSET_PNG_MAGIC)):
        raise CoverAssetError(ERR_COVER_ASSET_TYPE_UNSUPPORTED)


def _decoded(content: bytes) -> PilImage:
    """One oriented frame, within the dimension and pixel budgets."""
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = CREATOR_ASSET_MAX_PIXELS
    try:
        with Image.open(BytesIO(content)) as opened:
            _check_dimensions(opened.size)
            oriented = ImageOps.exif_transpose(opened)
            return oriented.convert(_target_mode(oriented))
    except CoverAssetError:
        raise
    except Image.DecompressionBombError:
        raise CoverAssetError(ERR_COVER_ASSET_TOO_LARGE) from None
    except (OSError, ValueError):
        raise CoverAssetError(ERR_COVER_ASSET_TYPE_UNSUPPORTED) from None


def _check_dimensions(size: tuple[int, int]) -> None:
    width, height = size
    if max(width, height) > CREATOR_ASSET_MAX_DIMENSION:
        raise CoverAssetError(ERR_COVER_ASSET_TOO_LARGE)
    if width * height > CREATOR_ASSET_MAX_PIXELS:
        raise CoverAssetError(ERR_COVER_ASSET_TOO_LARGE)


def _target_mode(image: PilImage) -> str:
    """RGBA when the image carries alpha (a logo cut-out), else RGB."""
    has_key = _TRANSPARENCY_KEY in image.info
    return _MODE_RGBA if image.mode in _ALPHA_MODES or has_key else _MODE_RGB


def _shaped(image: PilImage, kind: str) -> PilImage:
    if kind == COVER_KIND_AI_IMAGE:
        return _ai_image(image)
    if image.width < COVER_SCREENSHOT_MIN_WIDTH:
        raise CoverAssetError(ERR_COVER_ASSET_TOO_SMALL)
    return image


def _ai_image(image: PilImage) -> PilImage:
    """Centre crop to 4:5, check the minimum, scale to the slide size."""
    from PIL import Image

    box = centre_crop_box(image.width, image.height)
    cropped = image.crop(box).convert(_MODE_RGB)
    if cropped.width < COVER_AI_MIN_WIDTH or cropped.height < COVER_AI_MIN_HEIGHT:
        raise CoverAssetError(ERR_COVER_ASSET_TOO_SMALL)
    size = (COVER_AI_MIN_WIDTH, COVER_AI_MIN_HEIGHT)
    return cropped.resize(size, Image.Resampling.LANCZOS)


def centre_crop_box(width: int, height: int) -> tuple[int, int, int, int]:
    """The largest centred 4:5 box inside ``width`` x ``height``."""
    if width * COVER_AI_RATIO_HEIGHT > height * COVER_AI_RATIO_WIDTH:
        crop_width = height * COVER_AI_RATIO_WIDTH // COVER_AI_RATIO_HEIGHT
        left = (width - crop_width) // 2
        return (left, 0, left + crop_width, height)
    crop_height = width * COVER_AI_RATIO_HEIGHT // COVER_AI_RATIO_WIDTH
    top = (height - crop_height) // 2
    return (0, top, width, top + crop_height)


def _normalized(image: PilImage) -> NormalizedCreatorAsset:
    buffer = BytesIO()
    image.save(
        buffer, format=IMAGE_FORMAT_WEBP, quality=_WEBP_QUALITY, method=_WEBP_METHOD
    )
    webp = buffer.getvalue()
    digest = hashlib.sha256(webp).hexdigest()
    return NormalizedCreatorAsset(
        content_sha256=digest,
        media_type=CREATOR_ASSET_MEDIA_TYPE_WEBP,
        width=image.width,
        height=image.height,
        relative_path=build_staged_creator_asset_relative_path(digest),
        webp_bytes=webp,
    )


__all__ = [
    "CoverAssetError",
    "CoverImageUpload",
    "centre_crop_box",
    "validate_cover_image",
]
