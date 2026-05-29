"""Protocols for carousel workflow services."""

from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

from rag_backend.domain.models import CarouselProject, ResearchSourceType


class ImageGenerationService(Protocol):
    """Protocol for AI image generation.

    Implementations wrap a concrete vendor SDK (Gemini, OpenAI, ...) so
    the agent pipeline can stay provider-agnostic. The caller is
    responsible for composing the final prompt (style wrapper + scene)
    before invoking `generate_image` — this protocol only handles the
    vendor call and persistence to disk.
    """

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
    ) -> str: ...


class ImageStyleStrategy(Protocol):
    """Protocol for wrapping an LLM-produced scene description with
    provider- and style-specific directives.

    Each (model, style) preset gets its own strategy so the style
    vocabulary can be tuned to what each model responds to best. The
    scene text is treated as user data and MUST appear verbatim in the
    output; the wrapper only prepends directives.
    """

    def wrap(self, scene: str, theme: Mapping[str, str]) -> str:
        """Return the final prompt for the image service.

        Args:
            scene: The LLM-generated scene description, user-owned text.
            theme: Palette dict with at minimum `primary`, `accent`,
                `background` hex strings.
        """
        ...


class CarouselExportService(Protocol):
    """Protocol for carousel HTML to image export."""

    async def export_slides(
        self,
        html_content: str,
        output_dir: str,
        width: int = 1080,
        height: int = 1350,
    ) -> list[str]: ...


class ResearchTool(Protocol):
    """Protocol for web research operations."""

    async def scrape_url(self, url: str) -> str: ...

    async def search_web(
        self, query: str, _source_types: list[ResearchSourceType]
    ) -> list[dict[str, str]]: ...


class CarouselRefinementService(Protocol):
    """Protocol for carousel refinement operations (copy, design, re-export)."""

    async def re_render_slides(self, project_id: UUID) -> CarouselProject: ...

    async def regenerate_slide_image(
        self,
        project_id: UUID,
        slide_number: int,
        instruction: str,
    ) -> CarouselProject: ...

    async def refine_carousel_design(
        self,
        project_id: UUID,
        instruction: str,
    ) -> CarouselProject: ...
