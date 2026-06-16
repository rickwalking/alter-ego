"""Module-level constants for the publishing bounded context.

Per backend/CLAUDE.md, each context owns its own ``constants`` file and no
magic strings appear in code. These constants identify the module for
tracing/observability metadata.

No new *domain* status/state strings are introduced here (AE-0126 constraint):
the blog workflow status language is re-exported (object-identity) from the
canonical :class:`~rag_backend.domain.constants.blog_post.BlogPostStatus`. Only
the module identity label lives here.
"""

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_PUBLISHED,
    PHASE_RESEARCH,
)

# Module identity (used for tracing/observability metadata).
MODULE_NAME = "publishing"

# Workflow-board phase columns, in display order (AE-0131). Single source of
# truth for both the read projection (the column grouping/order) and the legacy
# ``workflow_board`` route alias — re-exported via the facade so the route no
# longer owns the carousel-phase ordering. Byte-identical to the legacy
# ``KANBAN_PHASES`` ending in ``PHASE_PUBLISHED``.
BOARD_PHASES = [
    PHASE_BRIEF,
    PHASE_RESEARCH,
    PHASE_OUTLINE,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_IMAGES,
    PHASE_FINAL_REVIEW,
    PHASE_PUBLISHED,
]
