"""The publishing-limit read asks for ``config`` and tolerates its absence.

Response shapes are the ones verified live on ``graph.instagram.com/v23.0``.

Gherkin: tests/features/autopilot_instagram_publish.feature
  Scenario: The quota read requests the config field
  Scenario: A quota body without config falls back to the documented limit
  Scenario: An unreadable quota fails the run instead of looping forever

The ``_BODY_*`` constants are live Graph v23.0 response bodies.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from rag_backend.domain.constants.instagram_publish import (
    DEFAULT_PUBLISHING_QUOTA_TOTAL,
    ERR_INSTAGRAM_QUOTA_UNREADABLE,
    PUBLISHING_LIMIT_FIELDS,
)
from rag_backend.infrastructure.external.instagram_graph_error import (
    InstagramGraphError,
)
from rag_backend.infrastructure.external.instagram_graph_payloads import (
    quota_remaining,
)
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
)
from rag_backend.modules.autopilot.constants import (
    NOTICE_PUBLISH_FAILED,
    NOTICE_PUBLISHED,
    PUBLISH_BACKOFF_SECONDS,
    PUBLISH_MAX_ATTEMPTS,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.instagram_gateway import (
    SteppedInstagramGateway,
)
from tests.unit.infrastructure.test_meta_instagram_publisher import _publisher
from tests.unit.modules.autopilot.test_instagram_publish_job import (
    _Claims,
    _Clock,
    _Notifier,
    _Repo,
    _run,
    _snapshot,
    _Source,
)

_HOST = "graph.instagram.com"
_LIMIT_PATH = "content_publishing_limit"
_BODY_WITHOUT_FIELDS: dict[str, object] = {"data": [{"quota_usage": 0}]}
_BODY_WITH_FIELDS: dict[str, object] = {
    "data": [
        {"quota_usage": 0, "config": {"quota_total": 100, "quota_duration": 86400}}
    ]
}
_UNREADABLE_BODY: dict[str, object] = {"data": []}


class _Graph:
    """Graph double: the quota body is configurable, the publish steps succeed."""

    def __init__(self, quota_body: dict[str, object]) -> None:
        self.quota_body = quota_body
        self.quota_requests: list[httpx.Request] = []
        self.posts = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if _LIMIT_PATH in request.url.path:
            self.quota_requests.append(request)
            return httpx.Response(200, json=self.quota_body)
        if request.method == "POST":
            self.posts += 1
            return httpx.Response(200, json={"id": f"id-{self.posts}"})
        if "permalink" in request.url.params.get("fields", ""):
            return httpx.Response(200, json={"permalink": "https://instagram.com/p/q"})
        return httpx.Response(200, json={"status_code": "FINISHED"})


def _job(graph: _Graph) -> tuple[InstagramPublishJob, _Repo, _Notifier, _Clock]:
    repo, notifier, clock = _Repo(), _Notifier(), _Clock()
    run = _run()
    repo.runs[run.run_id] = run
    gateway = SteppedInstagramGateway(_publisher("IGAA-token", "ig-user"))
    deps = PublishJobDependencies(
        runs=repo,
        source=_Source(_snapshot()),
        gateway=gateway,
        notifier=notifier,
        clock=clock,
        checkpoint=repo,
        claims=_Claims(),
    )
    return InstagramPublishJob(deps), repo, notifier, clock


@pytest.mark.unit
class TestQuotaRequestFields:
    """Scenario: The quota read requests the config field."""

    async def test_request_carries_fields_and_reads_config_total(self) -> None:
        graph = _Graph(_BODY_WITH_FIELDS)
        with respx.mock(assert_all_called=True) as router:
            router.route(host=_HOST).mock(side_effect=graph)
            remaining = await _publisher("t", "ig-user").content_publishing_remaining()

        assert remaining == 100
        assert len(graph.quota_requests) == 1
        params = graph.quota_requests[0].url.params
        assert params["fields"] == PUBLISHING_LIMIT_FIELDS
        assert PUBLISHING_LIMIT_FIELDS == "quota_usage,config"

    def test_config_total_wins_over_the_default(self) -> None:
        body = {"data": [{"quota_usage": 3, "config": {"quota_total": 25}}]}
        assert quota_remaining(body) == 22


@pytest.mark.unit
class TestQuotaFallback:
    """Scenario: A quota body without config falls back to the documented limit."""

    async def test_body_without_config_uses_the_documented_limit(self) -> None:
        graph = _Graph(_BODY_WITHOUT_FIELDS)
        with respx.mock(assert_all_called=True) as router:
            router.route(host=_HOST).mock(side_effect=graph)
            remaining = await _publisher("t", "ig-user").content_publishing_remaining()

        assert DEFAULT_PUBLISHING_QUOTA_TOTAL == 100
        assert remaining == 100

    @pytest.mark.parametrize(
        "first",
        [
            {"quota_usage": 7},
            {"quota_usage": 7, "config": "not-a-dict"},
            {"quota_usage": 7, "config": {}},
            {"quota_usage": 7, "config": {"quota_total": True}},
            {"quota_usage": 7, "config": {"quota_total": "100"}},
        ],
    )
    def test_missing_or_bad_total_falls_back(self, first: dict[str, object]) -> None:
        assert quota_remaining({"data": [first]}) == 100 - 7

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"data": []},
            {"data": "x"},
            {"data": ["x"]},
            {"data": [{}]},
            {"data": [{"quota_usage": True, "config": {"quota_total": 100}}]},
            {"data": [{"quota_usage": "0", "config": {"quota_total": 100}}]},
        ],
    )
    def test_unreadable_usage_still_fails_closed(
        self, payload: dict[str, object]
    ) -> None:
        with pytest.raises(InstagramGraphError) as caught:
            quota_remaining(payload)
        assert caught.value.error_code == ERR_INSTAGRAM_QUOTA_UNREADABLE
        assert caught.value.transient is True

    async def test_publish_proceeds_on_the_fieldless_shape(self) -> None:
        graph = _Graph(_BODY_WITHOUT_FIELDS)
        job, repo, notifier, _clock = _job(graph)
        with respx.mock(assert_all_called=False) as router:
            router.route(host=_HOST).mock(side_effect=graph)
            assert await job.tick() == 1

        stored = next(iter(repo.runs.values()))
        assert stored.state is AutopilotRunState.PUBLISHED
        assert graph.posts > 0
        assert [notice.outcome for notice in notifier.notices] == [NOTICE_PUBLISHED]


@pytest.mark.unit
class TestQuotaUnreadableBounded:
    """Scenario: An unreadable quota fails the run instead of looping forever."""

    async def test_unreadable_quota_fails_after_the_retry_budget(self) -> None:
        graph = _Graph(_UNREADABLE_BODY)
        job, repo, notifier, clock = _job(graph)
        with respx.mock(assert_all_called=False) as router:
            router.route(host=_HOST).mock(side_effect=graph)
            assert await job.tick() == 1
            for wait in PUBLISH_BACKOFF_SECONDS:
                stored = next(iter(repo.runs.values()))
                assert stored.state is AutopilotRunState.PUBLISHING
                assert stored.state_reason == ERR_INSTAGRAM_QUOTA_UNREADABLE
                clock.advance(wait)
                assert await job.tick() == 1

        stored = next(iter(repo.runs.values()))
        assert stored.state is AutopilotRunState.PUBLISH_FAILED
        assert stored.state_reason == ERR_INSTAGRAM_QUOTA_UNREADABLE
        assert stored.publish_attempts == PUBLISH_MAX_ATTEMPTS
        assert len(graph.quota_requests) == PUBLISH_MAX_ATTEMPTS
        assert graph.posts == 0
        assert len(notifier.notices) == 1
        notice = notifier.notices[0]
        assert notice.outcome == NOTICE_PUBLISH_FAILED
        assert notice.error_code == ERR_INSTAGRAM_QUOTA_UNREADABLE
        assert notice.offer_retry is True
