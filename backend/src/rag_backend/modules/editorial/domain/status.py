"""Workflow status language for the editorial bounded context.

The editorial workflow (the 7-phase carousel editorial pipeline) already has a
canonical, single source of truth for its status language: the shared module
``rag_backend.domain.constants.carousel_workflow``. That file is imported by the
existing workflow engine, routes, and services.

**Re-export, not new strings (AE-0108 constraint).** This module introduces NO
new status strings. It re-exports the canonical phase / phase-status /
review-action / interrupt-type constants so the editorial module exposes the
same workflow status language under its own domain namespace while the legacy
import path keeps resolving to the IDENTICAL objects (object-identity shim). The
canonical definitions are NOT modified or relocated.
"""

from __future__ import annotations

from rag_backend.domain.constants.carousel_workflow import (
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
]
