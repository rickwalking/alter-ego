"""The guard on slide 1 of approved and published carousels, over fakes.

Gherkin: tests/features/website_cover_review_switch_ae0594.feature
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from rag_backend.application.services.carousel.cover_pick import (
    CoverPickCommand,
    CoverPickDeps,
    CoverPickError,
    CoverPickService,
)
from rag_backend.application.services.carousel.cover_switch_guard import (
    ReviewState,
    cover_switch_refusal,
    review_state_of,
)
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
    REASON_AUTO_SELECT_APPROVED,
    REASON_AUTO_SELECT_PUBLISHED,
)
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from tests.unit.application.cover_review_fakes import APPROVED, in_review
from tests.unit.application.test_cover_pick_ae0445 import (
    _Library,
    _Offers,
    _photo,
    _Switcher,
)


@dataclass
class _Review:
    state: ReviewState | None

    async def review_state(self, project_id: str) -> ReviewState | None:
        del project_id
        return self.state


_Photos = tuple[CarouselCreatorAsset, CarouselCreatorAsset]


def _picker(state: ReviewState | None) -> tuple[CoverPickService, _Switcher, _Photos]:
    a, b = _photo("a"), _photo("b")
    switcher = _Switcher()
    service = CoverPickService(
        CoverPickDeps(
            library=_Library((a, b)),
            offers=_Offers(),
            switcher=switcher,
            review=_Review(state),
        )
    )
    return service, switcher, (a, b)


@pytest.mark.unit
class TestGuard:
    # Scenario: The picker refuses an approved carousel
    # Scenario: The picker refuses a published carousel
    def test_refusal_reasons(self) -> None:
        draft = ReviewState(workflow_status="draft", is_public=False)
        assert cover_switch_refusal(draft) is None
        assert (
            cover_switch_refusal(ReviewState(workflow_status="", is_public=False))
            is None
        )
        approved = ReviewState(workflow_status=APPROVED, is_public=False)
        assert cover_switch_refusal(approved) == REASON_AUTO_SELECT_APPROVED
        public = review_state_of(in_review(is_public=True), "draft")
        assert cover_switch_refusal(public) == REASON_AUTO_SELECT_PUBLISHED

    # Scenario: The picker refuses an approved carousel
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("status", "public"), [(APPROVED, False), ("draft", True), (APPROVED, True)]
    )
    async def test_picker_refuses_before_switching(
        self, status: str, public: bool
    ) -> None:
        state = ReviewState(workflow_status=status, is_public=public)
        service, switcher, photos = _picker(state)
        a, b = photos
        project = in_review(owner_id="owner-1", hook_asset_id=a.id)

        with pytest.raises(CoverPickError) as refused:
            await service.pick(
                CoverPickCommand(project=project, asset_id=b.id, expected_version=7)
            )

        assert refused.value.code == ERR_COVER_SWITCH_REQUIRES_REVIEW
        assert switcher.commands == []

    # Scenario: The picker refuses an approved carousel
    @pytest.mark.asyncio
    async def test_an_unknown_state_lets_the_switch_decide(self) -> None:
        service, switcher, photos = _picker(None)
        a, b = photos
        project = in_review(owner_id="owner-1", hook_asset_id=a.id)

        await service.pick(
            CoverPickCommand(project=project, asset_id=b.id, expected_version=7)
        )

        assert len(switcher.commands) == 1
