"""Unit tests for managed creator asset upload validation.

Feature: Versioned carousel presentation contract
Scenario: Invalid creator uploads are rejected before persistence
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.creator_asset_validation import (
    CreatorAssetUpload,
    CreatorAssetValidationError,
    validate_and_normalize_creator_asset,
)
from rag_backend.domain.constants.carousel_presentation import (
    CREATOR_ASSET_MEDIA_TYPE_WEBP,
)
from rag_backend.domain.constants.creator_asset import (
    CREATOR_ASSET_MAX_BYTES,
    CREATOR_ASSET_MAX_DIMENSION,
    CREATOR_ASSET_MIME_JPEG,
    CREATOR_ASSET_MIME_PNG,
    CREATOR_ASSET_MIME_WEBP,
    ERR_CREATOR_ASSET_ANIMATED,
    ERR_CREATOR_ASSET_DECODE_FAILED,
    ERR_CREATOR_ASSET_DECOMPRESSION_BOMB,
    ERR_CREATOR_ASSET_DIMENSIONS_EXCEEDED,
    ERR_CREATOR_ASSET_EMPTY,
    ERR_CREATOR_ASSET_MAGIC_MISMATCH,
    ERR_CREATOR_ASSET_MIME_NOT_ALLOWED,
    ERR_CREATOR_ASSET_TOO_LARGE,
    ERR_CREATOR_ASSET_TRUNCATED,
    build_staged_creator_asset_relative_path,
)


def _make_png_bytes(width: int = 64, height: int = 64) -> bytes:
    from PIL import Image

    buffer = __import__("io").BytesIO()
    Image.new("RGB", (width, height), color="green").save(buffer, format="PNG")
    return buffer.getvalue()


def _make_jpeg_bytes(width: int = 64, height: int = 64) -> bytes:
    from PIL import Image

    buffer = __import__("io").BytesIO()
    Image.new("RGB", (width, height), color="blue").save(buffer, format="JPEG")
    return buffer.getvalue()


def _make_webp_bytes(width: int = 64, height: int = 64) -> bytes:
    from PIL import Image

    buffer = __import__("io").BytesIO()
    Image.new("RGB", (width, height), color="red").save(buffer, format="WEBP")
    return buffer.getvalue()


def _make_animated_gif_bytes() -> bytes:
    from PIL import Image

    buffer = __import__("io").BytesIO()
    frames = [
        Image.new("RGB", (32, 32), color="red"),
        Image.new("RGB", (32, 32), color="blue"),
    ]
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=[frames[1]],
        duration=100,
        loop=0,
    )
    return buffer.getvalue()


@pytest.mark.unit
class TestCreatorAssetValidationRejections:
    def test_rejects_empty_upload(self) -> None:
        with pytest.raises(CreatorAssetValidationError) as exc_info:
            validate_and_normalize_creator_asset(
                CreatorAssetUpload(content=b"", declared_mime=CREATOR_ASSET_MIME_PNG)
            )
        assert exc_info.value.code == ERR_CREATOR_ASSET_EMPTY

    def test_rejects_oversized_upload(self) -> None:
        oversized = b"x" * (CREATOR_ASSET_MAX_BYTES + 1)
        with pytest.raises(CreatorAssetValidationError) as exc_info:
            validate_and_normalize_creator_asset(
                CreatorAssetUpload(
                    content=oversized, declared_mime=CREATOR_ASSET_MIME_PNG
                )
            )
        assert exc_info.value.code == ERR_CREATOR_ASSET_TOO_LARGE

    def test_rejects_disallowed_mime(self) -> None:
        with pytest.raises(CreatorAssetValidationError) as exc_info:
            validate_and_normalize_creator_asset(
                CreatorAssetUpload(content=_make_png_bytes(), declared_mime="image/gif")
            )
        assert exc_info.value.code == ERR_CREATOR_ASSET_MIME_NOT_ALLOWED

    def test_rejects_magic_bytes_mismatch(self) -> None:
        with pytest.raises(CreatorAssetValidationError) as exc_info:
            validate_and_normalize_creator_asset(
                CreatorAssetUpload(
                    content=_make_png_bytes(), declared_mime=CREATOR_ASSET_MIME_JPEG
                )
            )
        assert exc_info.value.code == ERR_CREATOR_ASSET_MAGIC_MISMATCH

    def test_rejects_dimensions_exceeded(self) -> None:
        width = CREATOR_ASSET_MAX_DIMENSION + 1
        with pytest.raises(CreatorAssetValidationError) as exc_info:
            validate_and_normalize_creator_asset(
                CreatorAssetUpload(
                    content=_make_png_bytes(width=width, height=64),
                    declared_mime=CREATOR_ASSET_MIME_PNG,
                )
            )
        assert exc_info.value.code == ERR_CREATOR_ASSET_DIMENSIONS_EXCEEDED

    def test_rejects_animated_input(self) -> None:
        with pytest.raises(CreatorAssetValidationError) as exc_info:
            validate_and_normalize_creator_asset(
                CreatorAssetUpload(
                    content=_make_animated_gif_bytes(),
                    declared_mime=CREATOR_ASSET_MIME_PNG,
                )
            )
        assert exc_info.value.code in {
            ERR_CREATOR_ASSET_ANIMATED,
            ERR_CREATOR_ASSET_MAGIC_MISMATCH,
            ERR_CREATOR_ASSET_DECODE_FAILED,
        }

    def test_rejects_truncated_file(self) -> None:
        truncated = _make_jpeg_bytes()[:32]
        with pytest.raises(CreatorAssetValidationError) as exc_info:
            validate_and_normalize_creator_asset(
                CreatorAssetUpload(
                    content=truncated, declared_mime=CREATOR_ASSET_MIME_JPEG
                )
            )
        assert exc_info.value.code in {
            ERR_CREATOR_ASSET_TRUNCATED,
            ERR_CREATOR_ASSET_DECODE_FAILED,
        }

    def test_rejects_decompression_bomb(self) -> None:
        from PIL import Image

        width = 5000
        height = 5000
        buffer = __import__("io").BytesIO()
        Image.new("RGB", (width, height), color="white").save(buffer, format="PNG")
        with pytest.raises(CreatorAssetValidationError) as exc_info:
            validate_and_normalize_creator_asset(
                CreatorAssetUpload(
                    content=buffer.getvalue(), declared_mime=CREATOR_ASSET_MIME_PNG
                )
            )
        assert exc_info.value.code in {
            ERR_CREATOR_ASSET_DECOMPRESSION_BOMB,
            ERR_CREATOR_ASSET_DIMENSIONS_EXCEEDED,
        }


@pytest.mark.unit
class TestCreatorAssetValidationSuccess:
    def test_normalizes_valid_png_to_webp(self) -> None:
        normalized = validate_and_normalize_creator_asset(
            CreatorAssetUpload(
                content=_make_png_bytes(), declared_mime=CREATOR_ASSET_MIME_PNG
            )
        )
        assert normalized.media_type == CREATOR_ASSET_MEDIA_TYPE_WEBP
        assert normalized.width == 64
        assert normalized.height == 64
        assert normalized.relative_path == build_staged_creator_asset_relative_path(
            normalized.content_sha256
        )
        assert normalized.webp_bytes.startswith(b"RIFF")

    def test_normalizes_valid_jpeg_to_webp(self) -> None:
        normalized = validate_and_normalize_creator_asset(
            CreatorAssetUpload(
                content=_make_jpeg_bytes(), declared_mime=CREATOR_ASSET_MIME_JPEG
            )
        )
        assert normalized.media_type == CREATOR_ASSET_MEDIA_TYPE_WEBP
        assert len(normalized.content_sha256) == 64

    def test_normalizes_valid_webp_input(self) -> None:
        normalized = validate_and_normalize_creator_asset(
            CreatorAssetUpload(
                content=_make_webp_bytes(), declared_mime=CREATOR_ASSET_MIME_WEBP
            )
        )
        assert normalized.media_type == CREATOR_ASSET_MEDIA_TYPE_WEBP
