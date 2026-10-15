"""Scout v3 picks the POV format and slide count per topic (PR #106 review, item 6).

Gherkin: tests/features/autopilot_pov_thesis.feature ("Scout POV format")
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from rag_backend.modules.autopilot.infrastructure.models import TopicCandidateModel
from tests.integration.autopilot_topic_support import (
    _AS_OF,
    _PATH,
    _URL_A,
    _client,
    _Clock,
    _headers,
    _serve,
    _topic,
    _topic_count,
    configured_key,
)

_ = configured_key
_POV = {"mode": "pov", "thesis_draft": "Quem decide o que construir ainda é o dev."}


async def _choices(engine: AsyncEngine) -> list[tuple[str | None, int | None]]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        rows = await session.execute(
            select(TopicCandidateModel.pov_format, TopicCandidateModel.slide_count)
        )
    return [(row[0], row[1]) for row in rows.all()]


async def _post(tmp: Path, topic: dict[str, object]) -> tuple[int, AsyncEngine]:
    async for client, engine in _client(tmp, _Clock(_AS_OF)):
        await _serve(engine, (_URL_A,), _AS_OF)
        response = await client.post(
            _PATH, headers=_headers(), json={"topics": [topic]}
        )
    return response.status_code, engine


# Scenario: The scout chooses the format and the slide count of a POV topic
@pytest.mark.asyncio
async def test_pov_choice_is_stored(configured_key: None, tmp_path: Path) -> None:
    del configured_key
    topic = {
        **_topic("Erros", _URL_A, 80),
        **_POV,
        "pov_format": "erros_e_mitos",
        "slide_count": 8,
    }
    status, engine = await _post(tmp_path / "choice.db", topic)
    assert status == 200
    assert await _choices(engine) == [("erros_e_mitos", 8)]


# Scenario: A POV topic without a choice stores none (the run applies defaults)
@pytest.mark.asyncio
async def test_pov_without_choice_stores_none(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    status, engine = await _post(
        tmp_path / "nochoice.db", {**_topic("Tese", _URL_A, 80), **_POV}
    )
    assert status == 200
    assert await _choices(engine) == [(None, None)]


# Scenario: A Radar IA topic ignores a POV choice
@pytest.mark.asyncio
async def test_radar_ia_ignores_the_choice(
    configured_key: None, tmp_path: Path
) -> None:
    del configured_key
    topic = {**_topic("Radar", _URL_A, 80), "pov_format": "opiniao", "slide_count": 9}
    status, engine = await _post(tmp_path / "radar.db", topic)
    assert status == 200
    assert await _choices(engine) == [(None, None)]


# Scenario Outline: An invalid POV choice rejects the batch
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "choice",
    [
        {"pov_format": "listicle"},
        {"slide_count": 7},
        {"slide_count": 11},
    ],
    ids=["unknown-format", "7-slides", "11-slides"],
)
async def test_invalid_choice_is_422(
    configured_key: None, tmp_path: Path, choice: dict[str, object]
) -> None:
    del configured_key
    topic = {**_topic("Tese", _URL_A, 80), **_POV, **choice}
    status, engine = await _post(tmp_path / "bad.db", topic)
    assert status == 422
    assert await _topic_count(engine) == 0
