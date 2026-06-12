"""Constants for managed carousel creator branding assets."""

CREATOR_ASSET_MAX_BYTES = 5 * 1024 * 1024
CREATOR_ASSET_MAX_DIMENSION = 4096
CREATOR_ASSET_MAX_PIXELS = 16_000_000

CREATOR_ASSET_MIME_JPEG = "image/jpeg"
CREATOR_ASSET_MIME_PNG = "image/png"
CREATOR_ASSET_MIME_WEBP = "image/webp"

# Image format magic bytes used to confirm declared MIME types.
CREATOR_ASSET_JPEG_MAGIC = b"\xff\xd8\xff"
CREATOR_ASSET_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
CREATOR_ASSET_RIFF_MAGIC = b"RIFF"
CREATOR_ASSET_WEBP_MAGIC = b"WEBP"
CREATOR_ASSET_WEBP_MAGIC_OFFSET = 8
CREATOR_ASSET_WEBP_MIN_HEADER_LENGTH = 12

ALLOWED_CREATOR_ASSET_MIME_TYPES: frozenset[str] = frozenset({
    CREATOR_ASSET_MIME_JPEG,
    CREATOR_ASSET_MIME_PNG,
    CREATOR_ASSET_MIME_WEBP,
})

ARTIFACT_ASSETS_DIR = "assets"
CREATOR_ASSETS_SUBDIR = "creators"
CREATOR_ASSET_FILENAME_SUFFIX = ".webp"

ERR_CREATOR_ASSET_EMPTY = "creator_asset_empty"
ERR_CREATOR_ASSET_TOO_LARGE = "creator_asset_too_large"
ERR_CREATOR_ASSET_MIME_NOT_ALLOWED = "creator_asset_mime_not_allowed"
ERR_CREATOR_ASSET_MAGIC_MISMATCH = "creator_asset_magic_bytes_mismatch"
ERR_CREATOR_ASSET_DECODE_FAILED = "creator_asset_decode_failed"
ERR_CREATOR_ASSET_DIMENSIONS_EXCEEDED = "creator_asset_dimensions_exceeded"
ERR_CREATOR_ASSET_PIXEL_BUDGET_EXCEEDED = "creator_asset_pixel_budget_exceeded"
ERR_CREATOR_ASSET_ANIMATED = "creator_asset_animated"
ERR_CREATOR_ASSET_DECOMPRESSION_BOMB = "creator_asset_decompression_bomb"
ERR_CREATOR_ASSET_TRUNCATED = "creator_asset_truncated"
ERR_CREATOR_ASSET_NOT_FOUND = "creator_asset_not_found"
ERR_CREATOR_ASSET_FORBIDDEN = "creator_asset_forbidden"
ERR_CREATOR_ASSET_URL_REJECTED = "creator_asset_url_rejected"
ERR_CREATOR_ASSET_PATH_REJECTED = "creator_asset_path_rejected"


def build_creator_asset_filename(content_sha256: str) -> str:
    """Return the content-addressed WebP filename for a creator asset."""
    return f"{content_sha256}{CREATOR_ASSET_FILENAME_SUFFIX}"


def build_staged_creator_asset_relative_path(content_sha256: str) -> str:
    """Return the artifact-relative path for a staged creator avatar."""
    return (
        f"{ARTIFACT_ASSETS_DIR}/{CREATOR_ASSETS_SUBDIR}/"
        f"{build_creator_asset_filename(content_sha256)}"
    )


__all__ = [
    "ALLOWED_CREATOR_ASSET_MIME_TYPES",
    "ARTIFACT_ASSETS_DIR",
    "CREATOR_ASSETS_SUBDIR",
    "CREATOR_ASSET_FILENAME_SUFFIX",
    "CREATOR_ASSET_JPEG_MAGIC",
    "CREATOR_ASSET_MAX_BYTES",
    "CREATOR_ASSET_MAX_DIMENSION",
    "CREATOR_ASSET_MAX_PIXELS",
    "CREATOR_ASSET_MIME_JPEG",
    "CREATOR_ASSET_MIME_PNG",
    "CREATOR_ASSET_MIME_WEBP",
    "CREATOR_ASSET_PNG_MAGIC",
    "CREATOR_ASSET_RIFF_MAGIC",
    "CREATOR_ASSET_WEBP_MAGIC",
    "CREATOR_ASSET_WEBP_MAGIC_OFFSET",
    "CREATOR_ASSET_WEBP_MIN_HEADER_LENGTH",
    "ERR_CREATOR_ASSET_ANIMATED",
    "ERR_CREATOR_ASSET_DECODE_FAILED",
    "ERR_CREATOR_ASSET_DECOMPRESSION_BOMB",
    "ERR_CREATOR_ASSET_DIMENSIONS_EXCEEDED",
    "ERR_CREATOR_ASSET_EMPTY",
    "ERR_CREATOR_ASSET_FORBIDDEN",
    "ERR_CREATOR_ASSET_MAGIC_MISMATCH",
    "ERR_CREATOR_ASSET_MIME_NOT_ALLOWED",
    "ERR_CREATOR_ASSET_NOT_FOUND",
    "ERR_CREATOR_ASSET_PATH_REJECTED",
    "ERR_CREATOR_ASSET_PIXEL_BUDGET_EXCEEDED",
    "ERR_CREATOR_ASSET_TOO_LARGE",
    "ERR_CREATOR_ASSET_TRUNCATED",
    "ERR_CREATOR_ASSET_URL_REJECTED",
    "build_creator_asset_filename",
    "build_staged_creator_asset_relative_path",
]
