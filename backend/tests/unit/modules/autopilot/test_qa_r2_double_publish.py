"""Double-publish edge windows (AE-0348 QA r2 R4).

Gherkin: tests/features/autopilot_instagram_publish.feature
  Scenario: A stale publish claim is not taken over while Graph may still run
  Scenario: A manual publish crash after the container reuses that container
  Scenario: An approved carousel that is not public yet is not failed
"""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field, replace
from datetime import timedelta
from uuid import UUID

import httpx
import pytest

from rag_backend.domain.constants.instagram_publish import (
    GRAPH_PUBLISH_WORST_CASE_SECONDS,
    GRAPH_REQUEST_DEADLINE_SECONDS,
    MAX_INSTAGRAM_CAROUSEL_ITEMS,
)
from rag_backend.domain.constants.retry import (
    META_MAX_ATTEMPTS,
    META_POLL_INTERVAL_SECONDS,
    META_POLL_MAX_ATTEMPTS,
)
from rag_backend.infrastructure.external import meta_instagram_publisher
from rag_backend.modules.autopilot.application.manual_publish import (
    ManualInstagramPublish,
)
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
)
from rag_backend.modules.autopilot.constants import (
    CONTAINER_REUSE_HOURS,
    REASON_CAROUSEL_NOT_PUBLIC,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.publish import ManualPublishCommand
from rag_backend.modules.autopilot.domain.publish_claims import (
    ManualContainer,
    RunClaim,
)
from rag_backend.modules.autopilot.recovery_constants import (
    MANUAL_CLAIM_STALE_MINUTES,
    RELEASE_GRACE_SECONDS,
)
from tests.unit.infrastructure.test_meta_instagram_publisher import _publisher
from tests.unit.modules.autopilot.test_instagram_publish_job import (
    _PROJECT,
    _SEVEN,
    _Claims,
    _Clock,
    _deps,
    _Gateway,
    _job,
    _Notifier,
    _Repo,
    _run,
    _snapshot,
    _Source,
    _store,
)

_COMMAND = ManualPublishCommand(project_id=_PROJECT, caption="cap", image_urls=_SEVEN)


# --- R4a: the stale window outlasts the slowest Graph publish ----------------


def test_worst_case_graph_publish_is_derived_from_the_retry_constants() -> None:
    # quota, expired-container status, items, parent, polls, publish, permalink
    requests = 1 + 1 + MAX_INSTAGRAM_CAROUSEL_ITEMS + 1 + META_POLL_MAX_ATTEMPTS + 1 + 1
    expected = (
        requests * META_MAX_ATTEMPTS * GRAPH_REQUEST_DEADLINE_SECONDS
        + META_POLL_MAX_ATTEMPTS * META_POLL_INTERVAL_SECONDS
    )
    assert expected == GRAPH_PUBLISH_WORST_CASE_SECONDS


# Scenario: A stale publish claim is not taken over while Graph may still run
def test_stale_claim_window_outlasts_the_worst_case_publish() -> None:
    assert MANUAL_CLAIM_STALE_MINUTES * 60 > GRAPH_PUBLISH_WORST_CASE_SECONDS
    assert MANUAL_CLAIM_STALE_MINUTES >= math.ceil(
        GRAPH_PUBLISH_WORST_CASE_SECONDS / 60
    )


@dataclass
class _Refusing(_Claims):
    """Refuses the claim on chosen runs, like a fresh claim held elsewhere."""

    refused: set[UUID] = field(default_factory=set)
    claims_seen: list[RunClaim] = field(default_factory=list)

    async def claim_run(self, claim: RunClaim) -> bool:
        self.claims_seen.append(claim)
        if claim.run_id in self.refused:
            return False
        return await super().claim_run(claim)


# Scenario: A stale publish claim is not taken over while Graph may still run
@pytest.mark.asyncio
async def test_a_refused_claim_does_not_block_the_next_due_run() -> None:
    repo, gateway, clock = _Repo(), _Gateway(), _Clock()
    blocked = _store(repo, _run())
    other = _store(repo, _run())
    claims = _Refusing(refused={blocked.run_id})
    job = _job_with(repo, gateway, clock, claims)

    assert await job.tick() == 1

    assert repo.runs[other.run_id].state is AutopilotRunState.PUBLISHED
    assert repo.runs[blocked.run_id].state is AutopilotRunState.PUBLISHING
    stale = clock.now() - timedelta(minutes=MANUAL_CLAIM_STALE_MINUTES)
    assert {claim.stale_before for claim in claims.claims_seen} == {stale}


# Scenario: A stale publish claim is not taken over while Graph may still run
@pytest.mark.asyncio
async def test_expired_container_that_was_published_is_recovered_not_reposted() -> None:
    repo, gateway, clock = _Repo(), _Gateway(), _Clock()
    old = clock.now() - timedelta(hours=CONTAINER_REUSE_HOURS + 1)
    run = _store(
        repo,
        replace(_run(), ig_container_id="old-container", ig_container_created_at=old),
    )
    gateway.published_before = True

    await _job_with(repo, gateway, clock, _Claims()).tick()

    assert gateway.opens == 0
    assert gateway.last_container == "old-container"
    assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHED


@pytest.mark.asyncio
async def test_expired_unpublished_container_is_replaced() -> None:
    repo, gateway, clock = _Repo(), _Gateway(), _Clock()
    old = clock.now() - timedelta(hours=CONTAINER_REUSE_HOURS + 1)
    run = _store(
        repo,
        replace(_run(), ig_container_id="old-container", ig_container_created_at=old),
    )

    await _job_with(repo, gateway, clock, _Claims()).tick()

    assert gateway.opens == 1
    assert gateway.checked == ["old-container"]
    assert repo.runs[run.run_id].ig_container_id == "container-new"


# --- R4b: the manual (no-run) path stores its container first ---------------


# Scenario: A manual publish crash after the container reuses that container
@pytest.mark.asyncio
async def test_manual_container_is_stored_before_media_publish() -> None:
    repo, gateway, claims = _Repo(), _Gateway(), _Claims()
    gateway.fail_finish = InstagramCallError(
        status_code=0, error_code="instagram_container_timeout", transient=True
    )
    manual = ManualInstagramPublish(_manual_deps(repo, gateway, claims))

    first = await manual.publish(_COMMAND)
    gateway.fail_finish = None
    second = await manual.publish(_COMMAND)

    assert first.status == "failed"
    assert claims.saved_containers == [
        ManualContainer(
            project_id=_PROJECT,
            container_id="container-new",
            created_at=_Clock().now(),
        )
    ]
    assert gateway.opens == 1
    assert gateway.finishes == 2
    assert gateway.last_container == "container-new"
    assert second.ig_post_id == "post-1"
    assert gateway.atomics == 0


@pytest.mark.asyncio
async def test_manual_crash_mid_publish_keeps_the_container_for_the_retry() -> None:
    repo, gateway, claims = _Repo(), _Gateway(), _Claims()
    manual = ManualInstagramPublish(_manual_deps(repo, gateway, claims))
    gateway.crash_finish = True

    with pytest.raises(RuntimeError):
        await manual.publish(_COMMAND)
    gateway.crash_finish = False
    outcome = await manual.publish(_COMMAND)

    assert gateway.opens == 1
    assert outcome.ig_post_id == "post-1"
    assert claims.manual[_PROJECT].ig_container_id == "container-new"


# --- R4c: approved but not public yet ----------------------------------------


# Scenario: An approved carousel that is not public yet is not failed
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("age_seconds", "fails"),
    [(RELEASE_GRACE_SECONDS - 30, False), (RELEASE_GRACE_SECONDS + 30, True)],
)
async def test_not_public_inside_the_grace_window_waits(
    age_seconds: int, fails: bool
) -> None:
    repo, gateway, clock = _Repo(), _Gateway(), _Clock()
    run = _store(repo, _run())
    clock.advance(age_seconds)
    notifier = _Notifier()
    source = _Source(replace(_snapshot(), is_public=False))
    job = _job(repo, gateway, source, clock, notifier)

    await job.tick()

    stored = repo.runs[run.run_id]
    assert gateway.opens == 0
    if fails:
        assert stored.state is AutopilotRunState.PUBLISH_FAILED
        assert stored.state_reason == REASON_CAROUSEL_NOT_PUBLIC
        return
    assert stored.state is AutopilotRunState.PUBLISHING
    assert notifier.notices == []


def _job_with(
    repo: _Repo, gateway: _Gateway, clock: _Clock, claims: _Claims
) -> InstagramPublishJob:
    deps = _deps(repo, gateway, _Source(_snapshot()), clock, _Notifier(), claims)
    return InstagramPublishJob(deps)


def _manual_deps(
    repo: _Repo, gateway: _Gateway, claims: _Claims
) -> PublishJobDependencies:
    return _deps(repo, gateway, _Source(None), _Clock(), _Notifier(), claims)


# Scenario: A stale publish claim is not taken over while Graph may still run
@pytest.mark.asyncio
async def test_a_hanging_graph_request_ends_at_the_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def hang(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5)
        return httpx.Response(200, json={"status_code": "FINISHED"})

    monkeypatch.setattr(meta_instagram_publisher, "_REQUEST_DEADLINE_SECONDS", 0.05)
    client = httpx.AsyncClient(transport=httpx.MockTransport(hang))
    publisher = _publisher("token", "ig-user", client)

    started = time.monotonic()
    with pytest.raises(httpx.TimeoutException):
        await publisher.container_status("container-1")

    assert time.monotonic() - started < 1
