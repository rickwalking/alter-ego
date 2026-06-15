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

from rag_backend.modules.presentation.application.service import (
    PresentationPorts,
    PresentationService,
)
from rag_backend.modules.presentation.bootstrap import (
    PresentationAdapters,
    PresentationModule,
    bootstrap_module,
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
    CarouselRepository,
    PresentationPolicyPort,
    SlideValidationPort,
)
from rag_backend.modules.presentation.infrastructure import (
    PresentationPersistenceAcl,
    PresentationProjectView,
    PresentationWriteOwner,
)

__all__ = [
    "CarouselPresentationPolicy",
    "CarouselProject",
    "CarouselRepository",
    "CarouselSlide",
    "ContentSlideCopy",
    "DesignPolicy",
    "DesignTokens",
    "FontPolicy",
    "GeometryBudget",
    "PresentationAdapters",
    "PresentationModule",
    "PresentationPersistenceAcl",
    "PresentationPolicyError",
    "PresentationPolicyPort",
    "PresentationPorts",
    "PresentationProject",
    "PresentationProjectView",
    "PresentationService",
    "PresentationWriteOwner",
    "SlideTypePolicy",
    "SlideValidationPort",
    "SlideValidationReport",
    "SlideValidationViolation",
    "SlideView",
    "TextBudget",
    "VisibleTextPolicy",
    "VisibleTextRule",
    "bootstrap_module",
]
