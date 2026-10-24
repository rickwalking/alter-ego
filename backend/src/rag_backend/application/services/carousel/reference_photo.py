"""Re-encode a stored library photo for the Grok Bot (image-to-image).

The stored WebP is decoded under the creator pixel budget, scaled down to at
most 1024 px a side and written as a fresh PNG, so no metadata block (EXIF,
GPS, XMP, ICC) of the original leaves the app. A PNG over
``REFERENCE_PHOTO_MAX_BYTES`` is scaled down further (768, then 512 px), so
three photos keep the webhook body bounded. Transparency is kept (cut-out
photos).
"""

from __future__ import annotations

from io import BytesIO

from rag_backend.application.services.carousel.creator_asset_validation import (
    open_within_pixel_budget,
)
from rag_backend.domain.constants.cover_generation import (
    REFERENCE_PHOTO_MAX_BYTES,
    REFERENCE_PHOTO_MIME_TYPE,
    REFERENCE_PHOTO_SIDES,
)
from rag_backend.domain.constants.slide_cover import (
    ERR_COVER_ASSET_TOO_LARGE,
    ERR_COVER_ASSET_TYPE_UNSUPPORTED,
)
from rag_backend.domain.models.cover_generation import ReferencePhoto
from rag_backend.domain.models.slide_cover import CoverAssetError

_PNG = "PNG"
_MODE_RGBA = "RGBA"


def reference_photo(content: bytes) -> ReferencePhoto:
    """The photo as a metadata-free PNG; raises ``CoverAssetError`` when unreadable."""
    from PIL import Image

    try:
        with open_within_pixel_budget(content) as opened:
            image = opened.convert(_MODE_RGBA)
    except (OSError, ValueError, Image.DecompressionBombError):
        raise CoverAssetError(ERR_COVER_ASSET_TYPE_UNSUPPORTED) from None
    encoded = b""
    for side in REFERENCE_PHOTO_SIDES:
        image.thumbnail((side, side), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        image.save(buffer, format=_PNG, optimize=True)
        encoded = buffer.getvalue()
        if len(encoded) <= REFERENCE_PHOTO_MAX_BYTES:
            return ReferencePhoto(content=encoded, mime_type=REFERENCE_PHOTO_MIME_TYPE)
    raise CoverAssetError(ERR_COVER_ASSET_TOO_LARGE)


__all__ = ["reference_photo"]
