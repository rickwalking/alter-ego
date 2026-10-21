"""PR #136 review fixes over the API: the claim race and the upload limit.

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
  Scenario: A cover another batch claimed after the read rejects the topic
  Scenario: A cover the sweep deleted after the read rejects the topic
  Scenario: Cover uploads have their own rate limit
"""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from rag_backend.modules.autopilot.domain.cover import CoverAsset
from rag_backend.modules.autopilot.infrastructure.cover_models import (
    AutopilotCoverAssetModel,
)
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore
from rag_backend.modules.autopilot.infrastructure.models import TopicCandidateModel
from tests.integration.autopilot_topic_support import (
    _URL_A,
    _URL_B,
    _Clock,
    _topic,
    configured_key,
)
from tests.integration.test_autopilot_cover_api_ae0418 import (
    _ai_cover,
    _post,
    _upload,
    _with_cover,
    api,
    cover_env,
)

_ = (api, configured_key, cover_env)
_Api = tuple[AsyncClient, AsyncEngine, _Clock]
_ORIGINAL_READ = SqlCoverAssetStore.covers_by_ids
_ASSETS_BUDGET = 30
_SHARED_BUDGET = 10


async def _topics(engine: AsyncEngine) -> int:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        count = await session.scalar(select(func.count(TopicCandidateModel.id)))
    return int(count or 0)


def _stale_read(monkeypatch: pytest.MonkeyPatch, *, sweep: bool) -> None:
    """The first read sees the cover free; the claim then meets the real row."""
    reads: list[int] = []

    async def _read(
        self: SqlCoverAssetStore, ids: tuple[UUID, ...]
    ) -> dict[UUID, CoverAsset]:
        """Models the sweep deleting the row between the facts read and the claim."""
        found = await _ORIGINAL_READ(self, ids)
        reads.append(len(ids))
        if len(reads) > 1:
            return found
        if sweep:
            await self._session.execute(
                delete(AutopilotCoverAssetModel).where(
                    AutopilotCoverAssetModel.id.in_(ids)
                )
            )
        return {key: replace(c, topic_candidate_id=None) for key, c in found.items()}

    monkeypatch.setattr(SqlCoverAssetStore, "covers_by_ids", _read)


# Scenario: A cover another batch claimed after the read rejects the topic
@pytest.mark.asyncio
async def test_lost_claim_rejects_the_topic_as_used(
    api: _Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rejected topic is not stored: only the first topic and "Robots plan" are."""
    client, engine, _clock = api
    asset_id = await _ai_cover(client)
    first = await _post(
        client, [_with_cover(_topic("Agents ship", _URL_A, 80), asset_id)]
    )
    assert len(first["accepted"]) == 1
    _stale_read(monkeypatch, sweep=False)
    body = await _post(
        client,
        [
            _with_cover(_topic("Models merge", _URL_B, 70), asset_id),
            _topic("Robots plan", _URL_B, 60),
        ],
    )
    assert len(body["accepted"]) == 1
    lost = [r for r in body["rejected"] if r.get("field")]
    assert [(r["index"], r["reason"], r["field"]) for r in lost] == [
        (0, "cover_asset_used", "cover.asset_id")
    ]
    assert await _topics(engine) == 2


# Scenario: A cover the sweep deleted after the read rejects the topic
@pytest.mark.asyncio
async def test_swept_cover_rejects_the_topic_as_unknown(
    api: _Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, engine, _clock = api
    asset_id = await _ai_cover(client)
    _stale_read(monkeypatch, sweep=True)
    body = await _post(
        client, [_with_cover(_topic("Agents ship", _URL_A, 80), asset_id)]
    )
    assert body["accepted"] == []
    assert [r["reason"] for r in body["rejected"]] == ["cover_asset_unknown"]
    assert await _topics(engine) == 0


# Scenario: Cover uploads have their own rate limit
@pytest.mark.asyncio
async def test_uploads_do_not_spend_the_shared_budget(api: _Api) -> None:
    """The other routes keep their whole 10/minute budget."""
    client, _engine, _clock = api
    statuses = [
        (await _upload(client, b"", {"kind": "ai_image"}))["status"]
        for _ in range(_ASSETS_BUDGET)
    ]
    assert 429 not in statuses
    blocked = await _upload(client, b"", {"kind": "ai_image"})
    assert blocked["status"] == 429
    topics = [
        (await _post(client, [_topic(f"Topic {n}", _URL_A, 50)]))["status"]
        for n in range(_SHARED_BUDGET)
    ]
    assert topics == [200] * _SHARED_BUDGET
