"""A container that is already PUBLISHED is recovered, never published twice (QA r1 H2).

Gherkin: tests/features/autopilot_instagram_publish.feature
  Scenario: Crash after media_publish recovers the published post
  Scenario: Published container whose media cannot be matched fails without reposting
  Scenario: A manual post before the container is not taken as the autopilot post
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from rag_backend.domain.constants.instagram_publish import (
    CONTAINER_STATUS_PUBLISHED,
    ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN,
    GRAPH_TIMESTAMP_FORMAT,
    MEDIA_TYPE_CAROUSEL_ALBUM,
)
from rag_backend.infrastructure.external.instagram_graph_payloads import (
    recent_carousel_id,
)
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
)
from rag_backend.modules.autopilot.constants import NOTICE_PUBLISHED
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.publish import StoredContainer
from rag_backend.modules.autopilot.infrastructure.instagram_gateway import (
    SteppedInstagramGateway,
)
from tests.unit.infrastructure.test_meta_instagram_publisher import (
    _publisher,
    _transport,
)
from tests.unit.modules.autopilot.test_instagram_publish_job import (
    _Claims,
    _Clock,
    _Notifier,
    _Repo,
    _run,
    _snapshot,
    _Source,
)

_CONTAINER = "container-77"
_RECOVERED = "media-recovered"
_CREATED_AGO = timedelta(minutes=5)


def _stored_container() -> StoredContainer:
    return StoredContainer(
        container_id=_CONTAINER, created_at=datetime.now(UTC) - _CREATED_AGO
    )


def _stamp(delta: timedelta) -> str:
    return (datetime.now(UTC) - delta).strftime(GRAPH_TIMESTAMP_FORMAT)


def _album(media_id: str, age: timedelta) -> dict[str, str]:
    return {
        "id": media_id,
        "media_type": MEDIA_TYPE_CAROUSEL_ALBUM,
        "timestamp": _stamp(age),
    }


class _Graph:
    """Container is PUBLISHED; ``/media`` lists the given recent media."""

    def __init__(self, recent: list[dict[str, str]]) -> None:
        self.recent = recent
        self.publish_calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "media_publish" in path:
            self.publish_calls += 1
            return httpx.Response(200, json={"id": "duplicate-post"})
        if "content_publishing_limit" in path:
            return httpx.Response(
                200, json={"data": [{"quota_usage": 0, "config": {"quota_total": 5}}]}
            )
        if path.endswith("/media"):
            return httpx.Response(200, json={"data": self.recent})
        if "fields=permalink" in str(request.url):
            return httpx.Response(200, json={"permalink": "https://instagram.com/p/r"})
        return httpx.Response(200, json={"status_code": CONTAINER_STATUS_PUBLISHED})


def _gateway(graph: _Graph) -> SteppedInstagramGateway:
    return SteppedInstagramGateway(_publisher("token", "ig-user", _transport(graph)))


def _job_with_stored_container(
    graph: _Graph,
) -> tuple[InstagramPublishJob, _Repo, _Notifier]:
    clock = _Clock()
    repo = _Repo()
    run = replace(
        _run(),
        ig_container_id=_CONTAINER,
        ig_container_created_at=datetime.now(UTC) - _CREATED_AGO,
    )
    repo.runs[run.run_id] = run
    notifier = _Notifier()
    deps = PublishJobDependencies(
        runs=repo,
        source=_Source(_snapshot()),
        gateway=_gateway(graph),
        notifier=notifier,
        clock=clock,
        checkpoint=repo,
        claims=_Claims(),
    )
    return InstagramPublishJob(deps), repo, notifier


@pytest.mark.unit
async def test_crash_after_media_publish_marks_the_run_published() -> None:
    """Scenario: Crash after media_publish recovers the published post."""
    graph = _Graph([_album(_RECOVERED, timedelta(minutes=3))])
    job, repo, notifier = _job_with_stored_container(graph)

    assert await job.tick() == 1

    stored = next(iter(repo.runs.values()))
    assert graph.publish_calls == 0
    assert stored.state is AutopilotRunState.PUBLISHED
    assert stored.ig_post_id == _RECOVERED
    assert [notice.outcome for notice in notifier.notices] == [NOTICE_PUBLISHED]


@pytest.mark.unit
async def test_unmatched_published_container_fails_without_reposting() -> None:
    """Scenario: Published container whose media cannot be matched fails without reposting."""
    graph = _Graph([_album("old-post", timedelta(hours=30))])
    job, repo, notifier = _job_with_stored_container(graph)

    await job.tick()

    stored = next(iter(repo.runs.values()))
    assert graph.publish_calls == 0
    assert stored.state is AutopilotRunState.PUBLISH_FAILED
    assert stored.state_reason == ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN
    assert stored.ig_post_id is None
    # QA r2 R3: Retry would create a new container and could post twice.
    assert [notice.offer_retry for notice in notifier.notices] == [False]


@pytest.mark.unit
async def test_manual_post_before_the_container_is_ignored() -> None:
    """Scenario: A manual post before the container is not taken as the autopilot post."""
    graph = _Graph([_album("manual-post", _CREATED_AGO + timedelta(minutes=2))])
    job, repo, notifier = _job_with_stored_container(graph)

    await job.tick()

    stored = next(iter(repo.runs.values()))
    assert stored.ig_post_id is None
    assert stored.state_reason == ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN
    assert [notice.offer_retry for notice in notifier.notices] == [False]


@pytest.mark.unit
async def test_two_albums_after_the_container_are_not_guessed() -> None:
    """Scenario: A manual post before the container is not taken as the autopilot post."""
    graph = _Graph([
        _album(_RECOVERED, timedelta(minutes=3)),
        _album("manual-post", timedelta(minutes=1)),
    ])
    with pytest.raises(InstagramCallError) as caught:
        await _gateway(graph).finish_container(_stored_container())
    assert caught.value.error_code == ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN


@pytest.mark.unit
async def test_gateway_raises_a_permanent_error_when_nothing_matches() -> None:
    """Scenario: Published container whose media cannot be matched fails without reposting."""
    graph = _Graph([])
    with pytest.raises(InstagramCallError) as caught:
        await _gateway(graph).finish_container(_stored_container())
    assert caught.value.error_code == ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN
    assert caught.value.transient is False
    assert graph.publish_calls == 0


@pytest.mark.unit
async def test_gateway_matches_the_album_posted_after_the_container() -> None:
    """Scenario: Crash after media_publish recovers the published post."""
    graph = _Graph([
        _album("older", timedelta(hours=2)),
        _album(_RECOVERED, timedelta(minutes=1)),
    ])
    assert await _gateway(graph).finish_container(_stored_container()) == _RECOVERED
    assert graph.publish_calls == 0


@pytest.mark.unit
def test_recent_carousel_id_skips_non_albums_and_malformed_rows() -> None:
    """Only carousel albums with an id and a parseable timestamp after ``since``."""
    since = datetime.now(UTC) - timedelta(hours=24)
    payload: dict[str, object] = {
        "data": [
            {"id": "image", "media_type": "IMAGE", "timestamp": _stamp(timedelta(0))},
            {
                "id": "",
                "media_type": MEDIA_TYPE_CAROUSEL_ALBUM,
                "timestamp": _stamp(timedelta(0)),
            },
            {
                "id": "bad-time",
                "media_type": MEDIA_TYPE_CAROUSEL_ALBUM,
                "timestamp": "yesterday",
            },
            {"id": "no-time", "media_type": MEDIA_TYPE_CAROUSEL_ALBUM},
            "not-a-dict",
            _album("kept", timedelta(hours=23)),
        ]
    }
    assert recent_carousel_id(payload, since) == "kept"
    assert recent_carousel_id({"data": "nope"}, since) is None
    assert recent_carousel_id({}, since) is None
