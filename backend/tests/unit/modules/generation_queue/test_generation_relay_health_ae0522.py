"""Progress relay payloads, queue health, the monitor and the alert policy."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable
from dataclasses import replace
from datetime import timedelta

import pytest

from rag_backend.application.services.carousel.carousel_run_stage import (
    clear_run_stage,
    get_run_stage,
)
from rag_backend.application.services.carousel.workflow_sse_hub import (
    get_workflow_sse_hub,
    install_workflow_sse_hub,
    reset_workflow_sse_hub,
)
from rag_backend.modules.generation_queue.application.monitor import (
    MonitorDependencies,
    monitor_once,
)
from rag_backend.modules.generation_queue.constants import MAX_NOTIFY_BYTES
from rag_backend.modules.generation_queue.domain.health import (
    QueueAlertPolicy,
    QueueMetrics,
)
from rag_backend.modules.generation_queue.infrastructure.progress_relay import (
    FIELD_REFETCH,
    RelayingWorkflowSseHub,
    decode,
    deliver,
    encode,
)
from tests.unit.modules.generation_queue.queue_fakes import NOW, FixedClock


@pytest.fixture(autouse=True)
def _fresh_hub() -> None:
    reset_workflow_sse_hub()
    yield
    reset_workflow_sse_hub()


async def _no_refetch(_project_id: str) -> dict[str, object] | None:
    return None


def test_small_events_travel_whole() -> None:
    """Scenario: Progress events reach the web through NOTIFY"""
    event = {"event": "phase_change", "phase": "outline", "phase_status": "in_progress"}
    payload = encode("p1", event)
    assert payload is not None
    assert decode(payload) == ("p1", event)


def test_oversized_review_travels_without_its_gate() -> None:
    """Scenario: An oversized review event is rebuilt from the checkpoint"""
    event = {"event": "review_required", "gate_payload": {"x": "y" * MAX_NOTIFY_BYTES}}
    payload = encode("p1", event)
    assert payload is not None
    assert len(payload.encode()) <= MAX_NOTIFY_BYTES
    _, slim = decode(payload)
    assert slim["gate_payload"] is None
    assert slim[FIELD_REFETCH] is True


def test_other_oversized_events_are_dropped() -> None:
    """Scenario: An oversized review event is rebuilt from the checkpoint"""
    event = {"event": "artifact", "data": "z" * MAX_NOTIFY_BYTES}
    assert encode("p1", event) is None


@pytest.mark.parametrize(
    "payload",
    ["not json", "[1]", json.dumps({"p": 1, "e": {}}), json.dumps({"p": "x"})],
)
def test_malformed_payloads_are_ignored(payload: str) -> None:
    """Scenario: Progress events reach the web through NOTIFY"""
    assert decode(payload) is None


async def _collect(project_id: str, action: Awaitable[None]) -> list[dict[str, object]]:
    hub = get_workflow_sse_hub()
    events: list[dict[str, object]] = []

    async def listen() -> None:
        async for event in hub.listen(project_id, keepalive_seconds=5):
            events.append(event)
            return

    listener = asyncio.create_task(listen())
    await asyncio.sleep(0)
    await action
    await asyncio.wait_for(listener, timeout=2)
    return events


async def test_deliver_mirrors_the_run_stage_and_publishes() -> None:
    """Scenario: Progress events reach the web through NOTIFY"""
    event = {"event": "run.stage_changed", "run_stage": "validating"}
    events = await _collect("p1", deliver("p1", event, _no_refetch))
    assert events == [event]
    assert get_run_stage("p1") == "validating"
    await deliver("p1", {"event": "run.finished"}, _no_refetch)
    assert get_run_stage("p1") == "generating"
    clear_run_stage("p1")


async def test_deliver_rebuilds_a_slim_review_event() -> None:
    """Scenario: An oversized review event is rebuilt from the checkpoint"""
    rebuilt = {"event": "review_required", "gate_payload": {"slides": 7}}

    async def refetch(project_id: str) -> dict[str, object] | None:
        return rebuilt if project_id == "p1" else None

    slim = {"event": "review_required", "gate_payload": None, FIELD_REFETCH: True}
    assert await _collect("p1", deliver("p1", slim, refetch)) == [rebuilt]
    await deliver("p2", slim, refetch)


async def test_worker_hub_relays_and_survives_a_relay_failure() -> None:
    """Scenario: Progress events reach the web through NOTIFY"""
    sent: list[str] = []

    async def notifier(payload: str) -> None:
        sent.append(payload)

    async def broken(_payload: str) -> None:
        raise ConnectionError

    install_workflow_sse_hub(RelayingWorkflowSseHub(notifier))
    await get_workflow_sse_hub().publish("p1", {"event": "phase_change"})
    await get_workflow_sse_hub().publish(
        "p1", {"event": "artifact", "data": "z" * 9000}
    )
    assert [decode(item) for item in sent] == [("p1", {"event": "phase_change"})]
    install_workflow_sse_hub(RelayingWorkflowSseHub(broken))
    await get_workflow_sse_hub().publish("p1", {"event": "phase_change"})


_BASE = QueueMetrics(
    queued=2,
    running=1,
    retry_wait=0,
    dead_letters=1,
    oldest_queued_seconds=60,
    running_seconds=30,
    worker_connected=True,
)


def _metrics(**overrides: int | bool) -> QueueMetrics:
    return replace(_BASE, **overrides)


def test_health_check_reports_numbers() -> None:
    """Scenario: Queue health is reported and alerts fire once per episode"""
    assert _metrics().as_check() == {
        "status": "ok",
        "queued": 2,
        "running": 1,
        "retry_wait": 0,
        "dead_letters": 1,
        "oldest_queued_seconds": 60,
        "running_seconds": 30,
    }
    assert _metrics(worker_connected=False).as_check()["status"] == "worker_down"


def test_worker_missing_alerts_once_after_ten_minutes() -> None:
    """Scenario: Queue health is reported and alerts fire once per episode"""
    policy = QueueAlertPolicy()
    down = _metrics(worker_connected=False)
    assert policy.evaluate(down, NOW) == []
    assert policy.evaluate(down, NOW + timedelta(minutes=9)) == []
    alerts = policy.evaluate(down, NOW + timedelta(minutes=10))
    assert len(alerts) == 1
    assert "10 min" in alerts[0]
    assert policy.evaluate(down, NOW + timedelta(minutes=30)) == []
    assert policy.evaluate(_metrics(), NOW + timedelta(minutes=31)) == []
    assert policy.evaluate(down, NOW + timedelta(minutes=32)) == []
    assert len(policy.evaluate(down, NOW + timedelta(minutes=42))) == 1


def test_stalled_queue_alerts_once_per_episode() -> None:
    """Scenario: Queue health is reported and alerts fire once per episode"""
    policy = QueueAlertPolicy()
    stalled = _metrics(oldest_queued_seconds=6 * 3600 + 1, queued=3)
    alerts = policy.evaluate(stalled, NOW)
    assert alerts == ["Fila de geração: o tema mais antigo espera há 6 h (3 na fila)."]
    assert policy.evaluate(stalled, NOW) == []
    assert policy.evaluate(_metrics(), NOW) == []
    assert len(policy.evaluate(stalled, NOW)) == 1


async def test_monitor_sends_what_the_policy_returns() -> None:
    """Scenario: Queue health is reported and alerts fire once per episode"""
    sent: list[str] = []

    async def read() -> QueueMetrics:
        return _metrics(oldest_queued_seconds=7 * 3600)

    deps = MonitorDependencies(read=read, alert=sent.append, clock=FixedClock())
    policy = QueueAlertPolicy()
    assert await monitor_once(deps, policy) == 1
    assert await monitor_once(deps, policy) == 0
    assert len(sent) == 1
