"""Instagram publish refuses an empty caption on every path.

Feature: backend/tests/features/approve_keeps_caption_ae0546.feature
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_CAPTION_EMPTY,
)
from rag_backend.modules.autopilot.application.manual_publish import (
    ManualPublishCommand,
)
from rag_backend.modules.autopilot.application.publish_steps import gate_for
from rag_backend.modules.autopilot.domain.exceptions import ManualPublishRefusedError
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.publish import CarouselMedia, gate_reason
from tests.unit.modules.autopilot.test_instagram_publish_job import (
    _PROJECT,
    _SEVEN,
    _Clock,
    _Gateway,
    _job,
    _manual,
    _Notifier,
    _Repo,
    _run,
    _snapshot,
    _Source,
    _store,
)


@pytest.mark.parametrize("caption", ["", "   ", "\n\t"])
async def test_the_worker_fails_a_run_with_an_empty_caption(caption: str) -> None:
    """Scenario: The autopilot worker never posts an empty caption"""
    repo, gateway, notifier = _Repo(), _Gateway(), _Notifier()
    run = _store(repo, _run())
    source = _Source(replace(_snapshot(), caption=caption))
    job = _job(repo, gateway, source, _Clock(), notifier)

    await job.tick()

    stored = repo.runs[run.run_id]
    assert stored.state is AutopilotRunState.PUBLISH_FAILED
    assert stored.state_reason == ERR_INSTAGRAM_CAPTION_EMPTY
    assert gateway.opens == 0
    assert gateway.atomics == 0
    assert [n.error_code for n in notifier.notices] == [ERR_INSTAGRAM_CAPTION_EMPTY]
    assert notifier.notices[0].offer_retry is True


async def test_a_caption_is_posted_when_present() -> None:
    """Scenario: The autopilot worker never posts an empty caption"""
    repo, gateway = _Repo(), _Gateway()
    run = _store(repo, _run())
    await _job(repo, gateway, _Source(_snapshot()), _Clock(), _Notifier()).tick()
    assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHED


@pytest.mark.parametrize("caption", ["", "  "])
async def test_the_manual_publish_refuses_an_empty_caption(caption: str) -> None:
    """Scenario: The manual publish refuses an empty caption"""
    repo, gateway = _Repo(), _Gateway()
    _store(repo, _run())
    manual = _manual(repo, gateway, _Source(_snapshot()))
    command = ManualPublishCommand(
        project_id=_PROJECT, caption=caption, image_urls=_SEVEN
    )
    with pytest.raises(ManualPublishRefusedError) as refused:
        await manual.publish(command)
    assert refused.value.code == ERR_INSTAGRAM_CAPTION_EMPTY
    assert gateway.opens == 0
    assert gateway.atomics == 0


def test_the_gate_reads_the_override_caption_first() -> None:
    """Scenario: The autopilot worker never posts an empty caption"""
    snapshot = _snapshot()
    empty = CarouselMedia(caption=" ", image_urls=snapshot.image_urls)
    assert gate_reason(gate_for(snapshot, empty)) == ERR_INSTAGRAM_CAPTION_EMPTY
    assert gate_reason(gate_for(snapshot, None)) is None
    assert gate_for(None, None).has_caption is False


@pytest.mark.parametrize("resume", [True, False])
async def test_a_claimed_run_rechecks_the_caption(resume: bool) -> None:
    """Scenario: The autopilot worker never posts an empty caption"""
    repo, gateway, notifier = _Repo(), _Gateway(), _Notifier()
    gateway.resume = resume
    run = _store(repo, _run())
    job = _job(repo, gateway, _Source(_snapshot()), _Clock(), notifier)

    await job.publish_claimed(run, CarouselMedia(caption=" ", image_urls=_SEVEN))

    stored = repo.runs[run.run_id]
    assert stored.state is AutopilotRunState.PUBLISH_FAILED
    assert stored.state_reason == ERR_INSTAGRAM_CAPTION_EMPTY
    assert gateway.opens == 0
    assert gateway.atomics == 0
    assert [n.error_code for n in notifier.notices] == [ERR_INSTAGRAM_CAPTION_EMPTY]
