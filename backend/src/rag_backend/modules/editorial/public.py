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
  composition root (manual constructor injection);
* ``CarouselAutomationAcl`` and the ``build_start_input`` /
  ``build_resume_input`` / ``content_approve_blocker`` / ``is_provider_outage``
  helpers — the in-process automation seam the autopilot module drives the
  workflow through (AE-0348 QA r1), so it imports no legacy carousel code.

Consumers SHALL NOT import internals such as
``rag_backend.modules.editorial.application.service`` or
``rag_backend.modules.editorial.domain.models`` directly.
"""

from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
    AUTOFIX_STATUS_NOTHING_TO_FIX,
)
from rag_backend.modules.editorial.application.service import (
    EditorialPorts,
    EditorialService,
)
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
from rag_backend.modules.editorial.domain.ports import (
    ApprovalPort,
    CarouselRepository,
    OptimisticLockingPort,
    PublicReleasePort,
    ReviewDecisionPort,
    ReviewerAssignmentPort,
    SourceMaterialPort,
)
from rag_backend.modules.editorial.domain.release import (
    ApprovalState,
    PublicReleaseState,
)
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
from rag_backend.modules.editorial.infrastructure.carousel_automation import (
    AutomationResume,
    AutomationResumeInput,
    AutomationStart,
    CarouselAutomationAcl,
    CarouselReviewRow,
    EditorialWorkflowEngine,
    RunHeartbeat,
    build_resume_input,
    build_start_input,
    content_approve_blocker,
    is_provider_outage,
    slides_in_config,
)
from rag_backend.modules.editorial.infrastructure.carousel_automation_run import (
    AutomationRun,
    redrive_automation_phase,
    run_automation_phase,
)
from rag_backend.modules.editorial.infrastructure.carousel_owner_autofix import (
    OwnerAutofixReport,
    OwnerAutofixRequest,
    OwnerIssues,
    inspect_owner_issues,
    run_owner_autofix,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_lock import (
    carousel_project_lock,
    carousel_project_lock_key,
    is_carousel_project_lock_held,
    is_carousel_project_lock_held_session,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_write_owner import (
    CarouselProjectWriteOwner,
)
from rag_backend.modules.editorial.infrastructure.carousel_run_progress import (
    read_project_owner_id,
    read_run_fence,
    write_run_heartbeat,
    write_run_heartbeat_once,
    write_run_heartbeat_with_retry,
)
from rag_backend.modules.editorial.infrastructure.editorial_port_adapters import (
    AclApprovalAdapter,
    AclOptimisticLockingAdapter,
    AclPublicReleaseAdapter,
    AclReviewerAssignmentAdapter,
    EngineReviewDecisionAdapter,
    EngineSourceMaterialAdapter,
    ReviewWorkflowEngine,
    SourceSynthesisEngine,
)
from rag_backend.modules.editorial.infrastructure.legacy_carousel_acl import (
    EditorialProjectView,
    LegacyCarouselAcl,
)

__all__ = [
    "AUTOFIX_STATUS_CONFLICT",
    "AUTOFIX_STATUS_FIXED",
    "AUTOFIX_STATUS_NOTHING_TO_FIX",
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
    "AclApprovalAdapter",
    "AclOptimisticLockingAdapter",
    "AclPublicReleaseAdapter",
    "AclReviewerAssignmentAdapter",
    "ApprovalPort",
    "ApprovalState",
    "AutomationResume",
    "AutomationResumeInput",
    "AutomationRun",
    "AutomationStart",
    "CarouselAutomationAcl",
    "CarouselProject",
    "CarouselProjectWriteOwner",
    "CarouselRepository",
    "CarouselReviewRow",
    "CarouselSlide",
    "CarouselStatus",
    "CarouselTheme",
    "EditorialAdapters",
    "EditorialModule",
    "EditorialPorts",
    "EditorialProject",
    "EditorialProjectView",
    "EditorialService",
    "EditorialWorkflow",
    "EditorialWorkflowEngine",
    "EditorialWorkflowHandlers",
    "EngineReviewDecisionAdapter",
    "EngineSourceMaterialAdapter",
    "LegacyCarouselAcl",
    "OptimisticLockingPort",
    "OwnerAutofixReport",
    "OwnerAutofixRequest",
    "OwnerIssues",
    "PublicReleasePort",
    "PublicReleaseState",
    "ResearchSource",
    "ResearchSourceType",
    "ReviewDecisionPort",
    "ReviewWorkflowEngine",
    "ReviewerAssignmentPort",
    "RunHeartbeat",
    "SourceMaterialPort",
    "SourceSynthesisEngine",
    "StartWorkflowCommand",
    "WorkflowEngine",
    "WorkflowStateView",
    "bootstrap_module",
    "build_resume_input",
    "build_start_input",
    "carousel_project_lock",
    "carousel_project_lock_key",
    "content_approve_blocker",
    "inspect_owner_issues",
    "is_carousel_project_lock_held",
    "is_carousel_project_lock_held_session",
    "is_provider_outage",
    "read_project_owner_id",
    "read_run_fence",
    "redrive_automation_phase",
    "run_automation_phase",
    "run_owner_autofix",
    "slides_in_config",
    "write_run_heartbeat",
    "write_run_heartbeat_once",
    "write_run_heartbeat_with_retry",
]
