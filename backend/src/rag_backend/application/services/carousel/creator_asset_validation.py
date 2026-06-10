"""Validation and normalization for managed creator branding uploads."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO

from rag_backend.domain.constants.carousel_presentation import (
    CREATOR_ASSET_MEDIA_TYPE_WEBP,
)
from rag_backend.domain.constants.creator_asset import (
    ALLOWED_CREATOR_ASSET_MIME_TYPES,
    CREATOR_ASSET_MAX_BYTES,
    CREATOR_ASSET_MAX_DIMENSION,
    CREATOR_ASSET_MAX_PIXELS,
    CREATOR_ASSET_MIME_JPEG,
    CREATOR_ASSET_MIME_PNG,
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

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_WEBP_MAGIC_OFFSET = 8
_WEBP_MIN_HEADER_LENGTH = 12
_WEBP_MAGIC = b"WEBP"


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


def validate_and_normalize_creator_asset(upload: CreatorAssetUpload) -> NormalizedCreatorAsset:
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
    if content.startswith(_JPEG_MAGIC):
        return "JPEG"
    if content.startswith(_PNG_MAGIC):
        return "PNG"
    if (
        len(content) >= _WEBP_MIN_HEADER_LENGTH
        and content[:4] == b"RIFF"
        and content[_WEBP_MAGIC_OFFSET:_WEBP_MIN_HEADER_LENGTH] == _WEBP_MAGIC
    ):
        return "WEBP"
    return None


def _mime_to_format(declared_mime: str) -> str:
    if declared_mime == CREATOR_ASSET_MIME_JPEG:
        return "JPEG"
    if declared_mime == CREATOR_ASSET_MIME_PNG:
        return "PNG"
    return "WEBP"


def _reject_if_animated(image: object) -> None:
    if _is_animated(image):
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_ANIMATED)


def _decode_and_normalize(content: bytes) -> NormalizedCreatorAsset:
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = CREATOR_ASSET_MAX_PIXELS

    try:
        with Image.open(BytesIO(content)) as image:
            _reject_if_animated(image)
            width, height = image.size
            _validate_dimensions(width, height)
            oriented = ImageOps.exif_transpose(image)
            rgb = oriented.convert("RGB")
    except CreatorAssetValidationError:
        raise
    except Image.DecompressionBombError:
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_DECOMPRESSION_BOMB) from None
    except (OSError, ValueError):
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_TRUNCATED) from None
    except Exception:
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_DECODE_FAILED) from None

    buffer = BytesIO()
    try:
        rgb.save(buffer, format="WEBP", quality=90, method=6)
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
