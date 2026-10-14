"""The manual publish resumes from the ledger read after its claim (QA r3 Q4).

Gherkin: tests/features/autopilot_instagram_publish.feature
  Scenario: A manual publish resumes the container another attempt just stored
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from rag_backend.modules.autopilot.application.manual_publish import (
    ManualInstagramPublish,
)
from rag_backend.modules.autopilot.domain.publish import ManualPublishCommand
from rag_backend.modules.autopilot.domain.publish_claims import (
    ManualClaim,
    ManualRecord,
)
from rag_backend.modules.autopilot.recovery_constants import (
    MANUAL_STATE_FAILED,
    MANUAL_STATE_PUBLISHED,
)
from tests.unit.modules.autopilot.test_instagram_publish_job import (
    _NOW,
    _PROJECT,
    _SEVEN,
    _Claims,
    _Clock,
    _deps,
    _Gateway,
    _Notifier,
    _Repo,
    _Source,
)

_COMMAND = ManualPublishCommand(project_id=_PROJECT, caption="cap", image_urls=_SEVEN)


@dataclass
class _RacingClaims(_Claims):
    """Another attempt writes the ledger between our read and our claim."""

    racer: ManualRecord | None = None

    async def claim_manual(self, claim: ManualClaim) -> bool:
        if self.racer is not None:
            self.manual[claim.project_id] = self.racer
        return await super().claim_manual(claim)


def _racer(state: str, post_id: str | None) -> ManualRecord:
    return ManualRecord(
        project_id=_PROJECT,
        state=state,
        ig_post_id=post_id,
        ig_permalink=None,
        error=None,
        ig_container_id="racer-container",
        ig_container_created_at=_NOW,
    )


def _manual(gateway: _Gateway, claims: _Claims) -> ManualInstagramPublish:
    deps = _deps(_Repo(), gateway, _Source(None), _Clock(), _Notifier(), claims)
    return ManualInstagramPublish(deps)


# Scenario: A manual publish resumes the container another attempt just stored
@pytest.mark.asyncio
async def test_the_container_stored_before_the_claim_is_resumed() -> None:
    gateway = _Gateway()
    claims = _RacingClaims(racer=_racer(MANUAL_STATE_FAILED, None))

    outcome = await _manual(gateway, claims).publish(_COMMAND)

    assert gateway.opens == 0
    assert gateway.last_container == "racer-container"
    assert outcome.ig_post_id == "post-1"


@pytest.mark.asyncio
async def test_a_post_id_stored_before_the_claim_short_circuits() -> None:
    gateway = _Gateway()
    claims = _RacingClaims(racer=_racer(MANUAL_STATE_PUBLISHED, "racer-post"))

    outcome = await _manual(gateway, claims).publish(_COMMAND)

    assert gateway.opens == 0
    assert gateway.finishes == 0
    assert outcome.ig_post_id == "racer-post"
    assert _PROJECT not in claims.manual_held
    assert claims.manual[_PROJECT].ig_post_id == "racer-post"
