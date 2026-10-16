"""POST /x-signals then /topics with ``pov_news`` quotes (AE-0406, spec §2-§6).

Gherkin: tests/features/autopilot_pov_news_ae0406.feature
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from rag_backend.modules.autopilot.infrastructure.models import TopicCandidateModel
from tests.integration.autopilot_scout_support import (
    _PATH_TOPICS,
    _PATH_X,
    _body,
    _client,
    _status_url,
    configured_key,
)
from tests.integration.autopilot_topic_support import _headers

_ = configured_key
_HANDLE = "kanishksj01"
_TEXT = (
    "In just a day I have run hundreds of cloud agents in parallel\r\n"
    "across all the lessons in my physics learning app."
)
_EXCERPT = "cloud agents in parallel across all the lessons"


def _quote(url: str, **changes: str) -> dict[str, str]:
    row = {
        "id": "q1",
        "url": url,
        "handle": _HANDLE,
        "name": "Kanishk Jain",
        "excerpt": _EXCERPT,
        "lang_original": "en",
        "text_pt": "Rodei centenas de agentes em paralelo.",
        "text_en": "I ran hundreds of agents in parallel.",
    }
    row.update(changes)
    return row


def _topic(title: str, url: str, quotes: list[dict[str, str]]) -> dict[str, object]:
    return {
        "mode": "pov_news",
        "title": title,
        "angle": "O custo vai para a revisão.",
        "why_viral": "Devs postam números.",
        "audience": "devs",
        "niche": "agentes de IA",
        "brief": f"Relatos sobre {title.lower()} e o custo de revisão.",
        "sources": [url],
        "score": 78,
        "thesis_draft": "Agentes em paralelo são um gargalo de revisão.",
        "slide_count": 9,
        "quotes": quotes,
    }


async def _send_post(client: AsyncClient) -> str:
    url = _status_url(_HANDLE, timedelta(hours=2))
    response = await client.post(
        _PATH_X, headers=_headers(), json={"posts": [_body(url, _HANDLE, _TEXT)]}
    )
    assert response.status_code == 200
    assert response.json()["accepted"] == [url]
    return url


async def _stored_quotes(engine: AsyncEngine) -> list[object]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        rows = (await session.execute(select(TopicCandidateModel))).scalars().all()
        return [row.quotes for row in rows]


# Scenario: A pov_news topic with one verified quote is accepted and queued
# Scenario Outline: A quote problem rejects only that topic
@pytest.mark.asyncio
async def test_verified_quote_is_stored_and_a_bad_one_rejects_its_topic(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    async for client, engine, _notices in _client(tmp_path / "news.db"):
        url = await _send_post(client)
        response = await client.post(
            _PATH_TOPICS,
            headers=_headers(),
            json={
                "topics": [
                    _topic("Agentes em paralelo", url, [_quote(url)]),
                    _topic(
                        "Revisão de agentes",
                        url,
                        [_quote(url, excerpt="hundreds of agents in parallel")],
                    ),
                ]
            },
        )
        stored = await _stored_quotes(engine)
    assert response.status_code == 200
    body = response.json()
    assert len(body["accepted"]) == 1
    assert len(body["queued"]) == 1
    assert body["rejected"] == [
        {
            "index": 1,
            "title": "Revisão de agentes",
            "reason": "quote_not_in_post",
            "field": "quotes[0].excerpt",
        }
    ]
    assert stored == [[_quote(url)]]


# Scenario: An unknown key inside a quote is still a 422
@pytest.mark.asyncio
async def test_unknown_quote_key_is_a_422(configured_key: None, tmp_path: Path) -> None:
    del configured_key
    async for client, engine, _notices in _client(tmp_path / "news422.db"):
        url = await _send_post(client)
        bad = {**_quote(url), "avatar_asset_id": "a1"}
        response = await client.post(
            _PATH_TOPICS,
            headers=_headers(),
            json={"topics": [_topic("Agentes", url, [bad])]},
        )
        stored = await _stored_quotes(engine)
    assert response.status_code == 422
    assert stored == []


# Scenario Outline: A quote problem rejects only that topic (unserved source)
@pytest.mark.asyncio
async def test_an_unserved_quote_source_is_rejected_first(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    async for client, _engine, _notices in _client(tmp_path / "newsnox.db"):
        url = await _send_post(client)
        other = _status_url("someone", timedelta(hours=1))
        topic = _topic("Agentes", url, [_quote(other, handle="someone")])
        topic["sources"] = [url, other]
        response = await client.post(
            _PATH_TOPICS, headers=_headers(), json={"topics": [topic]}
        )
    rejected = response.json()["rejected"]
    # ``other`` was never served, so the topic's sources fail first.
    assert [(r["reason"], r["field"]) for r in rejected] == [
        ("source_not_in_signals", "sources[1]")
    ]
