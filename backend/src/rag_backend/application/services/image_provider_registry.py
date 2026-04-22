"""Registry mapping (image_model, image_style) combos to their
concrete `ImageGenerationService` + `ImageStyleStrategy` pair.

The registry is the single source of truth for which combinations are
supported. The API layer validates inputs against the same
`SUPPORTED_IMAGE_COMBOS` set, so anything the registry can resolve is
something the API already accepted.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.application.services.image_style_strategies import (
    GeminiComicNeonStrategy,
    OpenAICinematicStrategy,
    OpenAIHyperrealStrategy,
    OpenAINeoAnimeStrategy,
)
from rag_backend.domain.constants import (
    IMAGE_MODEL_GEMINI,
    IMAGE_MODEL_OPENAI,
    IMAGE_STYLE_CINEMATIC,
    IMAGE_STYLE_COMIC_NEON,
    IMAGE_STYLE_HYPERREAL,
    IMAGE_STYLE_NEO_ANIME,
    SUPPORTED_IMAGE_COMBOS,
)
from rag_backend.domain.protocols import (
    ImageGenerationService,
    ImageStyleStrategy,
)


@dataclass(frozen=True)
class ImageProvider:
    """Pairs a generation service with the style wrapper used against it."""

    service: ImageGenerationService
    strategy: ImageStyleStrategy


class ImageProviderRegistry:
    """Resolves (model, style) tuples to a configured `ImageProvider`.

    Services are injected by the DI container. Strategies are stateless,
    so the registry constructs them internally — one per supported combo.
    A combo outside `SUPPORTED_IMAGE_COMBOS` raises `ValueError`; API
    validation should have caught it first, but we defend in depth.
    """

    def __init__(
        self,
        gemini_service: ImageGenerationService,
        openai_service: ImageGenerationService,
    ) -> None:
        self._providers: dict[tuple[str, str], ImageProvider] = {
            (IMAGE_MODEL_GEMINI, IMAGE_STYLE_COMIC_NEON): ImageProvider(
                service=gemini_service,
                strategy=GeminiComicNeonStrategy(),
            ),
            (IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC): ImageProvider(
                service=openai_service,
                strategy=OpenAICinematicStrategy(),
            ),
            (IMAGE_MODEL_OPENAI, IMAGE_STYLE_HYPERREAL): ImageProvider(
                service=openai_service,
                strategy=OpenAIHyperrealStrategy(),
            ),
            (IMAGE_MODEL_OPENAI, IMAGE_STYLE_NEO_ANIME): ImageProvider(
                service=openai_service,
                strategy=OpenAINeoAnimeStrategy(),
            ),
        }

    def resolve(self, model: str, style: str) -> ImageProvider:
        key = (model, style)
        if key not in SUPPORTED_IMAGE_COMBOS:
            raise ValueError(
                f"Image preset ({model!r}, {style!r}) is not supported. "
                f"Allowed combos: {sorted(SUPPORTED_IMAGE_COMBOS)}"
            )
        provider = self._providers.get(key)
        if provider is None:
            raise RuntimeError(f"Image preset ({model!r}, {style!r}) has no registered provider.")
        return provider
