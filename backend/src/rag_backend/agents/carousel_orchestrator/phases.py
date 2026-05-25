"""Phase implementation functions for the carousel pipeline.

Each function takes ``self`` (a CarouselAgent instance) as the first param
so they can be assigned as methods on the class at definition time.
"""

from pathlib import Path

from rag_backend.application.services.carousel.nodes.caption import run_caption
from rag_backend.application.services.carousel.nodes.content import run_content
from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.nodes.export import (
    render_language,
    run_bilingual_export,
)
from rag_backend.application.services.carousel.nodes.images import run_images
from rag_backend.application.services.carousel.nodes.linkedin import run_linkedin
from rag_backend.application.services.carousel.nodes.progress import set_progress
from rag_backend.application.services.carousel.nodes.research import run_research
from rag_backend.application.services.carousel.theme_resolver import resolve_theme
from rag_backend.application.services.carousel.types import SlideData
from rag_backend.domain.models import CarouselProject, ResearchSource


async def _phase1_research(
    self,
    project: CarouselProject,
    seed_urls: list[str],
) -> list[ResearchSource]:
    return await run_research(
        project,
        seed_urls,
        repo=self._repo,
        research_tool=self._research,
    )


async def _phase2_3_content(
    self,
    project: CarouselProject,
    sources: list[ResearchSource],
) -> tuple[list[SlideData], str]:
    return await run_content(
        project,
        sources,
        llm=self._llm,
        template=self._template,
    )


def _phase4_design(
    self,
    project: CarouselProject,
    slides: list[SlideData],
) -> str:
    return run_design(project, slides, template=self._template)


async def _phase5_images(
    self,
    project: CarouselProject,
    slides: list[SlideData],
    output_dir: Path,
) -> None:
    await run_images(
        project,
        slides,
        output_dir,
        repo=self._repo,
        image_registry=self._image_registry,
    )


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


async def _render_language(
    self,
    project: CarouselProject,
    _slides: list[SlideData],
    language: str,
    html_content: str,
    output_dir: Path,
) -> None:
    await render_language(
        project,
        language,
        html_content,
        output_dir,
        export=self._export,
        pdf_builder=self._pdf_slide_builder,
    )


async def _phase7_caption(
    self,
    project: CarouselProject,
    slides: list[SlideData],
) -> str:
    return await run_caption(project, slides, llm=self._llm, template=self._template)


async def _phase8_linkedin(self, project: CarouselProject) -> None:
    await run_linkedin(
        project, repo=self._repo, generator=self._linkedin_post_generator
    )


def _resolve_theme(self, project: CarouselProject) -> dict[str, str]:
    return resolve_theme(project)


async def _set_progress(
    self,
    project: CarouselProject,
    label: str,
    current: int | None = None,
    total: int | None = None,
    detail: str | None = None,
) -> CarouselProject:
    return await set_progress(
        project,
        repo=self._repo,
        label=label,
        current=current,
        total=total,
        detail=detail,
    )
