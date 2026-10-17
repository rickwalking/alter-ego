"""The owner's GrokBot cover choice, read and written in SQL (AE-0418).

``SqlCoverOffers`` builds the Telegram offer of a run (its topic's cover, the
stored preview file, the owner's choice) and the project's ``slide_cover``
once the owner chose it. ``SqlCoverChoices`` stores the choice with a
compare-and-set on the run state, so a stale tap changes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import cast

from sqlalchemy import CursorResult, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.content_mode import is_pov_family
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.modules.autopilot.domain.cover import (
    CoverAsset,
    cover_credit,
    slide_cover_for,
)
from rag_backend.modules.autopilot.domain.cover_offer import CoverOffer
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverAssetReader,
    CoverChoiceCommand,
    CoverImageStore,
    CoverOffers,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.notify import ReviewFacts
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    ReviewFactsSource,
    TopicCandidateRepository,
)
from rag_backend.modules.autopilot.infrastructure.cover_images import (
    EditorialCoverImages,
)
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)


class SqlCoverOffers:
    """``CoverOffers`` over the topic, cover and creator-asset rows."""

    def __init__(
        self,
        topics: TopicCandidateRepository,
        covers: CoverAssetReader,
        images: CoverImageStore,
    ) -> None:
        self._topics = topics
        self._covers = covers
        self._images = images

    async def offer(self, run: AutopilotRun) -> CoverOffer | None:
        """The offer, or None when the topic has no usable cover."""
        found = await self._cover(run)
        if found is None:
            return None
        cover, pov = found
        path = await self._images.image_file(cover.creator_asset_id)
        if path is None:
            return None
        return CoverOffer(
            kind=cover.kind,
            credit=cover_credit(cover.source_url),
            chosen=run.cover_chosen,
            pov=pov,
            photo_path=path,
        )

    async def chosen_cover(self, run: AutopilotRun) -> SlideCover | None:
        """The project field when the owner chose the cover, else None."""
        if not run.cover_chosen:
            return None
        found = await self._cover(run)
        if found is None:
            return None
        return slide_cover_for(found[0])

    async def _cover(self, run: AutopilotRun) -> tuple[CoverAsset, bool] | None:
        topic = await self._topics.get_topic(run.topic_candidate_id)
        if topic is None or topic.cover_asset_id is None:
            return None
        covers = await self._covers.covers_by_ids((topic.cover_asset_id,))
        cover = covers.get(topic.cover_asset_id)
        if cover is None:
            return None
        return cover, is_pov_family(topic.content_mode)


class SqlCoverChoices:
    """``CoverChoiceStore``: the choice, only while the run is in ``expected``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set_cover_choice(self, command: CoverChoiceCommand) -> bool:
        """False when the run is not in ``expected`` any more."""
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == command.run_id,
                AutopilotRunModel.state == command.expected.value,
            )
            .values(cover_chosen=command.chosen)
        )
        return cast(CursorResult[object], result).rowcount == 1


@dataclass(frozen=True, kw_only=True)
class CoverFactsSources:
    """Where the review facts find the run and its cover offer."""

    runs: AutopilotRunRepository
    offers: CoverOffers


class CoverReviewFacts:
    """Review facts plus the run's cover offer (decorates the facts loader)."""

    def __init__(self, inner: ReviewFactsSource, sources: CoverFactsSources) -> None:
        self._inner = inner
        self._runs = sources.runs
        self._offers = sources.offers

    async def load(self, project_id: str) -> ReviewFacts | None:
        """The inner facts with ``cover`` set when the topic has one."""
        facts = await self._inner.load(project_id)
        if facts is None:
            return None
        run = await self._runs.find_by_carousel(project_id)
        if run is None:
            return facts
        return replace(facts, cover=await self._offers.offer(run))


def cover_review_facts(
    inner: ReviewFactsSource, session: AsyncSession
) -> CoverReviewFacts:
    """``inner`` with the cover offer of the carousel's run (one session)."""
    return CoverReviewFacts(
        inner,
        CoverFactsSources(
            runs=SqlAlchemyAutopilotRepository(session), offers=cover_offers(session)
        ),
    )


def cover_offers(session: AsyncSession) -> SqlCoverOffers:
    """The offers of one session (topics, covers and the image store)."""
    return SqlCoverOffers(
        SqlAlchemyAutopilotRepository(session),
        SqlCoverAssetStore(session),
        EditorialCoverImages(session),
    )


__all__ = [
    "CoverFactsSources",
    "CoverReviewFacts",
    "SqlCoverChoices",
    "SqlCoverOffers",
    "cover_offers",
    "cover_review_facts",
]
