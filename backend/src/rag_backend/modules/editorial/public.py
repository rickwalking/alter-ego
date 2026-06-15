"""Public facade for the editorial bounded context.

**This file is the module's public API.** Cross-module code SHALL import only
the symbols re-exported here (also re-exported from the package ``__init__``);
everything else under ``rag_backend.modules.editorial.*`` is private to the
module. The dedicated Import Linter facade contract is added alongside the later
phases.

The facade exposes:

* ``EditorialService`` — the use-case entry point (scaffolding; AE-0108);
* ``EditorialProject`` / ``EditorialWorkflow`` — the editorial aggregate and its
  workflow value object (new, fully typed);
* ``CarouselProject`` / ``CarouselSlide`` / ``CarouselStatus`` /
  ``CarouselTheme`` / ``ResearchSource`` / ``ResearchSourceType`` — the carousel
  entities (re-exported, identical objects) so existing callers keep resolving;
* ``CarouselRepository`` — the carousel persistence port (re-exported,
  object-identity shim);
* the workflow status language (phases, phase statuses, review actions,
  interrupt types, caps) — re-exported from the canonical
  ``rag_backend.domain.constants.carousel_workflow`` (no new strings);
* ``EditorialAdapters`` / ``EditorialModule`` / ``bootstrap_module`` — the
  composition root (manual constructor injection).

Consumers SHALL NOT import internals such as
``rag_backend.modules.editorial.application.service`` or
``rag_backend.modules.editorial.domain.models`` directly.
"""

from rag_backend.modules.editorial.application.service import EditorialService
from rag_backend.modules.editorial.application.workflow_handlers import (
    EditorialWorkflowHandlers,
    StartWorkflowCommand,
    WorkflowEngine,
    WorkflowStateView,
)
from rag_backend.modules.editorial.bootstrap import (
    EditorialAdapters,
    EditorialModule,
    bootstrap_module,
)
from rag_backend.modules.editorial.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    CarouselTheme,
    EditorialProject,
    EditorialWorkflow,
    ResearchSource,
    ResearchSourceType,
)
from rag_backend.modules.editorial.domain.ports import CarouselRepository
from rag_backend.modules.editorial.domain.status import (
    CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
    CAROUSEL_WORKFLOW_PHASES,
    DEFAULT_PHASE_RETRY_CAP,
    DEFAULT_REVISION_CAP_PER_PHASE,
    FINAL_REVIEW_SEND_BACK_PHASES,
    INTERRUPT_TYPE_CONTENT_REVIEW,
    INTERRUPT_TYPE_DESIGN_REVIEW,
    INTERRUPT_TYPE_FINAL_REVIEW,
    INTERRUPT_TYPE_IMAGE_REVIEW,
    INTERRUPT_TYPE_OUTLINE_REVIEW,
    INTERRUPT_TYPE_RESEARCH_REVIEW,
    PHASE_BRIEF,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_PUBLISHED,
    PHASE_RESEARCH,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_PENDING,
    PHASE_STATUS_REJECTED,
    RESUME_ROUTE_SUPPORTED_ACTIONS,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_EDIT,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_REVISE,
    REVIEW_ACTIONS,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_write_owner import (
    CarouselProjectWriteOwner,
)
from rag_backend.modules.editorial.infrastructure.legacy_carousel_acl import (
    EditorialProjectView,
    LegacyCarouselAcl,
)

__all__ = [
    "CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT",
    "CAROUSEL_WORKFLOW_PHASES",
    "DEFAULT_PHASE_RETRY_CAP",
    "DEFAULT_REVISION_CAP_PER_PHASE",
    "FINAL_REVIEW_SEND_BACK_PHASES",
    "INTERRUPT_TYPE_CONTENT_REVIEW",
    "INTERRUPT_TYPE_DESIGN_REVIEW",
    "INTERRUPT_TYPE_FINAL_REVIEW",
    "INTERRUPT_TYPE_IMAGE_REVIEW",
    "INTERRUPT_TYPE_OUTLINE_REVIEW",
    "INTERRUPT_TYPE_RESEARCH_REVIEW",
    "PHASE_BRIEF",
    "PHASE_CONTENT",
    "PHASE_DESIGN",
    "PHASE_FINAL_REVIEW",
    "PHASE_IMAGES",
    "PHASE_OUTLINE",
    "PHASE_PUBLISHED",
    "PHASE_RESEARCH",
    "PHASE_STATUS_APPROVED",
    "PHASE_STATUS_AWAITING_HUMAN",
    "PHASE_STATUS_FAILED",
    "PHASE_STATUS_IN_PROGRESS",
    "PHASE_STATUS_PENDING",
    "PHASE_STATUS_REJECTED",
    "RESUME_ROUTE_SUPPORTED_ACTIONS",
    "REVIEW_ACTIONS",
    "REVIEW_ACTION_APPROVE",
    "REVIEW_ACTION_EDIT",
    "REVIEW_ACTION_REJECT",
    "REVIEW_ACTION_REVISE",
    "WORKFLOW_STATUS_APPROVED_FOR_PUBLISH",
    "CarouselProject",
    "CarouselProjectWriteOwner",
    "CarouselRepository",
    "CarouselSlide",
    "CarouselStatus",
    "CarouselTheme",
    "EditorialAdapters",
    "EditorialModule",
    "EditorialProject",
    "EditorialProjectView",
    "EditorialService",
    "EditorialWorkflow",
    "EditorialWorkflowHandlers",
    "LegacyCarouselAcl",
    "ResearchSource",
    "ResearchSourceType",
    "StartWorkflowCommand",
    "WorkflowEngine",
    "WorkflowStateView",
    "bootstrap_module",
]
