"""Validation and normalization for managed creator branding uploads."""

from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from rag_backend.domain.constants.carousel import (
    IMAGE_FORMAT_JPEG,
    IMAGE_FORMAT_PNG,
    IMAGE_FORMAT_WEBP,
)
from rag_backend.domain.constants.carousel_presentation import (
    CREATOR_ASSET_MEDIA_TYPE_WEBP,
)
from rag_backend.domain.constants.creator_asset import (
    ALLOWED_CREATOR_ASSET_MIME_TYPES,
    CREATOR_ASSET_JPEG_MAGIC,
    CREATOR_ASSET_MAX_BYTES,
    CREATOR_ASSET_MAX_DIMENSION,
    CREATOR_ASSET_MAX_PIXELS,
    CREATOR_ASSET_MIME_JPEG,
    CREATOR_ASSET_MIME_PNG,
    CREATOR_ASSET_PNG_MAGIC,
    CREATOR_ASSET_RIFF_MAGIC,
    CREATOR_ASSET_WEBP_MAGIC,
    CREATOR_ASSET_WEBP_MAGIC_OFFSET,
    CREATOR_ASSET_WEBP_MIN_HEADER_LENGTH,
    ERR_CREATOR_ASSET_ANIMATED,
    ERR_CREATOR_ASSET_DECODE_FAILED,
    ERR_CREATOR_ASSET_DECOMPRESSION_BOMB,
    ERR_CREATOR_ASSET_DIMENSIONS_EXCEEDED,
    ERR_CREATOR_ASSET_EMPTY,
    ERR_CREATOR_ASSET_MAGIC_MISMATCH,
    ERR_CREATOR_ASSET_MIME_NOT_ALLOWED,
    ERR_CREATOR_ASSET_PIXEL_BUDGET_EXCEEDED,
    ERR_CREATOR_ASSET_TOO_LARGE,
    ERR_CREATOR_ASSET_TRUNCATED,
    build_staged_creator_asset_relative_path,
)

if TYPE_CHECKING:
    from PIL.Image import Image as PilImage

_WEBP_SAVE_QUALITY = 90
_WEBP_SAVE_METHOD = 6


