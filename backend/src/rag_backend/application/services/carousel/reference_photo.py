"""Re-encode a stored library photo for the Grok Bot (image-to-image).

The stored WebP is decoded under the creator pixel budget, scaled down to at
most ``REFERENCE_PHOTO_MAX_SIDE`` px a side and written as a fresh PNG, so no
metadata block (EXIF, GPS, XMP, ICC) of the original leaves the app and the
webhook body stays small. Transparency is kept (cut-out photos).
"""

from __future__ import annotations

from io import BytesIO

from rag_backend.application.services.carousel.creator_asset_validation import (
    open_within_pixel_budget,
)
from rag_backend.domain.constants.cover_generation import (
    REFERENCE_PHOTO_MAX_SIDE,
    REFERENCE_PHOTO_MIME_TYPE,
)
from rag_backend.domain.constants.slide_cover import ERR_COVER_ASSET_TYPE_UNSUPPORTED
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
    image.thumbnail(
        (REFERENCE_PHOTO_MAX_SIDE, REFERENCE_PHOTO_MAX_SIDE),
        Image.Resampling.LANCZOS,
    )
    buffer = BytesIO()
    image.save(buffer, format=_PNG, optimize=True)
    return ReferencePhoto(
        content=buffer.getvalue(), mime_type=REFERENCE_PHOTO_MIME_TYPE
    )


__all__ = ["reference_photo"]
