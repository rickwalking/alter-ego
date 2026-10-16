"""The schedule picker's signals over SQLite, and the Graph audience reader (AE-0404).

Gherkin: tests/features/telegram_schedule_picker_ae0404.feature
(Scenarios: With online_followers the peak hours rank first; Post performance
shifts the ranking with shrinkage; An insights fetch error falls back silently)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisherConfig,
)
from rag_backend.modules.autopilot.constants import STATUS_CANDIDATE_ACCEPTED
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.audience_gateway import (
    GraphAudienceGateway,
    build_audience_gateway,
    parse_online_followers,
)
from rag_backend.modules.autopilot.infrastructure.insights_models import (
    InstagramAudienceHoursModel,
    InstagramPostInsightsModel,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    ManualPublishModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.infrastructure.schedule_signals import (
    ScheduleSignalsConfig,
    SqlScheduleSignals,
)

_USER = "17841400000000000"
_NOW = datetime(2026, 10, 16, 13, 0, tzinfo=UTC)


@dataclass
class _Clock:
    at: datetime = _NOW

    def now(self) -> datetime:
        return self.at


@dataclass
class _Graph:
    hours: dict[int, int] = field(default_factory=lambda: {23: 90, 12: 10})
    fail: bool = False
    calls: int = 0

    async def online_followers(self) -> dict[int, int]:
        self.calls += 1
        if self.fail:
            raise InstagramCallError(status_code=400, error_code="100", transient=False)
        return dict(self.hours)


@dataclass
class _RacingGraph(_Graph):
    """Another request stores the account's row while this one reads Graph."""

    sessions: async_sessionmaker[AsyncSession] | None = None

    async def online_followers(self) -> dict[int, int]:
        assert self.sessions is not None
        async with self.sessions() as other:
            other.add(
                InstagramAudienceHoursModel(
                    ig_user_id=_USER, online_followers={"1": 1}, checked_at=_NOW
                )
            )
            await other.commit()
        return await super().online_followers()


