"""Unit tests for carousel image node helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_backend.application.services.carousel.nodes.images import (
    _ensure_jpeg_format,
    filter_image_slides,
)
from rag_backend.application.services.carousel.types import SlideData


@pytest.mark.unit
class TestEnsureJpegFormat:
    """PNG-to-JPEG conversion when file extension mismatch occurs."""

    def test_returns_unchanged_when_file_missing(self, tmp_path: Path) -> None:
        missing = str(tmp_path / "missing.jpg")
        assert _ensure_jpeg_format(missing) == missing

    def test_accepts_existing_jpeg(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        file_path = tmp_path / "already.jpg"
        PILImage.new("RGB", (10, 10), color="blue").save(file_path, format="JPEG")
        assert _ensure_jpeg_format(str(file_path)) == str(file_path)

    def test_converts_png_to_jpeg(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        png_path = tmp_path / "test.jpg"
        img = PILImage.new("RGB", (10, 10), color="red")
        img.save(png_path, format="PNG")

        result = _ensure_jpeg_format(str(png_path))
        assert result == str(png_path)
        with PILImage.open(png_path) as converted:
            assert converted.format == "JPEG"

    def test_converts_rgba_png_to_rgb_jpeg(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        png_path = tmp_path / "test.jpg"
        img = PILImage.new("RGBA", (10, 10), color=(255, 0, 0, 128))
        img.save(png_path, format="PNG")

        result = _ensure_jpeg_format(str(png_path))
        assert result == str(png_path)
        with PILImage.open(png_path) as converted:
            assert converted.format == "JPEG"
            assert converted.mode == "RGB"

    def test_rejects_invalid_image_data(self, tmp_path: Path) -> None:
        invalid_path = tmp_path / "test.jpg"
        invalid_path.write_bytes(b"img")

        with pytest.raises(RuntimeError, match="not a valid JPEG"):
            _ensure_jpeg_format(str(invalid_path))

    def test_rejects_invalid_png_data(self, tmp_path: Path) -> None:
        png_path = tmp_path / "test.jpg"
        png_path.write_bytes(b"\x89PNG\r\n\x1a\ninvalid")

        with pytest.raises(RuntimeError, match="not a valid JPEG"):
            _ensure_jpeg_format(str(png_path))


@pytest.mark.unit
class TestFilterImageSlides:
    """Filtering slides that should receive hero images."""

    def test_returns_only_slides_with_image_prompt(self) -> None:
        slides = [
            SlideData(1, "intro", "H", "B", image_prompt="scene 1"),
            SlideData(2, "content", "H2", "B2"),
            SlideData(3, "content", "H3", "B3", image_prompt="scene 3"),
        ]
        result = filter_image_slides(slides)
        assert len(result) == 2
        assert result[0].slide_number == 1
        assert result[1].slide_number == 3

    def test_includes_editorial_slides_and_excludes_final_cta(self) -> None:
        slides = [
            SlideData(1, "intro", "H", "B", image_prompt="scene 1"),
            SlideData(2, "summary", "H2", "B2", image_prompt="scene 2"),
            SlideData(3, "content", "H3", "B3", image_prompt="scene 3"),
            SlideData(4, "closing", "H4", "B4", image_prompt="scene 4"),
            SlideData(5, "cta", "H5", "B5", image_prompt="scene 5"),
        ]
        result = filter_image_slides(slides)
        assert [slide.slide_number for slide in result] == [1, 2, 3, 4]

    def test_returns_empty_when_no_prompts(self) -> None:
        slides = [
            SlideData(1, "intro", "H", "B"),
            SlideData(2, "content", "H2", "B2"),
        ]
        assert filter_image_slides(slides) == []
