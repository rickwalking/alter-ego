"""Phase 6: bilingual slide rendering and PDF export.

Renders PT slides from the already-built HTML, and — when the slides
carry `translation_en` payloads — re-runs phase 4 for EN and renders
those too. Hero images live at `<output>/images/` and are shared by
both languages.  Relative paths are rewritten so that standard exports
(`<output>/<lang>/`) use `../images/...` and HD exports
(`<output>/<lang>/hd/`) use `../../images/...`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rag_backend.application.services.carousel.carousel_export_assets import (
    prepare_carousel_export_assets,
)
from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.types import (
    SlideData,
    slides_data_for_language,
)
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.carousel_template.strategies.registry import (
    SlideLayoutRegistry,
)
from rag_backend.application.services.pdf_slide_builder import PdfSlideBuilder
from rag_backend.domain.constants import (
    HD_SUBDIR_NAME,
    LANGUAGE_EN,
    LANGUAGE_PT,
    SHARED_IMAGES_DIR_NAME,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import CarouselExportService, ExportConfig
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


@dataclass
class BilingualExportConfig:
    """Configuration for bilingual export operations."""

    project: CarouselProject
    slides_data: list[SlideData]
    pt_html: str
    output_dir: Path
    export: CarouselExportService
    pdf_builder: PdfSlideBuilder | None = None
    template: CarouselTemplateBuilder | None = None
    strategy_registry: SlideLayoutRegistry | None = None
    strategy_name: str | None = None
    language: str = ""
    html_content: str = ""


async def render_language(
    config: BilingualExportConfig,
) -> None:
    """Export a single language's slide JPGs + PDF into `<output>/<lang>/`."""
    lang_dir = config.output_dir / config.language
    lang_dir.mkdir(parents=True, exist_ok=True)
    if config.language == LANGUAGE_PT:
        prepare_carousel_export_assets(config.output_dir)

    def _rewrite_image_paths(html: str, prefix: str) -> str:
        return (
            html
            .replace(f'src="{SHARED_IMAGES_DIR_NAME}/', f'src="{prefix}')
            .replace(f"src='{SHARED_IMAGES_DIR_NAME}/", f"src='{prefix}")
            .replace(f'url("{SHARED_IMAGES_DIR_NAME}/', f'url("{prefix}')
            .replace(f"url('{SHARED_IMAGES_DIR_NAME}/", f"url('{prefix}")
        )

    standard_html = _rewrite_image_paths(config.html_content, "../images/")
    hd_html = _rewrite_image_paths(config.html_content, "../../images/")

    slide_paths = await config.export.export_slides(
        html_content=standard_html,
        output_dir=str(lang_dir),
    )
    # Export HD slides too (2160x2700 for archive/retina). Non-blocking:
    # if HD fails the standard slides are still available.
    try:
        hd_dir = lang_dir / HD_SUBDIR_NAME
        hd_dir.mkdir(parents=True, exist_ok=True)
        await config.export.export_slides(
            html_content=hd_html,
            output_dir=str(hd_dir),
            config=ExportConfig(hd=True),
        )
    except Exception:
        logger.warning(
            "hd_export_failed",
            project_id=str(config.project.id),
            language=config.language,
            exc_info=True,
        )
    if config.pdf_builder is None or not slide_paths:
        return
    try:
        pdf_path = config.pdf_builder.build(
            slide_paths=slide_paths,
            output_dir=str(lang_dir),
        )
    except (ValueError, FileNotFoundError, OSError) as exc:
        logger.warning(
            "carousel_pdf_build_failed",
            project_id=str(config.project.id),
            language=config.language,
            error=str(exc),
        )
        return
    if config.language == LANGUAGE_EN:
        config.project.pdf_path_en = pdf_path
    else:
        config.project.pdf_path = pdf_path


async def run_bilingual_export(
    config: BilingualExportConfig,
) -> None:
    """Render PT slides, then EN slides when translations exist."""
    pt_config = BilingualExportConfig(
        project=config.project,
        slides_data=config.slides_data,
        pt_html=config.pt_html,
        output_dir=config.output_dir,
        export=config.export,
        pdf_builder=config.pdf_builder,
        template=config.template,
        strategy_registry=config.strategy_registry,
        strategy_name=config.strategy_name,
        language=LANGUAGE_PT,
        html_content=config.pt_html,
    )
    await render_language(pt_config)

    en_available = any(s.translation_en for s in config.slides_data)
    if not en_available:
        return

    en_slides = slides_data_for_language(config.slides_data, LANGUAGE_EN)
    en_html = run_design(
        config.project,
        en_slides,
        template=config.template,  # type: ignore[arg-type]
        language=LANGUAGE_EN,
        strategy_registry=config.strategy_registry,
        strategy_name=config.strategy_name,
    )
    en_config = BilingualExportConfig(
        project=config.project,
        slides_data=config.slides_data,
        pt_html=config.pt_html,
        output_dir=config.output_dir,
        export=config.export,
        pdf_builder=config.pdf_builder,
        template=config.template,
        strategy_registry=config.strategy_registry,
        strategy_name=config.strategy_name,
        language=LANGUAGE_EN,
        html_content=en_html,
    )
    await render_language(en_config)