@pytest_asyncio.fixture
async def sessions(tmp_path: Path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ae0404.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _signals(
    session: AsyncSession, graph: _Graph | None, clock: _Clock | None = None
) -> SqlScheduleSignals:
    return SqlScheduleSignals(
        ScheduleSignalsConfig(
            session=session, clock=clock or _Clock(), audience=graph, ig_user_id=_USER
        )
    )


async def _load_twice(
    sessions: async_sessionmaker[AsyncSession], graph: _Graph, clock: _Clock
) -> dict[int, int]:
    async with sessions() as session:
        await _signals(session, graph, clock).load()
        await session.commit()
    clock.at += timedelta(hours=2)
    async with sessions() as session:
        loaded = await _signals(session, graph, clock).load()
        await session.commit()
    return dict(loaded.audience)


@pytest.mark.integration
class TestAudienceCache:
    # Scenario: With online_followers the peak hours rank first
    @pytest.mark.asyncio
    async def test_fetched_once_a_day_and_cached(
        self, sessions: async_sessionmaker[AsyncSession]
    ) -> None:
        graph, clock = _Graph(), _Clock()
        assert await _load_twice(sessions, graph, clock) == {23: 90, 12: 10}
        assert graph.calls == 1
        clock.at += timedelta(hours=23)
        async with sessions() as session:
            await _signals(session, graph, clock).load()
        assert graph.calls == 2

    # Scenario: An insights fetch error falls back silently
    @pytest.mark.asyncio
    async def test_fetch_error_falls_back_and_waits_a_day(
        self, sessions: async_sessionmaker[AsyncSession]
    ) -> None:
        graph = _Graph(fail=True)
        assert await _load_twice(sessions, graph, _Clock()) == {}
        assert graph.calls == 1
        async with sessions() as session:
            row = await session.get(InstagramAudienceHoursModel, _USER)
        assert row is not None
        assert row.fetched_at is None

    @pytest.mark.asyncio
    async def test_fetch_error_keeps_the_cached_hours(
        self, sessions: async_sessionmaker[AsyncSession]
    ) -> None:
        graph, clock = _Graph(), _Clock()
        await _load_twice(sessions, graph, clock)
        graph.fail = True
        clock.at += timedelta(days=2)
        async with sessions() as session:
            loaded = await _signals(session, graph, clock).load()
        assert dict(loaded.audience) == {23: 90, 12: 10}
        assert graph.calls == 2

    @pytest.mark.asyncio
    async def test_without_a_gateway_only_the_cache_is_read(
        self, sessions: async_sessionmaker[AsyncSession]
    ) -> None:
        async with sessions() as session:
            assert dict((await _signals(session, None).load()).audience) == {}
        graph, clock = _Graph(), _Clock()
        await _load_twice(sessions, graph, clock)
        clock.at += timedelta(days=2)
        async with sessions() as session:
            loaded = await _signals(session, None, clock).load()
        assert dict(loaded.audience) == {23: 90, 12: 10}

    @pytest.mark.asyncio
    async def test_concurrent_save_is_logged_not_raised(
        self, sessions: async_sessionmaker[AsyncSession]
    ) -> None:
        racer = _RacingGraph(sessions=sessions)
        async with sessions() as session:
            loaded = await _signals(session, racer).load()
            await session.commit()
        assert dict(loaded.audience) == {23: 90, 12: 10}
        async with sessions() as session:
            row = await session.get(InstagramAudienceHoursModel, _USER)
        assert row is not None
        assert row.online_followers == {"1": 1}

    @pytest.mark.asyncio
    async def test_blank_account_reads_nothing(
        self, sessions: async_sessionmaker[AsyncSession]
    ) -> None:
        graph = _Graph()
        async with sessions() as session:
            config = ScheduleSignalsConfig(
                session=session, clock=_Clock(), audience=graph, ig_user_id=" "
            )
            loaded = await SqlScheduleSignals(config).load()
        assert dict(loaded.audience) == {}
        assert graph.calls == 0


async def _seed_posts(session: AsyncSession) -> None:
    topic_id = uuid4()
    session.add(
        TopicCandidateModel(
            id=topic_id,
            title="Agents",
            angle="a",
            why_viral="w",
            audience="devs",
            niche="ai",
            brief="b",
            sources=["https://x.com/a/status/1"],
            score=80,
            signal_hash=uuid4().hex,
            status=STATUS_CANDIDATE_ACCEPTED,
        )
    )
    await session.flush()
    scheduled = datetime(2026, 10, 14, 18, 0, tzinfo=UTC)  # Wed 15:00 São Paulo
    for media, at in (("1001", scheduled), ("1002", None), ("1003", None)):
        session.add(
            AutopilotRunModel(
                id=uuid4(),
                topic_candidate_id=topic_id,
                state=AutopilotRunState.PUBLISHED.value,
                state_reason=None,
                publish_attempts=1,
                telegram_message_ids=[],
                ig_post_id=media,
                scheduled_at=at,
                created_at=_NOW,
                updated_at=_NOW,
            )
        )
    session.add(
        ManualPublishModel(
            carousel_project_id=str(uuid4()),
            state="published",
            ig_post_id="2001",
            claimed_at=_NOW - timedelta(days=1),
        )
    )
    snapshots = (
        ("1001", 100, 10),
        ("1002", 0, 5),
        ("2001", 50, 5),
    )
    for media, reach, saved in snapshots:
        session.add(
            InstagramPostInsightsModel(
                media_id=media,
                reach=reach,
                saved=saved,
                shares=5,
                total_interactions=5,
                fetched_at=_NOW,
            )
        )
    await session.commit()


@pytest.mark.integration
class TestPostEngagement:
    # Scenario: Post performance shifts the ranking with shrinkage
    @pytest.mark.asyncio
    async def test_posts_join_their_insights(
        self, sessions: async_sessionmaker[AsyncSession]
    ) -> None:
        async with sessions() as session:
            await _seed_posts(session)
        async with sessions() as session:
            posts = (await _signals(session, None).load()).posts
        found = sorted((post.published_at, post.rate) for post in posts)
        assert found == [
            (datetime(2026, 10, 14, 18, 0, tzinfo=UTC), 0.2),
            (_NOW - timedelta(days=1), 0.3),
        ]


@pytest.mark.integration
class TestGraphAudienceGateway:
    def test_parse_sums_days_and_skips_odd_entries(self) -> None:
        payload: dict[str, object] = {
            "data": [
                {
                    "name": "online_followers",
                    "values": [
                        {"value": {"0": 5, "23": 7}},
                        {"value": {"0": 1, "24": 9, "x": 3, "1": True, "2": "4"}},
                        {"value": []},
                        "odd",
                    ],
                },
                {"name": "other", "values": [{"value": {"5": 50}}]},
                {"name": "online_followers", "values": "odd"},
                "odd",
            ]
        }
        assert parse_online_followers(payload) == {0: 6, 23: 7}
        assert parse_online_followers({"data": "odd"}) == {}

    @pytest.mark.asyncio
    async def test_reads_online_followers_with_the_lifetime_period(self) -> None:
        seen: list[httpx.Request] = []

        def _handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            body = {
                "data": [{"name": "online_followers", "values": [{"value": {"3": 4}}]}]
            }
            return httpx.Response(200, content=json.dumps(body))

        hours = await _gateway(_handler).online_followers()
        assert hours == {3: 4}
        params = seen[0].url.params
        assert seen[0].url.path == f"/v24.0/{_USER}/insights"
        assert params["metric"] == "online_followers"
        assert params["period"] == "lifetime"

    @pytest.mark.asyncio
    async def test_graph_error_raises_a_call_error(self) -> None:
        def _handler(request: httpx.Request) -> httpx.Response:
            del request
            return httpx.Response(400, json={"error": {"code": 100, "message": "x"}})

        with pytest.raises(InstagramCallError):
            await _gateway(_handler).online_followers()

    @pytest.mark.asyncio
    async def test_missing_token_raises_a_call_error(self) -> None:
        with pytest.raises(InstagramCallError):
            await _gateway(lambda _: httpx.Response(200), access="").online_followers()

    @pytest.mark.asyncio
    async def test_build_needs_an_account(self) -> None:
        assert build_audience_gateway(Settings(meta_ig_user_id=" ")) is None
        built = build_audience_gateway(Settings(meta_ig_user_id=_USER))
        assert isinstance(built, GraphAudienceGateway)
        async with built._client_factory() as client:
            assert client.timeout.read == 10.0


@dataclass
class _Token:
    value: str

    async def get(self) -> str:
        return self.value


def _gateway(
    handler: Callable[[httpx.Request], httpx.Response], access: str = "t"
) -> GraphAudienceGateway:
    transport = httpx.MockTransport(handler)
    return GraphAudienceGateway(
        MetaInstagramPublisherConfig(
            ig_user_id=_USER,
            graph_base="https://graph.example/v24.0",
            token_provider=_Token(access),
        ),
        lambda: httpx.AsyncClient(transport=transport),
    )
