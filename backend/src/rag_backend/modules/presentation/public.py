"""Public facade for the presentation bounded context.

**This file is the module's public API.** Cross-module code SHALL import only
the symbols re-exported here (also re-exported from the package ``__init__``);
everything else under ``rag_backend.modules.presentation.*`` is private to the
module.

The facade exposes:

* ``PresentationService`` — the use-case entry point (scaffolding; AE-0117);
* ``PresentationProject`` / ``DesignPolicy`` / ``SlideView`` — the presentation
  VIEW aggregate and its value objects (new, fully typed);
* the presentation policy types (``CarouselPresentationPolicy``,
  ``SlideTypePolicy``, ``GeometryBudget``, ``FontPolicy``, ``TextBudget``,
  ``VisibleTextPolicy``, ``VisibleTextRule``, ``PresentationPolicyError``) —
  re-exported, identical objects, from
  ``application.services.carousel.presentation_policy_types``;
* ``ContentSlideCopy`` / ``SlideValidationReport`` / ``SlideValidationViolation``
  — the per-slide presentation/validation models (re-exported, identical
  objects, from ``domain.models.carousel_presentation``);
* ``CarouselProject`` / ``CarouselSlide`` / ``DesignTokens`` — the carousel
  entities/types (re-exported, identical objects) so existing callers keep
  resolving;
* ``CarouselRepository`` — the carousel persistence port (re-exported,
  object-identity shim);
* ``PresentationPolicyPort`` / ``SlideValidationPort`` — the presentation
  provider ports (new Protocols);
* ``ImageGenerationService`` / ``ImageStyleStrategy`` / ``ImageProvider`` /
  ``ImageProviderPort`` — the image-generation ports + value object (AE-0119):
  the per-vendor generation/style contracts (re-exported object-identity shims),
  the provider value object, and the registry contract; the concrete vendor
  adapters (``OpenAIImageService`` / ``GeminiImageService``) and the
  ``ImageProviderRegistry`` implement them. Vendor SDK imports stay in the
  adapter layer;
* ``PresentationWriteOwner`` / ``PresentationPersistenceAcl`` /
  ``PresentationProjectView`` — the AE-0118 presentation persistence seam: the
  single writer of the presentation columns + slide rows (and the owner of the
  ``artifact_version`` ↔ ``lock_version`` compound CAS delegation), the
  read/write ACL over it, and its concurrency-token view. Editorial / global
  callers reach presentation persistence ONLY through these facade symbols;
* ``PresentationAdapters`` / ``PresentationModule`` / ``bootstrap_module`` — the
  composition root (manual constructor injection).

Consumers SHALL NOT import internals such as
``rag_backend.modules.presentation.application.service`` or
``rag_backend.modules.presentation.domain.models`` directly.
"""

from rag_backend.modules.presentation.application.handlers import (
    CreatorAssetResult,
    PresentationBulkResult,
    PresentationCollaborators,
    PresentationHandlers,
    SlideMissingPredicate,
)
from rag_backend.modules.presentation.application.service import (
    PresentationPorts,
    PresentationService,
)
from rag_backend.modules.presentation.bootstrap import (
    PresentationAdapters,
    PresentationModule,
    bootstrap_module,
)
from rag_backend.modules.presentation.domain.contracts import (
    ArtifactActivation,
    ProducedArtifact,
    ProduceFormat,
    ProgressSnapshot,
)
from rag_backend.modules.presentation.domain.models import (
    CarouselPresentationPolicy,
    CarouselProject,
    CarouselSlide,
    ContentSlideCopy,
    DesignPolicy,
    DesignTokens,
    FontPolicy,
    GeometryBudget,
    PresentationPolicyError,
    PresentationProject,
    SlideTypePolicy,
    SlideValidationReport,
    SlideValidationViolation,
    SlideView,
    TextBudget,
    VisibleTextPolicy,
    VisibleTextRule,
)
from rag_backend.modules.presentation.domain.ports import (
    ArtifactBuildPort,
    CarouselRepository,
    ContentFormatProducer,
    ImageGenerationService,
    ImageProvider,
    ImageProviderPort,
    ImageStyleStrategy,
    PresentationPolicyPort,
    PresentationReviewPort,
    SlideValidationPort,
    WorkflowProgressPort,
)
from rag_backend.modules.presentation.infrastructure import (
    CarouselArtifactBuildAdapter,
    CarouselFormatProducer,
    GeminiImageService,
    ImageProviderRegistry,
    OpenAIImageService,
    PresentationPersistenceAcl,
    PresentationProjectView,
    PresentationReviewAdapter,
    PresentationWriteOwner,
    ProgressReporter,
    WorkflowProgressCallback,
    apply_localized_slide_edits_via_port,
)

__all__ = [
    "ArtifactActivation",
    "ArtifactBuildPort",
    "CarouselArtifactBuildAdapter",
    "CarouselFormatProducer",
    "CarouselPresentationPolicy",
    "CarouselProject",
    "CarouselRepository",
    "CarouselSlide",
    "ContentFormatProducer",
    "ContentSlideCopy",
    "CreatorAssetResult",
    "DesignPolicy",
    "DesignTokens",
    "FontPolicy",
    "GeminiImageService",
    "GeometryBudget",
    "ImageGenerationService",
    "ImageProvider",
    "ImageProviderPort",
    "ImageProviderRegistry",
    "ImageStyleStrategy",
    "OpenAIImageService",
    "PresentationAdapters",
    "PresentationBulkResult",
    "PresentationCollaborators",
    "PresentationHandlers",
    "PresentationModule",
    "PresentationPersistenceAcl",
    "PresentationPolicyError",
    "PresentationPolicyPort",
    "PresentationPorts",
    "PresentationProject",
    "PresentationProjectView",
    "PresentationReviewAdapter",
    "PresentationReviewPort",
    "PresentationService",
    "PresentationWriteOwner",
    "ProduceFormat",
    "ProducedArtifact",
    "ProgressReporter",
    "ProgressSnapshot",
    "SlideMissingPredicate",
    "SlideTypePolicy",
    "SlideValidationPort",
    "SlideValidationReport",
    "SlideValidationViolation",
    "SlideView",
    "TextBudget",
    "VisibleTextPolicy",
    "VisibleTextRule",
    "WorkflowProgressCallback",
    "WorkflowProgressPort",
    "apply_localized_slide_edits_via_port",
    "bootstrap_module",
]
