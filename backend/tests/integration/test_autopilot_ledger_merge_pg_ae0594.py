"""Two writers of a run's notice ledger at once, on Postgres.

Feature: tests/features/website_cover_review_switch_ae0594.feature. Both read
the run first, then save concurrently through the real ``SqlNoticeLogStore``;
the row lock and the merge keep both records. Skipped without a Postgres
``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import (
    NoticeLog,
    ReviewRecord,
    record_reminder,
    record_review,
)
from rag_backend.modules.autopilot.domain.notify import SaveNoticeLog
from rag_backend.modules.autopilot.infrastructure.notice_source import SqlNoticeLogStore
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.website_cover_review_pg_support import (
    Harness,
    harness,
    seed,
    seed_run,
    tables,
)


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    monkeypatch.setenv("CAROUSEL_OUTPUT_DIR", str(tmp_path / "out"))
    get_settings.cache_clear()
    yield assets
    get_settings.cache_clear()


async def _read(built: Harness, project_id: str) -> AutopilotRun:
    async with built.sessions()() as session:
        run = await SqlAlchemyAutopilotRepository(session).find_by_carousel(project_id)
    assert run is not None
    return run


async def _save(built: Harness, run: AutopilotRun, log: NoticeLog) -> None:
    async with built.sessions()() as session:
        await SqlNoticeLogStore(session).save(
            SaveNoticeLog(run_id=run.run_id, log=log, base=run.notice_log)
        )
        await asyncio.sleep(0.05)
        await session.commit()


@requires_postgres
@pytest.mark.asyncio
async def test_two_stale_writers_keep_both_records(
    dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A review keyboard and a reminder saved at once from the same read both survive."""
    # Scenario: Concurrent notice ledger writes never erase a recorded review
    async with isolated_schema(tables()) as engine:
        built = harness(engine, monkeypatch)
        project_id, _ = await seed(built, dirs)
        await seed_run(built, project_id, AutopilotRunState.AWAITING_OWNER)
        first, second = await _read(built, project_id), await _read(built, project_id)
        review = ReviewRecord(revision=4, album_ids=(1,), keyboard_id=9)

        await asyncio.gather(
            _save(built, first, record_review(first.notice_log, review)),
            _save(built, second, record_reminder(second.notice_log, 4, 30)),
        )

        after = (await _read(built, project_id)).notice_log
        assert after.reviews == (review,)
        assert [r.message_id for r in after.reminder_messages] == [30]
        assert set(after.message_ids) == {1, 9, 30}
