"""The scout's override of the weekly repost cap.

Gherkin: tests/features/autopilot_repost_cap_override_ae0640.feature
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest
from structlog.testing import capture_logs

from rag_backend.modules.autopilot.api.repost_mapping import draft_from
from rag_backend.modules.autopilot.api.repost_schemas import RepostCreate
from rag_backend.modules.autopilot.application.repost_drafts import (
    RepostDeps,
    RepostDraftService,
)
from rag_backend.modules.autopilot.domain.repost import RepostError, request_hash
from rag_backend.modules.autopilot.repost_constants import (
    ERR_TOO_RECENT,
    ERR_WEEKLY_CAP,
    LOG_CREATED,
    STATUS_PENDING,
)
from tests.unit.modules.autopilot.repost_fakes import (
    MEDIA,
    NOW,
    Clock,
    FakeCovers,
    FakeProbe,
    FakeReels,
    MemoryStore,
    draft,
    reel,
    stored,
)

_PLAIN_HASH = "ee3f8df0aa3b4bb54b96c8d5fe95d41ec96cbdd9a74e98c9f25432dc1b5a8939"


def _full_week(days_old: int = 120) -> tuple[RepostDraftService, MemoryStore]:
    store = MemoryStore()
    for media in ("111", "222"):
        row = stored(media_id=media, created_at=NOW - timedelta(days=2))
        store.rows[row.id] = row
    service = RepostDraftService(
        RepostDeps(
            store=store,
            covers=FakeCovers(),
            facts=store,
            reels=FakeReels(items={MEDIA: reel(days_old=days_old)}),
            probe=FakeProbe(),
            clock=Clock(),
        )
    )
    return service, store


# Scenario: Without the override the cap still refuses a third draft
async def test_cap_refuses_without_the_override() -> None:
    service, _store = _full_week()
    with pytest.raises(RepostError) as error:
        await service.create(draft())
    assert error.value.problem.code == ERR_WEEKLY_CAP


# Scenario: The override skips the weekly cap
async def test_override_creates_a_pending_draft_over_the_cap() -> None:
    service, store = _full_week()
    with capture_logs() as logs:
        created = await service.create(draft(override_weekly_cap=True))
    assert created.status == STATUS_PENDING
    assert created.id in store.rows
    assert len(store.rows) == 3
    line = next(log for log in logs if log.get("outcome") == LOG_CREATED)
    assert line["cap_override"] is True


# Scenario: The override skips the weekly cap
async def test_a_plain_draft_logs_no_override() -> None:
    service, store = _full_week()
    store.rows.clear()
    with capture_logs() as logs:
        await service.create(draft())
    line = next(log for log in logs if log.get("outcome") == LOG_CREATED)
    assert line["cap_override"] is False


# Scenario: The override skips only the cap
async def test_override_keeps_the_other_rules() -> None:
    service, _store = _full_week(days_old=10)
    with pytest.raises(RepostError) as error:
        await service.create(draft(override_weekly_cap=True))
    assert error.value.problem.code == ERR_TOO_RECENT


# Scenario: Drafts without the override keep their request hash
def test_hash_of_a_plain_draft_ignores_the_flag_field() -> None:
    plain = draft()
    overridden = replace(plain, override_weekly_cap=True)
    assert request_hash(plain) == _PLAIN_HASH
    assert request_hash(overridden) != _PLAIN_HASH


# Scenario: Drafts without the override keep their request hash
async def test_replay_of_a_stored_plain_draft_returns_it() -> None:
    service, store = _full_week()
    store.rows.clear()
    first = await service.create(draft())
    again = await service.create(draft())
    assert again.id == first.id


# Scenario: The request body accepts the override flag
def test_body_maps_the_override_and_defaults_to_false() -> None:
    body = {"media_id": MEDIA, "caption": "Nova legenda", "reason": "Views 3x a mediana"}
    plain = RepostCreate.model_validate(body)
    flagged = RepostCreate.model_validate({**body, "override_weekly_cap": True})
    assert draft_from(plain, "scout-key-0001").override_weekly_cap is False
    assert draft_from(flagged, "scout-key-0001").override_weekly_cap is True
