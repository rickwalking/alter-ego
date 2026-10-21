"""Pure transitions of ``ai_generation_metadata.generation``.

Feature: backend/tests/features/blog_generate_ae0425.feature
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from rag_backend.domain.constants.blog_generation import ERR_GENERATION_INTERRUPTED
from rag_backend.domain.models.blog_generation import GenerationOutcome
from rag_backend.domain.models.blog_generation_state import (
    GenerationStart,
    finished,
    generation_of,
    heartbeat,
    is_stale,
    lease_of,
    reaped,
    started,
    status_of,
    with_voice_score,
)

NOW = "2026-10-18T12:00:00+00:00"


def _start(lease: str = "lease-a") -> GenerationStart:
    return GenerationStart(
        kind="from_carousel",
        lease_id=lease,
        now=NOW,
        request={"project_id": "p"},
        warnings=("carousel_private",),
    )


def test_started_keeps_other_metadata_and_counts_attempts() -> None:
    # Scenario: The 202 run is a tracked in-process task with a lease and heartbeat
    first = started({"ai_disclosure_label": "ai"}, _start())
    generation = generation_of(first)
    assert first["ai_disclosure_label"] == "ai"
    assert generation["status"] == "in_progress"
    assert generation["attempt"] == 1
    assert generation["heartbeat_at"] == NOW
    assert generation["warnings"] == ["carousel_private"]
    assert lease_of(first) == "lease-a"
    # Scenario: The owner can retry an interrupted generation on the same row
    second = started(reaped(first, NOW), _start("lease-b"))
    assert generation_of(second)["attempt"] == 2
    assert generation_of(second)["errors"] == []
    assert lease_of(second) == "lease-b"


def test_heartbeat_finish_and_voice_score() -> None:
    beat = heartbeat(started({}, _start()), "later")
    assert generation_of(beat)["heartbeat_at"] == "later"
    done = finished(
        beat,
        GenerationOutcome(
            status="partial",
            errors=({"slot": "sec_1", "code": "image_failed"},),
            recoverable=True,
            image_count=3,
        ),
        "end",
    )
    generation = generation_of(done)
    assert status_of(done) == "partial"
    assert generation["errors"] == [
        {"slot": "sec_1", "code": "image_failed", "at": "end"}
    ]
    assert generation["image_count"] == 3
    assert lease_of(done) == "lease-a"
    assert with_voice_score(done, 81.5)["voice_score"] == 81.5
    assert "voice_score" not in with_voice_score({}, None)


def test_reaped_is_failed_recoverable_and_revokes_the_lease() -> None:
    # Scenario: A restart mid-generation is reaped to failed/recoverable
    gone = reaped(started({}, _start()), NOW)
    generation = generation_of(gone)
    assert generation["status"] == "failed"
    assert generation["recoverable"] is True
    errors = generation["errors"]
    assert isinstance(errors, list)
    assert errors[0]["code"] == ERR_GENERATION_INTERRUPTED
    assert lease_of(gone) is None


def test_staleness() -> None:
    now = datetime(2026, 10, 18, 12, tzinfo=UTC)
    fresh = started({}, _start())
    assert not is_stale(fresh, now - timedelta(minutes=1))
    assert is_stale(fresh, now + timedelta(minutes=1))
    naive = heartbeat(fresh, "2026-10-18T11:00:00")
    assert is_stale(naive, now)
    broken = heartbeat(fresh, "yesterday")
    assert is_stale(broken, now)
    assert not is_stale(reaped(fresh, NOW), now + timedelta(days=1))


def test_garbage_metadata_reads_as_empty() -> None:
    assert generation_of(None) == {}
    assert generation_of({"generation": "x"}) == {}
    assert lease_of({"generation": {"lease_id": ""}}) is None
    assert status_of({"generation": {"status": 3}}) is None
    assert generation_of(started("x", _start()))["attempt"] == 1
