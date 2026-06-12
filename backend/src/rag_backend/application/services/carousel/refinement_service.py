"""Carousel refinement operations for copy, design, and slide re-export."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict
from uuid import UUID

from rag_backend.application.services.carousel.carousel_export_assets import (
    prepare_carousel_export_assets,
)
from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.nodes.export import (
    BilingualExportConfig,
    run_bilingual_export,
)
from rag_backend.application.services.carousel.types import SlideData, unpack_extras
from rag_backend.application.services.carousel_refinement import CarouselRefinementMixin
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.carousel_template.strategies.registry import (
    SlideLayoutRegistry,
)
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


@dataclass
class CarouselRefinementConfig:
    repository: CarouselRepository
    llm_service: LLMService
    image_registry: ImageProviderRegistry
    export_service: CarouselExportService
    pdf_slide_builder: PdfSlideBuilder | None = None
    strategy_registry: SlideLayoutRegistry | None = None


class BilingualExportParams(TypedDict):
    project: CarouselProject
    slides_data: list[SlideData]
    pt_html: str
    output_dir: Path
    strategy_name: str | None


class CarouselRefinementService(CarouselRefinementMixin):
    """Refinement-only carousel service (image, design, re-export)."""

    def __init__(
        self,
        config: CarouselRefinementConfig,
    ) -> None:
        self._repo = config.repository
        self._llm = config.llm_service
        self._image_registry = config.image_registry
        self._export = config.export_service
        self._pdf_slide_builder = config.pdf_slide_builder
        self._strategy_registry = config.strategy_registry
        self._template = CarouselTemplateBuilder()

    def _phase4_design(
        self,
        project: CarouselProject,
        slides: list[SlideData],
        strategy_name: str | None = None,
    ) -> str:
        return run_design(
            project,
            slides,
            template=self._template,
            strategy_registry=self._strategy_registry,
            strategy_name=strategy_name,
        )

    async def _phase6_bilingual_export(
        self,
        params: BilingualExportParams,
    ) -> None:
        await run_bilingual_export(
            BilingualExportConfig(
                project=params["project"],
                slides_data=params["slides_data"],
                pt_html=params["pt_html"],
                output_dir=params["output_dir"],
                export=self._export,
                pdf_builder=self._pdf_slide_builder,
                template=self._template,
                strategy_registry=self._strategy_registry,
                strategy_name=params["strategy_name"],
            )
        )

    async def re_render_slides(
        self,
        project_id: UUID,
        strategy: str | None = None,
    ) -> CarouselProject:
        """Re-export slide JPGs and PDF from persisted slide data.

        When ``strategy`` is given, the project's ``slide_layout_strategy``
        is updated and slides are regenerated with that strategy.
        """
        project = await self._repo.get_project_by_id(project_id)
        if project is None:
            raise ValueError(_ERR_PROJECT_NOT_FOUND.format(project_id))
        if not project.output_dir:
            raise ValueError(_ERR_NO_OUTPUT_DIR.format(project_id))
        slides = await self._repo.get_slides_by_project(project_id)
        if not slides:
            raise ValueError(_ERR_NO_SLIDES.format(project_id))

        if strategy is not None:
            project.slide_layout_strategy = strategy

        output_dir = Path(project.output_dir)
        prepare_carousel_export_assets(output_dir)
        slides_data = [unpack_extras(slide) for slide in slides]
        pt_html = self._phase4_design(project, slides_data, strategy_name=strategy)
        await self._phase6_bilingual_export(
            BilingualExportParams(
                project=project,
                slides_data=slides_data,
                pt_html=pt_html,
                output_dir=output_dir,
                strategy_name=strategy,
            )
        )
        if strategy is not None:
            await self._repo.update_project(project)
        project.updated_at = datetime.now(tz=UTC)
        return await self._repo.update_project(project)


__all__ = ["CarouselRefinementService"]
