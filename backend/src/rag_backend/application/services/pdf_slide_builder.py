"""PDF slide builder.

Assembles the exported JPG slides into a single multi-page PDF — one
page per slide, each page sized to the source image so the 1080x1350
layout is preserved byte-accurate. Uses `img2pdf` because it embeds
JPEG bytes losslessly without re-encoding (ReportLab and Pillow would
rasterize and bloat the file).

The output path lives alongside the slides in the project output
directory as `carousel.pdf`. The pipeline writes it, the API serves it
for download, and the LinkedIn publishing flow uploads it (manual or
broker-based).
"""

from __future__ import annotations

from pathlib import Path

import img2pdf

from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_PDF_FILENAME = "carousel.pdf"
_ERR_EMPTY_SLIDE_LIST = "Cannot build PDF from empty slide list"
_ERR_SLIDE_IMAGE_NOT_FOUND = "Slide image not found: {}"


class PdfSlideBuilder:
    """Builds a multi-page PDF from a list of slide image files."""

    def build(self, slide_paths: list[str], output_dir: str) -> str:
        """Write `carousel.pdf` into output_dir and return the path.

        Raises:
            ValueError: if slide_paths is empty.
            FileNotFoundError: if any slide file is missing.
        """
        if not slide_paths:
            raise ValueError(_ERR_EMPTY_SLIDE_LIST)

        existing: list[bytes] = []
        for path in slide_paths:
            slide_file = Path(path)
            if not slide_file.exists():
                raise FileNotFoundError(_ERR_SLIDE_IMAGE_NOT_FOUND.format(path))
            existing.append(slide_file.read_bytes())

        output = Path(output_dir) / _PDF_FILENAME
        output.parent.mkdir(parents=True, exist_ok=True)
        # layout_fun=None → one page per image at the image's native size.
        pdf_bytes = img2pdf.convert(existing)
        output.write_bytes(pdf_bytes)
        logger.info(
            "pdf_slides_built",
            output=str(output),
            pages=len(existing),
            bytes=len(pdf_bytes),
        )
        return str(output)
