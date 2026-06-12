"""Unit tests for carousel route helpers.

Gherkin: tests/features/carousel_design_tokens_slide_count.feature
"""

from pathlib import Path

import pytest

from rag_backend.application.services.carousel.design_token_utils import (
    _count_slide_images,
    _preview_rendered_slide_urls,
    _slide_image_numbers,
    merge_design_tokens_with_disk,
)


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

    def test_uses_max_count_across_directories(self, tmp_path: Path):
        output_dir = str(tmp_path)
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        pt_dir = tmp_path / "pt"
        pt_dir.mkdir()
        for i in range(1, 5):
            (images_dir / f"slide_{i}.jpg").write_text("")
        for i in range(1, 8):
            (pt_dir / f"slide_{i}.jpg").write_text("")

        assert _count_slide_images(output_dir) == 7

    def test_returns_0_for_none_output_dir(self):
        assert _count_slide_images(None) == 0

    def test_returns_0_for_empty_output_dir(self, tmp_path: Path):
        assert _count_slide_images(str(tmp_path)) == 0

    def test_returns_sparse_slide_numbers(self, tmp_path: Path) -> None:
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        for number in (5, 1, 3, 4):
            (images_dir / f"slide_{number}.jpg").write_text("")

        assert _slide_image_numbers(str(tmp_path), "images") == [1, 3, 4, 5]


@pytest.mark.unit
class TestMergeDesignTokensWithDisk:
    def test_uses_rendered_slide_count_over_stale_tokens(self, tmp_path: Path):
        output_dir = str(tmp_path)
        pt_dir = tmp_path / "pt"
        pt_dir.mkdir()
        for i in range(1, 8):
            (pt_dir / f"slide_{i}.jpg").write_text("")

        from rag_backend.domain.models import CarouselProject, CarouselTheme

        project = CarouselProject(
            id="2958760d-89c4-4a68-b9be-36daeba6dba0",
            topic="Test",
            audience="Devs",
            niche="Tech",
            theme=CarouselTheme.CYBERSECURITY,
            output_dir=output_dir,
            design_tokens={
                "colors": {},
                "typography": {},
                "images": {
                    "hero": "/api/carousels/x/images/slide_1.jpg",
                    "slides": [
                        f"/api/carousels/x/images/slide_{i}.jpg" for i in range(1, 7)
                    ],
                    "rendered_slides_pt": [
                        f"/api/carousels/x/slide-images/pt/slide_{i}.jpg"
                        for i in range(1, 7)
                    ],
                },
                "layout": {"progress_segments": 6},
            },
        )

        merged = merge_design_tokens_with_disk(project)
        rendered = merged["images"]["rendered_slides_pt"]
        assert isinstance(rendered, list)
        assert len(rendered) == 7

    def test_draft_project_uses_preview_urls_for_rendered_slides(
        self, tmp_path: Path
    ) -> None:
        from uuid import UUID

        from rag_backend.domain.models import CarouselProject, CarouselTheme

        project_id = UUID("2958760d-89c4-4a68-b9be-36daeba6dba0")
        output_dir = str(tmp_path)
        pt_dir = tmp_path / "pt"
        pt_dir.mkdir()
        for i in range(1, 7):
            (pt_dir / f"slide_{i}.jpg").write_text("")

        project = CarouselProject(
            id=project_id,
            topic="Test",
            audience="Devs",
            niche="Tech",
            theme=CarouselTheme.CYBERSECURITY,
            output_dir=output_dir,
            is_public=False,
            design_tokens={
                "images": {
                    "rendered_slides_pt": [
                        f"/api/carousels/{project_id}/slide-images/pt/slide_{i}.jpg"
                        for i in range(1, 7)
                    ],
                    "rendered_slides_en": [
                        f"/api/carousels/{project_id}/slide-images/en/slide_{i}.jpg"
                        for i in range(1, 7)
                    ],
                },
            },
        )

        merged = merge_design_tokens_with_disk(project)
        rendered_pt = merged["images"]["rendered_slides_pt"]
        assert isinstance(rendered_pt, list)
        assert rendered_pt[0].startswith(
            f"/api/carousels/{project_id}/preview/images/slide_1.jpg?lang=pt"
        )
        assert merged["images"]["hero"] == rendered_pt[0]
        assert merged["images"]["slides"] == rendered_pt
        assert "rendered_slides_en" not in merged["images"]

    def test_preview_rendered_slide_urls_include_lang_query(self) -> None:
        from uuid import UUID

        project_id = UUID("2958760d-89c4-4a68-b9be-36daeba6dba0")
        urls = _preview_rendered_slide_urls(project_id, [1, 3], "pt")
        assert urls == [
            f"/api/carousels/{project_id}/preview/images/slide_1.jpg?lang=pt",
            f"/api/carousels/{project_id}/preview/images/slide_3.jpg?lang=pt",
        ]

    def test_draft_project_falls_back_to_raw_preview_urls(self, tmp_path: Path) -> None:
        from uuid import UUID

        from rag_backend.domain.models import CarouselProject, CarouselTheme

        project_id = UUID("2958760d-89c4-4a68-b9be-36daeba6dba0")
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        for number in (1, 3, 4, 5):
            (images_dir / f"slide_{number}.jpg").write_text("")
        project = CarouselProject(
            id=project_id,
            topic="Test",
            audience="Devs",
            niche="Tech",
            theme=CarouselTheme.CYBERSECURITY,
            output_dir=str(tmp_path),
            is_public=False,
        )

        merged = merge_design_tokens_with_disk(project)

        rendered_pt = merged["images"]["rendered_slides_pt"]
        assert isinstance(rendered_pt, list)
        assert rendered_pt == [
            f"/api/carousels/{project_id}/preview/images/slide_1.jpg?lang=pt",
            f"/api/carousels/{project_id}/preview/images/slide_3.jpg?lang=pt",
            f"/api/carousels/{project_id}/preview/images/slide_4.jpg?lang=pt",
            f"/api/carousels/{project_id}/preview/images/slide_5.jpg?lang=pt",
        ]
        assert merged["images"]["hero"] == rendered_pt[0]
        assert merged["images"]["slides"] == rendered_pt
