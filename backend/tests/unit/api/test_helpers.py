"""Unit tests for carousel route helpers.

Gherkin: tests/features/carousel_design_tokens_slide_count.feature
"""

from pathlib import Path

import pytest

from rag_backend.api.routes.carousels.helpers import _count_slide_images


@pytest.mark.unit
class TestCountSlideImages:
    """Tests for _count_slide_images()."""

    def test_counts_images_dir(self, tmp_path: Path):
        output_dir = str(tmp_path)
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        for i in range(1, 5):
            (images_dir / f"slide_{i}.jpg").write_text("")

        assert _count_slide_images(output_dir) == 4

    def test_falls_back_to_pt_dir(self, tmp_path: Path):
        output_dir = str(tmp_path)
        pt_dir = tmp_path / "pt"
        pt_dir.mkdir()
        for i in range(1, 7):
            (pt_dir / f"slide_{i}.jpg").write_text("")

        assert _count_slide_images(output_dir) == 6

    def test_falls_back_to_en_dir(self, tmp_path: Path):
        output_dir = str(tmp_path)
        en_dir = tmp_path / "en"
        en_dir.mkdir()
        for i in range(1, 8):
            (en_dir / f"slide_{i}.jpg").write_text("")

        assert _count_slide_images(output_dir) == 7

    def test_prefers_images_over_fallback(self, tmp_path: Path):
        output_dir = str(tmp_path)
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        pt_dir = tmp_path / "pt"
        pt_dir.mkdir()
        for i in range(1, 5):
            (images_dir / f"slide_{i}.jpg").write_text("")
        for i in range(1, 8):
            (pt_dir / f"slide_{i}.jpg").write_text("")

        assert _count_slide_images(output_dir) == 4

    def test_returns_0_for_none_output_dir(self):
        assert _count_slide_images(None) == 0

    def test_returns_0_for_empty_output_dir(self, tmp_path: Path):
        assert _count_slide_images(str(tmp_path)) == 0
