"""Repair of checklist items whose edited text sits in the hidden body.

Feature file: tests/features/carousel_checklist_wysiwyg.feature
"""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.carousel_repair_projection import (
    apply_localized_to_slides,
    localized_from_slides,
)
from rag_backend.application.services.carousel.checklist_item_repair import (
    plan_checklist_repair,
)
from rag_backend.application.services.carousel.presentation_review_edits import (
    merge_localized_slide_edits,
)
from rag_backend.application.services.carousel_template.strategies.save_checklist import (
    checklist_items,
)
from rag_backend.domain.models.carousel import CarouselSlide
from rag_backend.domain.protocols.repositories import CarouselRepository

_EDITED_PT = "Revise o contrato antes de assinar"
_EDITED_EN = "Review the contract before signing"


def _point(title: str, body: str) -> dict[str, object]:
    return {"icon_name": "check", "title": title, "body": body}


def _slide(number: int, slide_type: str) -> CarouselSlide:
    return CarouselSlide(
        project_id=uuid4(),
        slide_number=number,
        slide_type=slide_type,
        heading="Salve",
        body="",
        extras={
            "summary_points": [
                _point("Gerado", _EDITED_PT),
                _point("Igual", "Igual"),
                _point("Sem corpo", ""),
            ],
            "translation_en": {
                "heading": "Save",
                "body": "",
                "summary_points": [
                    _point("Generated", _EDITED_EN),
                    _point("Same", "Same"),
                    _point("No body", ""),
                ],
            },
        },
    )


def _payload(record: dict[str, object], key: str) -> dict[str, object]:
    payload = record[key]
    assert isinstance(payload, dict)
    return payload


class _Repo:
    async def update_slide(self, slide: CarouselSlide) -> CarouselSlide:
        return slide


@pytest.mark.unit
def test_plan_moves_hidden_body_into_the_title_in_both_languages() -> None:
    """Only items whose non-empty body differs from the title move.

    Scenario: A repair moves hidden checklist text into the displayed line
    """
    plan = plan_checklist_repair(
        localized_from_slides([_slide(8, "summary")]), frozenset({8})
    )

    assert [(m.locale, m.item_index, m.old_title, m.new_title) for m in plan.moves] == [
        ("pt", 0, "Gerado", _EDITED_PT),
        ("en", 0, "Generated", _EDITED_EN),
    ]
    edited = plan.edited_slides[0]
    pt_points = _payload(edited, "presentation_pt")["summary_points"]
    assert isinstance(pt_points, list)
    assert pt_points[0] == _point(_EDITED_PT, "")
    assert pt_points[1] == _point("Igual", "Igual")


@pytest.mark.unit
def test_plan_leaves_slides_that_are_not_checklists() -> None:
    """A grid slide shows title and body, so its items stay as they are.

    Scenario: A repair moves hidden checklist text into the displayed line
    """
    plan = plan_checklist_repair(
        localized_from_slides([_slide(3, "summary")]), frozenset({8})
    )

    assert plan.moves == ()
    assert plan.edited_slides == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_repaired_slide_renders_the_edit_and_repairs_once() -> None:
    """After the repair the slide shows the edited text and the repair is idempotent.

    Scenario: A repair moves hidden checklist text into the displayed line
    """
    slides = [_slide(8, "summary")]
    records = localized_from_slides(slides)
    plan = plan_checklist_repair(records, frozenset({8}))

    merged = merge_localized_slide_edits(records, plan.edited_slides)
    await apply_localized_to_slides(cast("CarouselRepository", _Repo()), slides, merged)
    repaired = localized_from_slides(slides)

    assert checklist_items(_payload(repaired[0], "presentation_pt"))[0] == _EDITED_PT
    assert checklist_items(_payload(repaired[0], "presentation_en"))[0] == _EDITED_EN
    assert plan_checklist_repair(repaired, frozenset({8})).moves == ()
