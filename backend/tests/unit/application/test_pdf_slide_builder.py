"""Unit tests for PdfSlideBuilder.

Gherkin: tests/features/pdf_slide_builder.feature
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from rag_backend.application.services.pdf_slide_builder import PdfSlideBuilder


def _make_jpg(path: Path, width: int = 1080, height: int = 1350) -> None:
    image = Image.new("RGB", (width, height), color=(10, 14, 23))
    image.save(path, format="JPEG", quality=90)


@pytest.mark.unit
class TestPdfSlideBuilder:
    """Happy path + failure modes for the PDF assembler."""

    def test_n_slides_produce_n_pages(self, tmp_path: Path) -> None:
        slide_paths: list[str] = []
        for i in range(1, 7):
            p = tmp_path / f"slide_{i}.jpg"
            _make_jpg(p)
            slide_paths.append(str(p))

        result = PdfSlideBuilder().build(slide_paths, str(tmp_path))

        pdf_file = Path(result)
        assert pdf_file.exists()
        assert pdf_file.name == "carousel.pdf"

        # Use pypdf to count pages (already a project dep).
        import pypdf

        reader = pypdf.PdfReader(str(pdf_file))
        assert len(reader.pages) == 6

    def test_single_slide_page_aspect_ratio_is_preserved(self, tmp_path: Path) -> None:
        slide = tmp_path / "only.jpg"
        _make_jpg(slide, width=1080, height=1350)
        PdfSlideBuilder().build([str(slide)], str(tmp_path))

        import pypdf

        reader = pypdf.PdfReader(str(tmp_path / "carousel.pdf"))
        page = reader.pages[0]
        # img2pdf converts pixels to PDF points at 96→72 DPI, so the raw
        # point size is smaller than the pixel size, but the 4:5 aspect
        # ratio is preserved byte-accurately.
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        assert width / height == pytest.approx(1080 / 1350, rel=1e-3)

    def test_empty_list_raises_value_error(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="empty"):
            PdfSlideBuilder().build([], str(tmp_path))

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            PdfSlideBuilder().build([str(tmp_path / "ghost.jpg")], str(tmp_path))

    def test_returns_absolute_path_to_pdf(self, tmp_path: Path) -> None:
        slide = tmp_path / "s.jpg"
        _make_jpg(slide)
        result = PdfSlideBuilder().build([str(slide)], str(tmp_path))
        assert result.endswith("carousel.pdf")
        assert Path(result).exists()
