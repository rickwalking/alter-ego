"""Carousel refinement operations for copy, design, and slide re-export."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.nodes.export import run_bilingual_export
from rag_backend.application.services.carousel.types import SlideData, unpack_extras
from rag_backend.application.services.carousel_refinement import CarouselRefinementMixin
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.application.services.pdf_slide_builder import PdfSlideBuilder
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import (
    CarouselExportService,
    CarouselRepository,
    LLMService,
)

_ERR_NO_OUTPUT_DIR = "Carousel project {} has no output_dir; cannot re-render slides."
_ERR_NO_SLIDES = "Carousel project {} has no slides."
_ERR_PROJECT_NOT_FOUND = "Carousel project {} not found"


class CarouselRefinementService(CarouselRefinementMixin):
    """Refinement-only carousel service (image, design, re-export)."""

    def __init__(
        self,
        repository: CarouselRepository,
        llm_service: LLMService,
        image_registry: ImageProviderRegistry,
        export_service: CarouselExportService,
        pdf_slide_builder: PdfSlideBuilder | None = None,
    ) -> None:
        self._repo = repository
        self._llm = llm_service
        self._image_registry = image_registry
        self._export = export_service
        self._pdf_slide_builder = pdf_slide_builder
        self._template = CarouselTemplateBuilder()

    def _phase4_design(
        self,
        project: CarouselProject,
        slides: list[SlideData],
    ) -> str:
        return run_design(project, slides, template=self._template)

    async def _phase6_bilingual_export(
        self,
        project: CarouselProject,
        slides_data: list[SlideData],
        pt_html: str,
        output_dir: Path,
    ) -> None:
        await run_bilingual_export(
            project,
            slides_data,
            pt_html,
            output_dir,
            export=self._export,
            pdf_builder=self._pdf_slide_builder,
            template=self._template,
        )

    async def re_render_slides(self, project_id: UUID) -> CarouselProject:
        """Re-export slide JPGs and PDF from persisted slide data."""
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(_ERR_PROJECT_NOT_FOUND.format(project_id))
        if not project.output_dir:
            raise ValueError(_ERR_NO_OUTPUT_DIR.format(project_id))
        slides = await self._repo.get_slides_by_project(project_id)
        if not slides:
            raise ValueError(_ERR_NO_SLIDES.format(project_id))

        slides_data = [unpack_extras(slide) for slide in slides]
        pt_html = self._phase4_design(project, slides_data)
        await self._phase6_bilingual_export(
            project,
            slides_data,
            pt_html,
            Path(project.output_dir),
        )
        project.updated_at = datetime.now(tz=UTC)
        return await self._repo.update_project(project)


__all__ = ["CarouselRefinementService"]
