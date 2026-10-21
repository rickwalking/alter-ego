"""Unknown published media is terminal and never retried (QA r2 R3).

Gherkin: tests/features/autopilot_instagram_publish.feature
  Scenario: A manual post before the container is not taken as the autopilot post
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN,
)
from rag_backend.modules.autopilot.constants import (
    EVENT_TYPE_PUBLISH_NOTICE,
    NOTICE_PUBLISH_FAILED,
    PAYLOAD_ERROR_CODE,
    PAYLOAD_OFFER_RETRY,
    PAYLOAD_OUTCOME,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.notify_constants import TEXT_PUBLISHED_MEDIA_UNKNOWN
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_MAY_BE_LIVE,
    TEXT_MAY_BE_LIVE,
)
from tests.unit.modules.autopilot.test_owner_actions import (
    _action,
    _handle,
    _tap,
    _world,
)
from tests.unit.modules.autopilot.test_owner_notifications import (
    _event,
    _Events,
    _Notifier,
    _run,
    _Runs,
    _service,
)


# Scenario: A manual post before the container is not taken as the autopilot post
@pytest.mark.asyncio
async def test_unknown_media_notice_has_no_retry_button() -> None:
    failed = _event(
        EVENT_TYPE_PUBLISH_NOTICE,
        {
            PAYLOAD_OUTCOME: NOTICE_PUBLISH_FAILED,
            PAYLOAD_ERROR_CODE: ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN,
            PAYLOAD_OFFER_RETRY: False,
        },
        event_id="unknown",
    )
    notifier = _Notifier()
    service, _store = _service(
        _Events([failed]),
        _Runs(_run(state=AutopilotRunState.PUBLISH_FAILED)),
        notifier,
    )

    assert await service.tick() == 1

    [notice] = notifier.statuses
    assert notice.keyboard is None
    assert notice.text == TEXT_PUBLISHED_MEDIA_UNKNOWN
    assert "check Instagram" in notice.text


@pytest.mark.asyncio
async def test_other_publish_failures_keep_the_retry_button() -> None:
    failed = _event(
        EVENT_TYPE_PUBLISH_NOTICE,
        {
            PAYLOAD_OUTCOME: NOTICE_PUBLISH_FAILED,
            PAYLOAD_ERROR_CODE: "36003",
            PAYLOAD_OFFER_RETRY: True,
        },
        event_id="other",
    )
    notifier = _Notifier()
    service, _store = _service(
        _Events([failed]),
        _Runs(_run(state=AutopilotRunState.PUBLISH_FAILED)),
        notifier,
    )

    await service.tick()

    [notice] = notifier.statuses
    assert notice.keyboard is not None


# Scenario: A manual post before the container is not taken as the autopilot post
@pytest.mark.asyncio
async def test_retry_is_refused_when_the_post_may_be_live() -> None:
    world = _world()
    world.runs.run = replace(
        world.runs.run,
        state=AutopilotRunState.PUBLISH_FAILED,
        state_reason=ERR_INSTAGRAM_PUBLISHED_MEDIA_UNKNOWN,
    )

    await _handle(world, _tap(1, _action("retry", world)))

    assert world.runs.run.state is AutopilotRunState.PUBLISH_FAILED
    assert world.messenger.answers[-1].text == ANSWER_MAY_BE_LIVE
    assert world.messenger.edits[-1].text == TEXT_MAY_BE_LIVE
    assert world.messenger.edits[-1].keyboard is None
