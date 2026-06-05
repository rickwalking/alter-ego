"""Protocols for carousel workflow services."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rag_backend.domain.models import CarouselProject, ResearchSourceType


class StrategyNotFoundError(LookupError):
    """Raised when a strategy name is not found in the registry."""


@dataclass(frozen=True)
class ExportConfig:
    """Configuration for carousel slide export."""

    width: int = 1080
    height: int = 1350
    css_overrides: str | None = None
    quality: int = 95
    hd: bool = False


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
        config: ExportConfig | None = None,
    ) -> list[str]: ...


class ResearchTool(Protocol):
    """Protocol for web research operations."""

    async def scrape_url(self, url: str) -> str: ...

    async def search_web(
        self, query: str, _source_types: list[ResearchSourceType]
    ) -> list[dict[str, str]]: ...


class CarouselRefinementService(Protocol):
    """Protocol for carousel refinement operations (copy, design, re-export)."""

    async def re_render_slides(
        self, project_id: UUID, strategy: str | None = None
    ) -> CarouselProject: ...

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


class SlideLayoutStrategy(Protocol):
    """Renders a single slide's inner HTML for a given layout format.

    Each strategy produces the content *inside* the ig-slide wrapper
    (heading, body, structured cards). The outer shell (action bar,
    counter, caption) is applied by the builder. Strategy implementations
    are stateless singletons registered at container bootstrap.
    """

    strategy_name: str
    """Unique key used in the API and registry, e.g. 'stat_card_grid'."""

    display_name: str
    """Human-readable label, e.g. 'Stat Card Grid'."""

    supported_slide_types: frozenset[str]
    """Slide types this strategy can render, e.g. {'content', 'summary'}."""

    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        theme: Mapping[str, str],
        total_slides: int,
        language: str,
    ) -> str:
        """Return inner HTML for a single slide.

        Args:
            slide: Structured slide data (heading, body, features, stats,
                insight, summary_points, tldr_strip, number, type).
            project: Full project metadata (watermark, creator, niche...).
            theme: Design palette dict (primary, accent, background...).
            total_slides: Total slide count for progress display.
            language: Language code (pt, en) for localized text.
        """
        ...
