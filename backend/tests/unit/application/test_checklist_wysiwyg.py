"""Checklist slides: the editor edits the line the slide shows.

Feature file: tests/features/carousel_checklist_wysiwyg.feature
"""

from __future__ import annotations

import pytest

from rag_backend.api.routes.carousels.editorial_workflow_routes_layouts import (
    apply_checklist_slides,
)
from rag_backend.api.schemas.carousel_workflow import (
    EditorialWorkflowStateResponse,
    LocalizedSlideReview,
)
from rag_backend.application.services.carousel_template.role_layouts import (
    checklist_slide_numbers,
)
from rag_backend.domain.models import CarouselProject

_POV_TYPES = {
    1: "intro",
    2: "content",
    3: "content",
    4: "content",
    5: "content",
    6: "content",
    7: "content",
    8: "summary",
    9: "cta",
}


def _project(**changes: object) -> CarouselProject:
    project = CarouselProject(topic="T", audience="Devs", niche="IA")
    project.content_mode = "pov"
    project.presentation_policy_version = "pov_hook_v1"
    project.slide_count = 9
    project.cta_goal = "send"
    project.creator_handle = "pedromarins.ai"
    project.slide_layout_strategy = "numbered_list"
    for key, value in changes.items():
        setattr(project, key, value)
    return project


@pytest.mark.unit
def test_pov_save_slide_is_a_checklist_slide() -> None:
    """The POV save role renders its items as checklist lines.

    Scenario: The editor knows which slides render items as checklist lines
    """
    assert checklist_slide_numbers(_project(), _POV_TYPES) == {8}


@pytest.mark.unit
def test_deck_checklist_layout_marks_summary_and_closing() -> None:
    """A non-POV deck that picked the checklist layout marks summary and closing.

    Scenario: The editor knows which slides render items as checklist lines
    """
    project = _project(content_mode=None, slide_layout_strategy="save_checklist")
    types = {1: "intro", 2: "content", 3: "summary", 4: "closing", 5: "cta"}

    assert checklist_slide_numbers(project, types) == {3, 4}


@pytest.mark.unit
def test_save_role_on_an_unsupported_slide_type_is_not_a_checklist() -> None:
    """The renderer falls back to another layout when the type is not supported.

    Scenario: The editor knows which slides render items as checklist lines
    """
    types = {**_POV_TYPES, 8: "content"}

    assert checklist_slide_numbers(_project(), types) == set()


@pytest.mark.unit
def test_other_decks_have_no_checklist_slides() -> None:
    """A regular deck renders summary points as a grid (title and body).

    Scenario: The editor knows which slides render items as checklist lines
    """
    project = _project(content_mode=None, slide_layout_strategy="numbered_list")

    assert checklist_slide_numbers(project, {1: "intro", 2: "summary"}) == set()


@pytest.mark.unit
def test_workflow_state_lists_the_checklist_slides() -> None:
    """The workflow state response carries the checklist slide numbers.

    Scenario: The editor knows which slides render items as checklist lines
    """
    response = EditorialWorkflowStateResponse(
        project_id="p",
        current_phase="content",
        phase_status="awaiting_human",
        localized_slides=[
            LocalizedSlideReview(slide_index=number, slide_type=slide_type)
            for number, slide_type in _POV_TYPES.items()
        ],
    )

    marked = apply_checklist_slides(response, _project())

    assert marked.checklist_slide_indexes == [8]
