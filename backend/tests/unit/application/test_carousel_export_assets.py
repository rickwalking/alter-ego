"""Unit tests for carousel export asset preparation."""

from pathlib import Path

import pytest

from rag_backend.application.services.carousel import carousel_export_assets as assets


class TestCarouselExportAssets:
    def test_copies_default_avatar_when_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = tmp_path / "source.jpg"
        source.write_bytes(b"avatar-bytes")
        monkeypatch.setattr(assets, "_AVATAR_SOURCE_CANDIDATES", (source,))

        assets.ensure_cta_avatar_image(tmp_path)

        target = tmp_path / "images" / "about-pedro.jpg"
        assert target.is_file()
        assert target.read_bytes() == b"avatar-bytes"

    def test_prepare_assets_optimizes_existing_slide_images(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from PIL import Image

        source = tmp_path / "source.jpg"
        source.write_bytes(b"avatar-bytes")
        monkeypatch.setattr(assets, "_AVATAR_SOURCE_CANDIDATES", (source,))
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        image_path = images_dir / "slide_1.jpg"
        Image.new("RGB", (2400, 2400), color=(10, 20, 30)).save(image_path, "JPEG")

        assets.prepare_carousel_export_assets(tmp_path)

        assert image_path.is_file()
        assert image_path.stat().st_size > 0
        assert (tmp_path / "images" / "about-pedro.jpg").is_file()
