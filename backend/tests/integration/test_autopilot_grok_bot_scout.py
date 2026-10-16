"""POST /api/autopilot/x-signals and /scout-failed (AE-0360).

Gherkin: tests/features/autopilot_grok_bot_scout.feature
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import pytest

from rag_backend.modules.autopilot.constants import (
    DETAIL_API_KEY_INVALID,
    DETAIL_SCOUT_NOTIFY_UNCONFIGURED,
    DETAIL_SCOUT_REASON_EMPTY,
    HEADER_API_KEY,
    REASON_NOT_STATUS_URL,
    REASON_SOURCE_NOT_IN_SIGNALS,
    REASON_STALE_STATUS,
    SOURCE_X_BROWSER,
    X_POST_TEXT_MAX_CHARS,
    X_SIGNAL_BATCH_MAX,
)
from tests.integration.autopilot_scout_support import (
    _CHAT,
    _INJECTION,
    _PATH_FAILED,
    _PATH_TOPICS,
    _PATH_X,
    _body,
    _client,
    _run_count,
    _signal_rows,
    _status_url,
    owner_chat,
)
from tests.integration.autopilot_topic_support import _headers, _topic, configured_key

_ = (owner_chat, configured_key)

_FOREIGN = "https://example.com/not-in-the-bundle"
_VALID_FAIL = {"reason": "x.com login expired"}


def _posts(*items: tuple[str, str, str]) -> dict[str, object]:
    return {"posts": [_body(url, handle, text) for url, handle, text in items]}


_VALID_X = _posts((_status_url("openai", timedelta(hours=1)), "openai", "note"))


# Scenario: Observed X posts become allowed sources
# Scenario: Unknown URL is still rejected
@pytest.mark.asyncio
async def test_accepted_x_urls_join_the_topic_allowlist(
    owner_chat: None, tmp_path: Path
) -> None:
    del owner_chat
    first = _status_url("openai", timedelta(hours=1))
    second = _status_url("anthropic", timedelta(hours=2))
    third = _status_url("google", timedelta(hours=3))
    payload = _posts(
        (first, "openai", "one"),
        (second, "anthropic", "two"),
        (third, "google", "three"),
    )
    async for client, engine, _notices in _client(tmp_path / "allow.db"):
        stored = await client.post(_PATH_X, headers=_headers(), json=payload)
        cited = await client.post(
            _PATH_TOPICS,
            headers=_headers(),
            json={"topics": [_topic("Agents", first, 90)]},
        )
        foreign = await client.post(
            _PATH_TOPICS,
            headers=_headers(),
            json={"topics": [_topic("Foreign", _FOREIGN, 80)]},
        )
    assert stored.status_code == 200
    assert stored.json()["accepted"] == [first, second, third]
    assert stored.json()["rejected"] == []
    rows = await _signal_rows(engine)
    assert len(rows) == 3
    assert {row[3] for row in rows} == {SOURCE_X_BROWSER}
    assert cited.status_code == 200
    assert cited.json()["rejected"] == []
    assert len(cited.json()["accepted"]) == 1
    # AE-0406: additive ``index`` and ``field`` on every rejection.
    assert foreign.json()["rejected"] == [
        {
            "index": 0,
            "title": "Foreign",
            "reason": REASON_SOURCE_NOT_IN_SIGNALS,
            "field": "sources[0]",
        }
    ]


# Scenario: Stale or malformed X items are rejected individually
@pytest.mark.asyncio
async def test_stale_and_profile_urls_are_rejected_individually(
    owner_chat: None, tmp_path: Path
) -> None:
    del owner_chat
    recent = _status_url("openai", timedelta(hours=1))
    stale = _status_url("openai", timedelta(days=3))
    profile = "https://x.com/openai"
    async for client, engine, _notices in _client(tmp_path / "mixed.db"):
        response = await client.post(
            _PATH_X,
            headers=_headers(),
            json=_posts(
                (profile, "openai", "profile"),
                (stale, "openai", "old"),
                (recent, "openai", "fresh"),
            ),
        )
    body = response.json()
    assert body["accepted"] == [recent]
    assert body["rejected"] == [
        {"url": profile, "reason": REASON_NOT_STATUS_URL},
        {"url": stale, "reason": REASON_STALE_STATUS},
    ]
    rows = await _signal_rows(engine)
    assert len(rows) == 1
    assert rows[0][0] == recent
    assert rows[0][3] == SOURCE_X_BROWSER


@pytest.mark.asyncio
async def test_twitter_url_is_stored_as_x_com(owner_chat: None, tmp_path: Path) -> None:
    """A twitter.com status is canonicalised before storage and allowlisting."""
    del owner_chat
    status_id = _status_url("openai", timedelta(hours=1)).rsplit("/", 1)[-1]
    submitted = f"https://twitter.com/openai/status/{status_id}"
    canonical = f"https://x.com/openai/status/{status_id}"
    async for client, engine, _notices in _client(tmp_path / "twitter.db"):
        response = await client.post(
            _PATH_X,
            headers=_headers(),
            json=_posts((submitted, "openai", "from twitter")),
        )
    assert response.json()["accepted"] == [canonical]
    rows = await _signal_rows(engine)
    assert rows == [(canonical, "openai", "from twitter", SOURCE_X_BROWSER)]


@pytest.mark.asyncio
async def test_repeat_post_updates_the_same_row(
    owner_chat: None, tmp_path: Path
) -> None:
    """A second observation of the same status does not insert another row."""
    del owner_chat
    url = _status_url("openai", timedelta(hours=1))
    async for client, engine, _notices in _client(tmp_path / "replay.db"):
        await client.post(
            _PATH_X, headers=_headers(), json=_posts((url, "openai", "first"))
        )
        second = await client.post(
            _PATH_X, headers=_headers(), json=_posts((url, "openai", "second"))
        )
    assert second.json()["accepted"] == [url]
    rows = await _signal_rows(engine)
    assert rows == [(url, "openai", "second", SOURCE_X_BROWSER)]


# Scenario: Instructions in post text stay inert
@pytest.mark.asyncio
async def test_prompt_injection_is_stored_as_text(
    owner_chat: None, tmp_path: Path
) -> None:
    del owner_chat
    url = _status_url("openai", timedelta(hours=1))
    async for client, engine, _notices in _client(tmp_path / "inject.db"):
        response = await client.post(
            _PATH_X,
            headers=_headers(),
            json=_posts((url, "openai", _INJECTION)),
        )
    assert response.status_code == 200
    rows = await _signal_rows(engine)
    assert rows == [(url, "openai", _INJECTION, SOURCE_X_BROWSER)]
    assert await _run_count(engine) == 0


# Scenario: Unauthenticated call
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "payload", "header"),
    [
        (_PATH_X, _VALID_X, None),
        (_PATH_FAILED, _VALID_FAIL, None),
        (_PATH_X, _VALID_X, "wrong-key"),
        (_PATH_FAILED, _VALID_FAIL, "wrong-key"),
    ],
)
async def test_missing_or_wrong_key_is_401(
    owner_chat: None,
    tmp_path: Path,
    path: str,
    payload: dict[str, object],
    header: str | None,
) -> None:
    del owner_chat
    headers = {} if header is None else {HEADER_API_KEY: header}
    async for client, engine, _notices in _client(tmp_path / "auth.db"):
        response = await client.post(path, headers=headers, json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == DETAIL_API_KEY_INVALID
    assert await _signal_rows(engine) == []


# Scenario: Scout reports a failure
@pytest.mark.asyncio
async def test_scout_failed_sends_one_telegram_message(
    owner_chat: None, tmp_path: Path
) -> None:
    del owner_chat
    reason = "x.com login expired"
    async for client, _engine, notices in _client(tmp_path / "fail.db"):
        response = await client.post(
            _PATH_FAILED, headers=_headers(), json={"reason": reason}
        )
    assert response.status_code == 200
    assert response.json() == {"delivered": True}
    assert len(notices.notices) == 1
    assert reason in notices.notices[0].text
    assert notices.notices[0].chat_id == _CHAT


@pytest.mark.asyncio
async def test_scout_failed_without_chat_is_unavailable(
    configured_key: None, tmp_path: Path
) -> None:
    """An empty owner chat does not pretend the message was sent."""
    del configured_key
    from rag_backend.infrastructure.config.settings import get_settings

    previous = os.environ.get("TELEGRAM_OWNER_CHAT_ID")
    os.environ["TELEGRAM_OWNER_CHAT_ID"] = ""
    get_settings.cache_clear()
    try:
        async for client, _engine, notices in _client(tmp_path / "noch.db"):
            response = await client.post(
                _PATH_FAILED,
                headers=_headers(),
                json={"reason": "x.com login expired"},
            )
    finally:
        if previous is None:
            os.environ.pop("TELEGRAM_OWNER_CHAT_ID", None)
        else:
            os.environ["TELEGRAM_OWNER_CHAT_ID"] = previous
        get_settings.cache_clear()
    assert response.status_code == 503
    assert response.json()["detail"] == DETAIL_SCOUT_NOTIFY_UNCONFIGURED
    assert notices.notices == []


@pytest.mark.asyncio
async def test_control_only_reason_is_422(owner_chat: None, tmp_path: Path) -> None:
    del owner_chat
    async for client, _engine, notices in _client(tmp_path / "blank.db"):
        response = await client.post(
            _PATH_FAILED, headers=_headers(), json={"reason": "\x00"}
        )
    assert response.status_code == 422
    assert response.json()["detail"] == DETAIL_SCOUT_REASON_EMPTY
    assert notices.notices == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"posts": []},
        {"posts": [_body("https://x.com/a/status/1", "a")] * (X_SIGNAL_BATCH_MAX + 1)},
        {"extra": True, "posts": [_body("https://x.com/a/status/1", "a")]},
        {"posts": [{**_body("https://x.com/a/status/1", "a"), "likes": -1}]},
        {
            "posts": [
                _body(
                    "https://x.com/a/status/1", "a", "x" * (X_POST_TEXT_MAX_CHARS + 1)
                )
            ]
        },
        {"reason": "x" * 501},
    ],
)
async def test_schema_violation_persists_nothing(
    owner_chat: None, tmp_path: Path, payload: dict[str, object]
) -> None:
    del owner_chat
    path = _PATH_FAILED if "reason" in payload and "posts" not in payload else _PATH_X
    async for client, engine, _notices in _client(tmp_path / "schema.db"):
        response = await client.post(path, headers=_headers(), json=payload)
    assert response.status_code == 422
    assert await _signal_rows(engine) == []


@pytest.mark.asyncio
async def test_x_signals_share_the_autopilot_rate_limit(
    owner_chat: None, tmp_path: Path
) -> None:
    """The route uses the shared 10/minute autopilot budget."""
    del owner_chat
    url = _status_url("openai", timedelta(hours=1))
    payload = _posts((url, "openai", "note"))
    statuses: list[int] = []
    async for client, _engine, _notices in _client(tmp_path / "limit.db"):
        for _ in range(11):
            response = await client.post(_PATH_X, headers=_headers(), json=payload)
            statuses.append(response.status_code)
    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429
