"""Closing Telegram client for scout-failed."""

from __future__ import annotations

from uuid import UUID

import httpx
import pytest
import respx

from rag_backend.modules.autopilot.domain.exceptions import NotifierUnconfiguredError
from rag_backend.modules.autopilot.domain.notify import StatusNotice
from rag_backend.modules.autopilot.infrastructure.scout_status import (
    ClosingTelegramStatus,
)
from rag_backend.modules.autopilot.infrastructure.telegram_notifier import AsyncSleeper
from rag_backend.modules.autopilot.notify_constants import (
    TELEGRAM_API_HOST,
    TELEGRAM_METHOD_MESSAGE,
)

_TOKEN = "scout-status-token"
_NOTICE = StatusNotice(
    chat_id="4242",
    run_id=UUID(int=0),
    text="Scout failed: x.com login expired",
    keyboard=None,
)


@pytest.mark.asyncio
async def test_send_status_posts_once_and_returns_the_message_id() -> None:
    """One sendMessage, then the client is closed."""
    url = f"{TELEGRAM_API_HOST}/bot{_TOKEN}/{TELEGRAM_METHOD_MESSAGE}"
    sender = ClosingTelegramStatus(_TOKEN, AsyncSleeper())
    with respx.mock(assert_all_called=True) as router:
        route = router.post(url).mock(
            return_value=httpx.Response(
                200, json={"ok": True, "result": {"message_id": 7}}
            )
        )
        result = await sender.send_status(_NOTICE)
    assert result.message_id == 7
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_empty_token_does_not_call_telegram() -> None:
    """An empty bot token raises before any HTTP call."""
    sender = ClosingTelegramStatus("  ", AsyncSleeper())
    with respx.mock(assert_all_called=False) as router:
        router.post(url__regex=r".*").mock(return_value=httpx.Response(500))
        with pytest.raises(NotifierUnconfiguredError):
            await sender.send_status(_NOTICE)
