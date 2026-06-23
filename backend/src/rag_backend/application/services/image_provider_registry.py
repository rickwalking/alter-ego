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
    IMAGE_STRATEGY_REGISTRY,
)
from rag_backend.domain.constants import (
    IMAGE_MODEL_GEMINI,
    IMAGE_MODEL_OPENAI,
    SUPPORTED_IMAGE_COMBOS,
)
from rag_backend.domain.protocols import (
    ImageGenerationService,
    ImageStyleStrategy,
)

_ERR_IMAGE_PRESET_UNSUPPORTED = (
    "Image preset ({!r}, {!r}) is not supported. Allowed combos: {}"
)
_ERR_IMAGE_PRESET_NO_PROVIDER = "Image preset ({!r}, {!r}) has no registered provider."


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

    This class is the concrete implementation of the presentation module's
    ``ImageProviderPort`` (``rag_backend.modules.presentation.domain.ports``):
    it structurally satisfies that Protocol via :meth:`resolve`, so the
    presentation application layer can depend on the port while keeping this
    registry the single source of truth for the supported combos. The
    relationship is structural (Protocol) rather than nominal to avoid an
    import cycle — the port re-exports :class:`ImageProvider` from here.
    """

    def __init__(
        self,
        gemini_service: ImageGenerationService,
        openai_service: ImageGenerationService,
    ) -> None:
        # Build one provider per registry combo, pairing each strategy with the
        # service for its model. ``IMAGE_STRATEGY_REGISTRY`` is the single source
        # of truth shared with the prompt renderer, so the two can never drift.
        services_by_model: dict[str, ImageGenerationService] = {
            IMAGE_MODEL_GEMINI: gemini_service,
            IMAGE_MODEL_OPENAI: openai_service,
        }
        self._providers: dict[tuple[str, str], ImageProvider] = {
            (model, style): ImageProvider(
                service=services_by_model[model],
                strategy=strategy_cls(),
            )
            for (model, style), strategy_cls in IMAGE_STRATEGY_REGISTRY.items()
        }

    def resolve(self, model: str, style: str) -> ImageProvider:
        key = (model, style)
        if key not in SUPPORTED_IMAGE_COMBOS:
            raise ValueError(
                _ERR_IMAGE_PRESET_UNSUPPORTED.format(
                    model, style, sorted(SUPPORTED_IMAGE_COMBOS)
                )
            )
        provider = self._providers.get(key)
        if provider is None:
            raise RuntimeError(_ERR_IMAGE_PRESET_NO_PROVIDER.format(model, style))
        return provider
