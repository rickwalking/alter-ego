"""POST /api/autopilot/topics.

Gherkin: tests/features/autopilot_topic_intake.feature

``_POV`` is a scout v3 "Ponto de Vista" topic with its draft thesis.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.modules.autopilot.application.topic_intake import (
    TopicIntakeCommand,
    TopicIntakeDependencies,
    TopicIntakeService,
)
from rag_backend.modules.autopilot.constants import (
    DEFAULT_DAILY_CAP,
    REASON_DAILY_CAP_REACHED,
    REASON_DUPLICATE_TOPIC,
    REASON_SOURCE_NOT_IN_SIGNALS,
    REASON_URL_IN_TEXT,
)
from rag_backend.modules.autopilot.domain.ports import HashLookup, RecordServedUrls
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)
from rag_backend.modules.autopilot.infrastructure.models import TopicCandidateModel
from tests.integration.autopilot_topic_support import (
    _AS_OF,
    _FOREIGN,
    _INJECTION,
    _PATH,
    _SIGNALS,
    _URL_A,
    _URL_B,
    _Bundle,
    _client,
    _Clock,
    _headers,
    _proposal,
    _queued_scores,
    _seed_carousel,
    _seed_run,
    _seed_run_on,
    _serve,
    _stored_brief,
    _topic,
    _topic_count,
    configured_key,
)

_ = configured_key
_POV = {"mode": "pov", "thesis_draft": "Quem decide o que construir ainda é o dev."}


# Scenario: Best valid topic is queued
@pytest.mark.asyncio
async def test_best_valid_topic_is_queued(configured_key: None, tmp_path: Path) -> None:
    del configured_key
    async for client, engine in _client(tmp_path / "best.db", _Clock(_AS_OF)):
        await _serve(engine, (_URL_A, _URL_B), _AS_OF)
        response = await client.post(
            _PATH,
            headers=_headers(),
            json={
                "topics": [_topic("Quiet", _URL_B, 70), _topic("Agents", _URL_A, 90)]
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body["accepted"]) == 2
    assert len(body["queued"]) == 1
    assert body["rejected"] == []
    assert await _topic_count(engine) == 2
    assert await _queued_scores(engine) == [90]


# Scenario: Invented source is rejected
# Scenario: A foreign URL rejects only that proposal
@pytest.mark.asyncio
async def test_foreign_url_rejects_only_that_proposal(
    configured_key: None, tmp_path: Path
) -> None:
    """The rejection carries the additive ``index`` (always) and ``field`` (the one
    field that caused it).
    """
    del configured_key
    async for client, engine in _client(tmp_path / "foreign.db", _Clock(_AS_OF)):
        await _serve(engine, (_URL_A,), _AS_OF)
        response = await client.post(
            _PATH,
            headers=_headers(),
            json={
                "topics": [
                    _topic("Invented", _FOREIGN, 99),
                    _topic("Grounded", _URL_A, 40),
                ]
            },
        )
    body = response.json()
    assert body["rejected"] == [
        {
            "index": 0,
            "title": "Invented",
            "reason": REASON_SOURCE_NOT_IN_SIGNALS,
            "field": "sources[0]",
        }
    ]
    assert len(body["queued"]) == 1
    assert await _queued_scores(engine) == [40]


# Scenario: Daily cap
@pytest.mark.asyncio
async def test_daily_cap_persists_and_does_not_queue(
    configured_key: None, tmp_path: Path
) -> None:
    """A cap rejection carries ``index`` but no ``field`` (it concerns the topic as a
    whole).
    """
    del configured_key
    async for client, engine in _client(tmp_path / "cap.db", _Clock(_AS_OF)):
        await _serve(engine, (_URL_A,), _AS_OF)
        for _ in range(DEFAULT_DAILY_CAP):
            await _seed_run(engine, _AS_OF)
        response = await client.post(
            _PATH,
            headers=_headers(),
            json={"topics": [_topic("Another", _URL_A, 80)]},
        )
    body = response.json()
    assert body["queued"] == []
    assert body["rejected"] == [
        {"index": 0, "title": "Another", "reason": REASON_DAILY_CAP_REACHED}
    ]
    assert len(body["accepted"]) == 1
    assert await _topic_count(engine) == DEFAULT_DAILY_CAP + 1


# Scenario: Replay is idempotent
@pytest.mark.asyncio
async def test_replay_queues_nothing_new(configured_key: None, tmp_path: Path) -> None:
    del configured_key
    payload = {"topics": [_topic("Agents", _URL_A, 90)]}
    async for client, engine in _client(tmp_path / "replay.db", _Clock(_AS_OF)):
        await _serve(engine, (_URL_A,), _AS_OF)
        first = await client.post(_PATH, headers=_headers(), json=payload)
        second = await client.post(_PATH, headers=_headers(), json=payload)
    assert first.status_code == 200
    assert second.json()["queued"] == []
    assert second.json()["accepted"] == first.json()["accepted"]
    assert second.json()["rejected"] == []
    assert await _topic_count(engine) == 1
    assert await _queued_scores(engine) == [90]


# Scenario: Schema violation persists nothing
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"topics": [_topic("Agents", _URL_A, 101)]},
        {"topics": [{**_topic("Agents", _URL_A, 90), "extra": "no"}]},
        {"topics": [_topic(f"T{i}", _URL_A, 10) for i in range(4)]},
        {"extra": True, "topics": [_topic("Agents", _URL_A, 90)]},
    ],
)
async def test_schema_violation_persists_nothing(
    configured_key: None,
    tmp_path: Path,
    payload: dict[str, object],
) -> None:
    del configured_key
    async for client, engine in _client(tmp_path / "schema.db", _Clock(_AS_OF)):
        response = await client.post(_PATH, headers=_headers(), json=payload)
    assert response.status_code == 422
    assert await _topic_count(engine) == 0


# Scenario: URL in free text is rejected
@pytest.mark.asyncio
async def test_url_in_brief_is_rejected(configured_key: None, tmp_path: Path) -> None:
    del configured_key
    async for client, engine in _client(tmp_path / "url.db", _Clock(_AS_OF)):
        await _serve(engine, (_URL_A,), _AS_OF)
        response = await client.post(
            _PATH,
            headers=_headers(),
            json={
                "topics": [
                    _topic("Agents", _URL_A, 80, brief="See https://evil.example/x")
                ]
            },
        )
    body = response.json()
    assert body["rejected"][0]["reason"] == REASON_URL_IN_TEXT
    assert body["queued"] == []
    assert await _topic_count(engine) == 0


# Scenario: Instructions in the brief stay inert text
@pytest.mark.asyncio
async def test_prompt_injection_brief_is_stored_as_text(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    async for client, engine in _client(tmp_path / "inject.db", _Clock(_AS_OF)):
        await _serve(engine, (_URL_A,), _AS_OF)
        response = await client.post(
            _PATH,
            headers=_headers(),
            json={"topics": [_topic("Carousel agents", _URL_A, 80, brief=_INJECTION)]},
        )
    assert response.status_code == 200
    assert len(response.json()["queued"]) == 1
    assert await _stored_brief(engine) == _INJECTION


# Scenario: Recent carousel topic is a duplicate
@pytest.mark.asyncio
async def test_recent_carousel_topic_is_a_duplicate(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    title = "alpha beta gamma delta"
    async for client, engine in _client(tmp_path / "dup.db", _Clock(_AS_OF)):
        await _serve(engine, (_URL_A,), _AS_OF)
        await _seed_carousel(
            engine, "alpha beta gamma epsilon", _AS_OF - timedelta(days=1)
        )
        response = await client.post(
            _PATH,
            headers=_headers(),
            json={"topics": [_topic(title, _URL_A, 80)]},
        )
    assert response.json()["rejected"][0]["reason"] == REASON_DUPLICATE_TOPIC
    assert await _topic_count(engine) == 0


# Scenario: Carousel topic older than 60 days is not a duplicate
@pytest.mark.asyncio
async def test_old_carousel_topic_is_not_a_duplicate(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    title = "alpha beta gamma delta"
    async for client, engine in _client(tmp_path / "old.db", _Clock(_AS_OF)):
        await _serve(engine, (_URL_A,), _AS_OF)
        await _seed_carousel(
            engine, "alpha beta gamma epsilon", _AS_OF - timedelta(days=61)
        )
        response = await client.post(
            _PATH,
            headers=_headers(),
            json={"topics": [_topic(title, _URL_A, 80)]},
        )
    assert response.status_code == 200
    assert len(response.json()["queued"]) == 1
    assert await _topic_count(engine) == 1


# Scenario: Control characters are stripped
@pytest.mark.asyncio
async def test_null_in_title_is_stripped(configured_key: None, tmp_path: Path) -> None:
    del configured_key
    async for client, engine in _client(tmp_path / "null.db", _Clock(_AS_OF)):
        await _serve(engine, (_URL_A,), _AS_OF)
        response = await client.post(
            _PATH,
            headers=_headers(),
            json={"topics": [_topic("Agents\x00 that ship", _URL_A, 80)]},
        )
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            title = await session.scalar(select(TopicCandidateModel.title))
    assert response.status_code == 200
    assert title == "Agents that ship"
    assert len(response.json()["queued"]) == 1


# Scenario: Signal URL older than six hours is rejected
@pytest.mark.asyncio
async def test_url_served_over_six_hours_ago_is_rejected(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    async for client, engine in _client(tmp_path / "stale.db", _Clock(_AS_OF)):
        await _serve(engine, (_URL_A,), _AS_OF - timedelta(hours=7))
        response = await client.post(
            _PATH,
            headers=_headers(),
            json={"topics": [_topic("Agents", _URL_A, 80)]},
        )
    assert response.json()["rejected"][0]["reason"] == REASON_SOURCE_NOT_IN_SIGNALS
    assert await _topic_count(engine) == 0


# Scenario: Served signals become the allowlist
@pytest.mark.asyncio
async def test_get_signals_records_the_allowlist(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    clock = _Clock(_AS_OF)
    async for client, engine in _client(tmp_path / "get.db", clock, _Bundle(_URL_A)):
        signals = await client.get(_SIGNALS, headers=_headers())
        response = await client.post(
            _PATH,
            headers=_headers(),
            json={"topics": [_topic("Agents", _URL_A, 80)]},
        )
    assert signals.status_code == 200
    assert response.status_code == 200
    assert len(response.json()["queued"]) == 1
    assert await _topic_count(engine) == 1


# Scenario: A higher daily cap queues more than one run
@pytest.mark.asyncio
async def test_higher_daily_cap_queues_both(
    configured_key: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Radar IA is capped at one a week, so the second topic is a POV topic."""
    del configured_key
    monkeypatch.setenv("AUTOPILOT_DAILY_CAP", "2")
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    async for client, engine in _client(tmp_path / "cap2.db", _Clock(_AS_OF)):
        await _serve(engine, (_URL_A, _URL_B), _AS_OF)
        response = await client.post(
            _PATH,
            headers=_headers(),
            json={
                "topics": [
                    _topic("One", _URL_A, 60),
                    {**_topic("Two", _URL_B, 70), **_POV},
                ]
            },
        )
    assert response.status_code == 200
    assert len(response.json()["queued"]) == 2
    assert set(await _queued_scores(engine)) == {70, 60}


