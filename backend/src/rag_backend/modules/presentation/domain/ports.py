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

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from rag_backend.application.services.image_provider_registry import ImageProvider
from rag_backend.domain.protocols.carousel import (
    ImageGenerationService,
    ImageStyleStrategy,
)
from rag_backend.domain.protocols.repositories import CarouselRepository
from rag_backend.modules.presentation.domain.contracts import (
    ArtifactActivation,
    ProducedArtifact,
    ProduceFormat,
    ProgressSnapshot,
)
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


@runtime_checkable
class WorkflowProgressPort(Protocol):
    """Report an image-generation progress snapshot BACK to editorial (callback).

    This is the presentation → editorial **callback port** (AE-0121). The image
    node generates images (a presentation concern) but ``phase_progress`` is a
    WORKFLOW-owned column (AE-0105 §2.3) — presentation must NOT write it. Instead
    the node hands a :class:`ProgressSnapshot` to this port; the EDITORIAL side
    implements it and performs the byte-identical ``phase_progress`` persist + SSE
    emission. The Protocol is defined HERE (in presentation) so the presentation
    image node depends only on its own port — never on an editorial internal — and
    the dependency direction stays editorial → presentation (no cycle).
    """

    async def report_progress(self, snapshot: ProgressSnapshot) -> None:
        """Persist the workflow ``phase_progress`` + publish it to the SSE stream."""
        ...


@runtime_checkable
class ContentFormatProducer(Protocol):
    """Produce a renderable presentation artifact for a project (extension point).

    The presentation-specific format boundary (AE-0121): a producer declares the
    ``format_name`` it owns and produces a :class:`ProducedArtifact` from a
    :class:`ProduceFormat` command. This is intentionally NOT a generic
    multi-format framework — carousel is the only producer today; a second format
    would add a second producer implementing this same Protocol, not a new
    abstraction layer. The concrete carousel producer delegates to the unchanged
    bilingual re-render so the rendered slides/PDFs stay byte-identical.
    """

    @property
    def format_name(self) -> str:
        """The format this producer owns (e.g. ``"carousel"``)."""
        ...

    async def produce(self, command: ProduceFormat) -> ProducedArtifact:
        """Render the project's slides + PDFs and return the artifact pointers."""
        ...


@runtime_checkable
class ArtifactBuildPort(Protocol):
    """Build + activate a project's output artifact (the activation CAS surface).

    Fronts the finalize → artifact-build call. The concrete adapter delegates
    UNCHANGED to ``CarouselArtifactBuildService.build_and_activate``, preserving
    the compound ``artifact_version`` ↔ ``lock_version`` compare-and-swap, the
    PDF-path stamping, and the design-token merge exactly (AE-0115 §3). It
    reports the outcome as an :class:`ArtifactActivation`.
    """

    async def build_and_activate(self, project_id: str) -> ArtifactActivation:
        """Stage → manifest → promote → run the activation CAS; report the outcome."""
        ...


@runtime_checkable
class PresentationReviewPort(Protocol):
    """Apply reviewer slide-copy edits to workflow state with re-validation.

    Fronts the presentation review/validation step the workflow content-review
    gate runs. The concrete adapter delegates UNCHANGED to
    ``apply_localized_slide_edits`` / ``edited_slides_block_approval`` so the
    re-validation behavior + the returned state-update shape stay byte-identical.
    The editorial workflow nodes call this through the facade port instead of
    importing the presentation review service directly (carousel = presentation
    only for every presentation path).
    """

    def apply_slide_edits(
        self,
        state: Mapping[str, object],
        edited_slides: list[dict[str, object]],
    ) -> dict[str, object]:
        """Apply edits and return the re-validated workflow-state updates."""
        ...

    def edits_block_approval(
        self,
        state: Mapping[str, object],
        edited_slides: list[dict[str, object]],
    ) -> bool:
        """Whether edited slides still carry blocking presentation violations."""
        ...


__all__ = [
    "ArtifactActivation",
    "ArtifactBuildPort",
    "CarouselRepository",
    "ContentFormatProducer",
    "ImageGenerationService",
    "ImageProvider",
    "ImageProviderPort",
    "ImageStyleStrategy",
    "PresentationPolicyPort",
    "PresentationReviewPort",
    "ProduceFormat",
    "ProducedArtifact",
    "ProgressSnapshot",
    "SlideValidationPort",
    "WorkflowProgressPort",
]
