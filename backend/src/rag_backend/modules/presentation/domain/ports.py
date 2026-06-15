"""Outbound ports (Protocols) for the presentation bounded context.

The presentation ports are:

* ``CarouselRepository`` — carousel project / slide persistence (re-exported,
  object-identity shim; see below). The presentation context reads the project's
  presentation fields and its slides through this contract.
* ``PresentationPolicyPort`` — loading the versioned presentation policy
  (slide budgets, geometry, fonts) the renderer/validator enforces.
* ``SlideValidationPort`` — validating per-slide presentation copy against the
  active policy and returning a structured validation report.
* ``ImageGenerationService`` / ``ImageStyleStrategy`` — the per-vendor image
  generation + style-wrapping contracts (re-exported, object-identity shims from
  the shared ``domain.protocols``; see below). The concrete vendor adapters
  (OpenAI / Gemini) implement ``ImageGenerationService``; vendor SDK imports stay
  in the adapter/infrastructure layer.
* ``ImageProviderPort`` — the image-provider registry contract: resolve an
  ``(image_model, image_style)`` preset to a configured :class:`ImageProvider`
  (a service + style-strategy pair). The application layer (carousel image
  nodes) depends only on this port, never on a concrete vendor SDK.

Per backend/CLAUDE.md, interfaces are :class:`typing.Protocol`, never ABCs, and
they are fully typed (no ``Any``). These Protocols let the presentation
APPLICATION/domain layers depend only on contracts — never on the carousel ORM
or a concrete Postgres repository; the concrete adapters (provider ports,
persistence) arrive in later phases (AE-0118/0119) behind this facade.

**Re-export, not relocation (AE-0117 constraint) for ``CarouselRepository``.**
That Protocol is defined in the SHARED protocol file
``rag_backend.domain.protocols.repositories`` which is imported by the carousel
routes, the workflow engine, services, and the container. Physically moving the
definition would break those imports, so this phase keeps the definition where it
is and merely **re-exports** it here. The legacy import path
(``rag_backend.domain.protocols.repositories.CarouselRepository``) keeps
resolving to the IDENTICAL Protocol object, while the presentation module domain
layer also exposes it as its own port. This mirrors
``modules.editorial.domain.ports`` exactly (object-identity shim).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rag_backend.application.services.image_provider_registry import ImageProvider
from rag_backend.domain.protocols.carousel import (
    ImageGenerationService,
    ImageStyleStrategy,
)
from rag_backend.domain.protocols.repositories import CarouselRepository
from rag_backend.modules.presentation.domain.models import (
    CarouselPresentationPolicy,
    SlideValidationReport,
)


@runtime_checkable
class PresentationPolicyPort(Protocol):
    """Load the versioned presentation policy a project renders/validates against.

    Wraps the canonical policy-loading step so the application layer requests the
    active :class:`CarouselPresentationPolicy` through a contract instead of
    reaching into the policy loader directly. The concrete adapter (AE-0119)
    delegates to the unchanged policy source so the loaded policy stays
    byte-identical.
    """

    async def load_policy(self, version: str) -> CarouselPresentationPolicy:
        """Return the typed presentation policy for the given version."""
        ...


@runtime_checkable
class SlideValidationPort(Protocol):
    """Validate per-slide presentation copy against the active policy.

    Implementations delegate to the unchanged slide-validation logic and return
    the canonical :class:`SlideValidationReport` so the validation behavior +
    report shape stay byte-identical. The application layer forwards the report
    opaquely; this contract introduces no behavior change.
    """

    async def validate_slides(self, project_id: str) -> SlideValidationReport:
        """Validate the project's slides and return a structured report."""
        ...


@runtime_checkable
class ImageProviderPort(Protocol):
    """Resolve an ``(image_model, image_style)`` preset to an image provider.

    The image-provider registry contract: the single source of truth for which
    ``(model, style)`` combinations are supported and which configured
    :class:`ImageProvider` (vendor service + style strategy) backs each. The
    presentation application layer (the carousel image nodes) depends only on
    this port — never on a concrete vendor SDK — so the OpenAI / Gemini adapters
    can be swapped without touching the pipeline. The concrete implementation
    (``ImageProviderRegistry``) preserves the exact resolve behavior, the
    supported combos, and the prompt-package metadata.
    """

    def resolve(self, model: str, style: str) -> ImageProvider:
        """Return the configured provider for the preset, or raise on an
        unsupported / unregistered ``(model, style)`` combo."""
        ...


__all__ = [
    "CarouselRepository",
    "ImageGenerationService",
    "ImageProvider",
    "ImageProviderPort",
    "ImageStyleStrategy",
    "PresentationPolicyPort",
    "SlideValidationPort",
]
