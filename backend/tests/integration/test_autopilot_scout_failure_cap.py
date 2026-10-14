"""POST /api/autopilot/scout-failed: URL stripping and the daily cap (QA r1 S-W3).

Gherkin: tests/features/autopilot_grok_bot_scout.feature
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_backend.modules.autopilot.constants import DETAIL_SCOUT_REASON_EMPTY
from tests.integration.autopilot_scout_support import (
    _PATH_FAILED,
    _client,
    owner_chat,
)
from tests.integration.autopilot_topic_support import _headers, configured_key

__all__ = ["configured_key", "owner_chat"]


# Scenario: Scout failure reason carries a URL
@pytest.mark.asyncio
async def test_scout_failed_strips_urls(owner_chat: None, tmp_path: Path) -> None:
    del owner_chat
    reason = "login expired https://evil.example/phish"
    async for client, _engine, notices in _client(tmp_path / "url.db"):
        response = await client.post(
            _PATH_FAILED, headers=_headers(), json={"reason": reason}
        )
        url_only = await client.post(
            _PATH_FAILED,
            headers=_headers(),
            json={"reason": "www.evil.example"},
        )
    assert response.status_code == 200
    assert response.json() == {"delivered": True}
    assert "evil" not in notices.notices[0].text
    assert "login expired" in notices.notices[0].text
    assert url_only.status_code == 422
    assert url_only.json()["detail"] == DETAIL_SCOUT_REASON_EMPTY
    assert len(notices.notices) == 1


# Scenario: A fourth scout failure in one day is not sent
# Scenario: A repeated scout failure is not sent twice
@pytest.mark.asyncio
async def test_scout_failed_caps_and_dedupes(owner_chat: None, tmp_path: Path) -> None:
    del owner_chat
    reasons = ["first", "first", "second", "third", "fourth"]
    bodies: list[object] = []
    async for client, _engine, notices in _client(tmp_path / "cap.db"):
        for reason in reasons:
            response = await client.post(
                _PATH_FAILED, headers=_headers(), json={"reason": reason}
            )
            assert response.status_code == 200
            bodies.append(response.json()["delivered"])
    assert bodies == [True, False, True, True, False]
    assert [notice.text.split(": ", 1)[1] for notice in notices.notices] == [
        "first",
        "second",
        "third",
    ]
