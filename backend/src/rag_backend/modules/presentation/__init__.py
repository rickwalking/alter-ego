"""Presentation bounded context (Supporting) — AE-0117 Phase 5 skeleton.

The presentation context owns the *visual contract* over a carousel project: the
versioned presentation policy (slide budgets, geometry, fonts), the per-slide
presentation copy / validation shapes, and a read VIEW over the carousel row's
presentation fields (design tokens, policy identity, activation
``artifact_version``). This package follows the module conventions
(``docs/architecture/module-conventions.md``, AE-0081) and ADR-0009 (Domain
Modular Monolith):

* per-module internal layers — ``domain/``, ``application/``,
  ``infrastructure/``, ``api/``;
* the **public-facade rule** — cross-module code imports ONLY from this
  package's public API (``public.py``, re-exported here);
* manual constructor injection via ``bootstrap_module`` (ADR-0009 §9);
* the Unit-of-Work boundary owned at the application layer.

Phase 5 is **behavior-preserving** (AE-0117): the presentation policy types, the
per-slide presentation/validation models, the carousel entities, and the
``CarouselRepository`` port are *re-exported* from their canonical locations (no
physical move, object-identity shims). The new ``PresentationProject`` VIEW,
``DesignPolicy``, and ``SlideView`` model the presentation view. Routes/ACL/
provider ports move behind this facade in AE-0118/0119/0120. Presentation does
NOT own blog/distribution, publishing/``is_public``, persona, or workflow state
(those are editorial / Phase 6).

Cross-module consumers SHALL import from the facade only, e.g.::

    from rag_backend.modules.presentation import (
        PresentationService,
        PresentationProject,
    )
"""

from rag_backend.modules.presentation.public import (
    CarouselPresentationPolicy,
    CarouselProject,
    CarouselRepository,
    CarouselSlide,
    ContentSlideCopy,
    DesignPolicy,
    DesignTokens,
    FontPolicy,
    GeometryBudget,
    PresentationAdapters,
    PresentationModule,
    PresentationPolicyError,
    PresentationPolicyPort,
    PresentationPorts,
    PresentationProject,
    PresentationService,
    SlideTypePolicy,
    SlideValidationPort,
    SlideValidationReport,
    SlideValidationViolation,
    SlideView,
    TextBudget,
    VisibleTextPolicy,
    VisibleTextRule,
    bootstrap_module,
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
    "PresentationPolicyError",
    "PresentationPolicyPort",
    "PresentationPorts",
    "PresentationProject",
    "PresentationService",
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
