"""X-signals service persistence decisions (AE-0360)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from rag_backend.modules.autopilot.application.x_signals import (
    XSignalsCommand,
    XSignalsDependencies,
    XSignalsService,
)
from rag_backend.modules.autopilot.domain.scout_ports import SaveXSignals
from rag_backend.modules.autopilot.domain.x_observation import ObservedPostInput
from tests.unit.autopilot.support import snowflake_id

_AS_OF = datetime(2026, 10, 14, 11, 0, tzinfo=UTC)


class _Clock:
    def now(self) -> datetime:
        return _AS_OF


class _Store:
    def __init__(self) -> None:
        self.saved: list[SaveXSignals] = []
        self.commits = 0

    async def save(self, command: SaveXSignals) -> None:
        self.saved.append(command)

    async def commit(self) -> None:
        self.commits += 1


def _post(url: str) -> ObservedPostInput:
    return ObservedPostInput(
        url=url,
        handle="openai",
        text="note",
        likes=None,
        reposts=None,
        replies=None,
        views=None,
        observed_at=_AS_OF,
    )


@pytest.mark.asyncio
async def test_rejections_only_do_not_commit() -> None:
    """A batch with no recent status writes nothing."""
    store = _Store()
    service = XSignalsService(XSignalsDependencies(store=store, clock=_Clock()))
    result = await service.accept(
        XSignalsCommand(posts=(_post("https://x.com/openai"),))
    )
    assert result.accepted == ()
    assert store.saved == []
    assert store.commits == 0


@pytest.mark.asyncio
async def test_accepted_posts_are_saved_once() -> None:
    """Accepted rows are saved and committed with the intake clock."""
    moment = _AS_OF - timedelta(hours=1)
    url = f"https://x.com/openai/status/{snowflake_id(moment)}"
    store = _Store()
    service = XSignalsService(XSignalsDependencies(store=store, clock=_Clock()))
    result = await service.accept(XSignalsCommand(posts=(_post(url),)))
    assert result.accepted == (url,)
    assert store.commits == 1
    assert store.saved[0].stored_at == _AS_OF
    assert store.saved[0].rows[0].text == "note"
