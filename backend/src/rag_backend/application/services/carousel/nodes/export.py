"""Phase 6: bilingual slide rendering and PDF export.

Renders PT slides from the already-built HTML, and — when the slides
carry `translation_en` payloads — re-runs phase 4 for EN and renders
those too. Hero images live one directory up (`<output>/images/`) and
are shared by both languages, so the HTML's `src="images/..."` is
rewritten to `src="../images/..."` before handing it to Playwright.
"""

from __future__ import annotations

from pathlib import Path

from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.types import (
    SlideData,
    slides_data_for_language,
)
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.pdf_slide_builder import PdfSlideBuilder
from rag_backend.domain.constants import (
    HD_SUBDIR_NAME,
    LANGUAGE_EN,
    LANGUAGE_PT,
    SHARED_IMAGES_DIR_NAME,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import CarouselExportService
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


async def render_language(
    project: CarouselProject,
    language: str,
    html_content: str,
    output_dir: Path,
    *,
    export: CarouselExportService,
    pdf_builder: PdfSlideBuilder | None,
) -> None:
    """Export a single language's slide JPGs + PDF into `<output>/<lang>/`."""
    lang_dir = output_dir / language
    lang_dir.mkdir(parents=True, exist_ok=True)
    src_dq = f'src="{SHARED_IMAGES_DIR_NAME}/'
    src_sq = f"src='{SHARED_IMAGES_DIR_NAME}/"
    url_dq = f'url("{SHARED_IMAGES_DIR_NAME}/'
    url_sq = f"url('{SHARED_IMAGES_DIR_NAME}/"
    rewritten_html = (
        html_content
        .replace(src_dq, 'src="../images/')
        .replace(src_sq, "src='../images/")
        .replace(url_dq, 'url("../images/')
        .replace(url_sq, "url('../images/")
    )
    slide_paths = await export.export_slides(
        html_content=rewritten_html,
        output_dir=str(lang_dir),
    )
    # Export HD slides too (2160x2700 for archive/retina). Non-blocking:
    # if HD fails the standard slides are still available.
    try:
        hd_dir = lang_dir / HD_SUBDIR_NAME
        hd_dir.mkdir(parents=True, exist_ok=True)
        await export.export_slides(
            html_content=rewritten_html,
            output_dir=str(hd_dir),
            hd=True,
        )
    except Exception:
        logger.warning(
            "hd_export_failed",
            project_id=str(project.id),
            language=language,
            exc_info=True,
        )
    if pdf_builder is None or not slide_paths:
        return
    try:
        pdf_path = pdf_builder.build(
            slide_paths=slide_paths,
            output_dir=str(lang_dir),
        )
    except (ValueError, FileNotFoundError, OSError) as exc:
        logger.warning(
            "carousel_pdf_build_failed",
            project_id=str(project.id),
            language=language,
            error=str(exc),
        )
        return
    if language == LANGUAGE_EN:
        project.pdf_path_en = pdf_path
    else:
        project.pdf_path = pdf_path


async def run_bilingual_export(
    project: CarouselProject,
    slides_data: list[SlideData],
    pt_html: str,
    output_dir: Path,
    *,
    export: CarouselExportService,
    pdf_builder: PdfSlideBuilder | None,
    template: CarouselTemplateBuilder,
) -> None:
    """Render PT slides, then EN slides when translations exist."""
    await render_language(
        project,
        LANGUAGE_PT,
        pt_html,
        output_dir,
        export=export,
        pdf_builder=pdf_builder,
    )

    en_available = any(s.translation_en for s in slides_data)
    if not en_available:
        return

    en_slides = slides_data_for_language(slides_data, LANGUAGE_EN)
    en_html = run_design(project, en_slides, template=template, language=LANGUAGE_EN)
    await render_language(
        project,
        LANGUAGE_EN,
        en_html,
        output_dir,
        export=export,
        pdf_builder=pdf_builder,
    )
