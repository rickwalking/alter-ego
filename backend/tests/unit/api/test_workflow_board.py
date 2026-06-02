"""Unit tests for workflow Kanban board API (UI-018)."""

from rag_backend.api.routes.workflow_board import KANBAN_PHASES
from rag_backend.domain.constants.carousel_workflow import PHASE_PUBLISHED


def test_kanban_includes_published_column() -> None:
    """Published carousels must appear in a dedicated Kanban column."""
    assert PHASE_PUBLISHED in KANBAN_PHASES
    assert KANBAN_PHASES[-1] == PHASE_PUBLISHED