# Scenario: Daily cap uses America/Sao_Paulo
@pytest.mark.asyncio
async def test_run_before_sao_paulo_midnight_does_not_consume_the_cap(
    db_session: AsyncSession,
) -> None:
    """The seeded run is this week's Radar IA run, so the new topic is POV."""
    moment = datetime(2026, 10, 13, 3, 30, tzinfo=UTC)
    before = datetime(2026, 10, 13, 2, 30, tzinfo=UTC)
    store = SqlAlchemyTopicIntakeStore(db_session)
    await store.record_served_urls(RecordServedUrls(urls=(_URL_A,), served_at=moment))
    await _seed_run_on(db_session, before)
    service = TopicIntakeService(
        TopicIntakeDependencies(store=store, clock=_Clock(moment), daily_cap=1)
    )
    pov = replace(
        _proposal("After midnight", _URL_A, 77),
        content_mode="pov",
        thesis_draft=_POV["thesis_draft"],
    )
    result = await service.accept(TopicIntakeCommand(proposals=(pov,)))
    assert len(result.queued) == 1
    assert result.rejected == ()


@pytest.mark.asyncio
async def test_refreshing_a_served_url_keeps_it_and_drops_stale_ones(
    db_session: AsyncSession,
) -> None:
    store = SqlAlchemyTopicIntakeStore(db_session)
    await store.record_served_urls(
        RecordServedUrls(urls=(_URL_B,), served_at=_AS_OF - timedelta(hours=7))
    )
    await store.record_served_urls(RecordServedUrls(urls=(_URL_A,), served_at=_AS_OF))
    found = await store.urls_served_since(_AS_OF - timedelta(hours=6))
    assert _URL_A in found
    assert _URL_B not in found
    assert await store.ids_for_hashes(HashLookup(hashes=())) == {}
