"""AE-0437: a revision re-drafts only the slides it names (QA F-10).

Gherkin: tests/features/closing_actions_scoped_revisions_ae0437.feature
(section D). Real engine + real artifact runner (the AE-0405 harness); the
drafting model is a spy that, like a model ignoring the prompt, returns a
fresh draft for EVERY slide, so the scope must be enforced in code.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import cast

import pytest

from rag_backend.application.services.carousel.editorial_workflow_generators import (
    SlideDraftGenerationParams,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import REVIEW_ACTION_REVISE
from tests.unit.agents.content_feedback_flow_ae0405 import (
    GENERATE_TARGET,
    DraftingModel,
    Review,
    build_engine,
    drafts_for,
    localized_slide,
    park_at_content,
    review,
    state_of,
)

_SCOPED_NOTE = "Altere apenas o slide 6. Não altere nenhum outro slide."
_GENERAL_NOTE = "Deixe o tom mais leve."
_UNSCOPED = (1, 2, 3, 4, 5, 7)


class _ScopeSpy(DraftingModel):
    """Records the slides each generation was allowed to draft."""

    def __init__(self) -> None:
        super().__init__()
        self.scopes: list[frozenset[int] | None] = []

    async def __call__(
        self, agent: object, params: SlideDraftGenerationParams
    ) -> list[dict[str, object]]:
        self.scopes.append(params.only_slides)
        return await super().__call__(agent, params)


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch) -> Iterator[_ScopeSpy]:
    spy = _ScopeSpy()
    monkeypatch.setattr(GENERATE_TARGET, spy)
    yield spy


def _copy(state: CarouselWorkflowState, index: int) -> tuple[object, object]:
    slide = localized_slide(state, index)
    return slide["presentation_pt"], slide["presentation_en"]


def _draft_text(state: CarouselWorkflowState, index: int) -> str:
    drafts = cast(list[dict[str, object]], state.get("slide_drafts") or [])
    return str(next(d for d in drafts if d["slide_index"] == index)["draft_text"])


@pytest.mark.unit
@pytest.mark.asyncio
class TestScopedRevision:
    async def test_named_slide_is_the_only_one_redrafted(
        self, model: _ScopeSpy
    ) -> None:
        """Scenario: A scoped revision re-drafts only the named and blocked slides."""
        engine = build_engine(model)
        await park_at_content(engine)
        parked = await state_of(engine)
        assert model.scopes == [None]  # a first draft is never scoped

        await review(engine, Review(action=REVIEW_ACTION_REVISE, feedback=_SCOPED_NOTE))

        state = await state_of(engine)
        assert model.scopes[-1] == frozenset({6})
        for index in _UNSCOPED:
            assert _copy(state, index) == _copy(parked, index), index
            assert _draft_text(state, index) == _draft_text(parked, index), index
        assert _copy(state, 6) != _copy(parked, 6)
        assert "terceira" in _draft_text(state, 6)
        features = cast(dict[str, object], _copy(state, 3)[0])["features"]
        assert features == cast(dict[str, object], _copy(parked, 3)[0])["features"]

    async def test_general_note_still_rewrites_the_deck(self, model: _ScopeSpy) -> None:
        """Scenario: A general revision note still rewrites the whole deck."""
        engine = build_engine(model)
        await park_at_content(engine)

        await review(
            engine, Review(action=REVIEW_ACTION_REVISE, feedback=_GENERAL_NOTE)
        )

        state = await state_of(engine)
        assert model.scopes[-1] is None
        assert all("terceira" in _draft_text(state, n) for n in range(2, 7))

    async def test_scope_keeps_the_deck_valid(self, model: _ScopeSpy) -> None:
        """The merged deck is re-validated as a whole (reports stay in step)."""
        engine = build_engine(model)
        await park_at_content(engine)

        await review(engine, Review(action=REVIEW_ACTION_REVISE, feedback=_SCOPED_NOTE))

        state = await state_of(engine)
        slides = state.get("localized_slides") or []
        assert [slide["slide_index"] for slide in slides] == list(range(1, 8))
        assert len(drafts_for(2)) == len(state.get("slide_drafts") or [])
        assert "presentation_validation" in state