class CreatorAssetValidationError(ValueError):
    """Raised when an uploaded creator asset fails validation."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class NormalizedCreatorAsset:
    content_sha256: str
    media_type: str
    width: int
    height: int
    relative_path: str
    webp_bytes: bytes


@dataclass(frozen=True)
class CreatorAssetUpload:
    content: bytes
    declared_mime: str


def validate_and_normalize_creator_asset(
    upload: CreatorAssetUpload,
) -> NormalizedCreatorAsset:
    """Validate upload bytes and normalize to single-frame sRGB WebP."""
    _validate_upload_size(upload.content)
    _validate_declared_mime(upload.declared_mime)
    _validate_magic_bytes(upload.content, upload.declared_mime)
    return _decode_and_normalize(upload.content)


def _validate_upload_size(content: bytes) -> None:
    if not content:
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_EMPTY)
    if len(content) > CREATOR_ASSET_MAX_BYTES:
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_TOO_LARGE)


def _validate_declared_mime(declared_mime: str) -> None:
    if declared_mime not in ALLOWED_CREATOR_ASSET_MIME_TYPES:
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_MIME_NOT_ALLOWED)


def _validate_magic_bytes(content: bytes, declared_mime: str) -> None:
    detected = _detect_format_from_magic(content)
    if detected is None:
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_MAGIC_MISMATCH)
    expected = _mime_to_format(declared_mime)
    if detected != expected:
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_MAGIC_MISMATCH)


def _detect_format_from_magic(content: bytes) -> str | None:
    if content.startswith(CREATOR_ASSET_JPEG_MAGIC):
        return IMAGE_FORMAT_JPEG
    if content.startswith(CREATOR_ASSET_PNG_MAGIC):
        return IMAGE_FORMAT_PNG
    riff_len = len(CREATOR_ASSET_RIFF_MAGIC)
    if (
        len(content) >= CREATOR_ASSET_WEBP_MIN_HEADER_LENGTH
        and content[:riff_len] == CREATOR_ASSET_RIFF_MAGIC
        and content[
            CREATOR_ASSET_WEBP_MAGIC_OFFSET:CREATOR_ASSET_WEBP_MIN_HEADER_LENGTH
        ]
        == CREATOR_ASSET_WEBP_MAGIC
    ):
        return IMAGE_FORMAT_WEBP
    return None


def _mime_to_format(declared_mime: str) -> str:
    if declared_mime == CREATOR_ASSET_MIME_JPEG:
        return IMAGE_FORMAT_JPEG
    if declared_mime == CREATOR_ASSET_MIME_PNG:
        return IMAGE_FORMAT_PNG
    return IMAGE_FORMAT_WEBP


def _reject_if_animated(image: object) -> None:
    if _is_animated(image):
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_ANIMATED)


_MODE_RGB = "RGB"
_MODE_RGBA = "RGBA"
_ALPHA_MODES: frozenset[str] = frozenset({"RGBA", "LA", "PA", "RGBa", "La"})
_TRANSPARENCY_INFO_KEY = "transparency"


def _target_mode(image: object) -> str:
    """RGBA when the image carries alpha (or a transparency key), else RGB."""
    mode = str(getattr(image, "mode", ""))
    info = getattr(image, "info", {})
    has_key = isinstance(info, dict) and _TRANSPARENCY_INFO_KEY in info
    return _MODE_RGBA if mode in _ALPHA_MODES or has_key else _MODE_RGB


def open_within_pixel_budget(content: bytes) -> PilImage:
    """Open (lazily, header only) an upload under the creator pixel budget.

    Pillow raises ``DecompressionBombError`` above 2x ``MAX_IMAGE_PIXELS`` and
    only *warns* between 1x and 2x. Callers reject that range themselves with a
    precise error code right after opening, so the warning is suppressed here.
    """
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = CREATOR_ASSET_MAX_PIXELS
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        return Image.open(BytesIO(content))


def _decode_and_normalize(content: bytes) -> NormalizedCreatorAsset:
    """Decode the upload, apply its EXIF orientation and normalize the colour mode.

    Transparency is kept so pre-cut PNG or WebP photos sit on the POV slide-1
    background; opaque images become RGB.
    """
    from PIL import Image, ImageOps

    try:
        with open_within_pixel_budget(content) as image:
            _reject_if_animated(image)
            width, height = image.size
            _validate_dimensions(width, height)
            oriented = ImageOps.exif_transpose(image)
            rgb = oriented.convert(_target_mode(oriented))
    except CreatorAssetValidationError:
        raise
    except Image.DecompressionBombError:
        raise CreatorAssetValidationError(
            ERR_CREATOR_ASSET_DECOMPRESSION_BOMB
        ) from None
    except (OSError, ValueError):
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_TRUNCATED) from None
    except Exception:
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_DECODE_FAILED) from None

    buffer = BytesIO()
    try:
        rgb.save(
            buffer,
            format=IMAGE_FORMAT_WEBP,
            quality=_WEBP_SAVE_QUALITY,
            method=_WEBP_SAVE_METHOD,
        )
    except (OSError, ValueError):
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_DECODE_FAILED) from None

    webp_bytes = buffer.getvalue()
    content_sha256 = hashlib.sha256(webp_bytes).hexdigest()
    return NormalizedCreatorAsset(
        content_sha256=content_sha256,
        media_type=CREATOR_ASSET_MEDIA_TYPE_WEBP,
        width=width,
        height=height,
        relative_path=build_staged_creator_asset_relative_path(content_sha256),
        webp_bytes=webp_bytes,
    )


def _is_animated(image: object) -> bool:
    is_animated = getattr(image, "is_animated", False)
    if bool(is_animated):
        return True
    n_frames = getattr(image, "n_frames", 1)
    return int(n_frames) > 1


def _validate_dimensions(width: int, height: int) -> None:
    if width > CREATOR_ASSET_MAX_DIMENSION or height > CREATOR_ASSET_MAX_DIMENSION:
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_DIMENSIONS_EXCEEDED)
    if width * height > CREATOR_ASSET_MAX_PIXELS:
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_PIXEL_BUDGET_EXCEEDED)


__all__ = [
    "CreatorAssetUpload",
    "CreatorAssetValidationError",
    "NormalizedCreatorAsset",
    "validate_and_normalize_creator_asset",
]
