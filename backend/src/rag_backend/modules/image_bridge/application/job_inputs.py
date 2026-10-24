"""Who may fetch a photo of an image-edit job (contract section 2.4).

The Grok Bot fetches ``GET /jobs/{job_id}/inputs/{n}`` with the job's
callback token. Access holds only while the job is pending and not past its
deadline; the token is compared in constant time against the stored digest.
Any refusal looks the same to the caller (404), so job ids cannot be probed.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from uuid import UUID

from rag_backend.modules.image_bridge.domain.models import ImageBridgeJobStatus
from rag_backend.modules.image_bridge.domain.ports import (
    BridgeClock,
    ImageBridgeJobRepository,
)
from rag_backend.modules.image_bridge.domain.tokens import token_digest


@dataclass(frozen=True)
class JobInputRequest:
    """The job named in the URL and the token sent in the header."""

    job_id: UUID
    token: str


class JobInputGate:
    """Allows a photo fetch only for a live job and its own token."""

    def __init__(
        self, repository: ImageBridgeJobRepository, clock: BridgeClock
    ) -> None:
        self._repository = repository
        self._clock = clock

    async def allows(self, request: JobInputRequest) -> bool:
        """True while the job is pending, before its deadline, with its token."""
        if not request.token:
            return False
        job = await self._repository.get(request.job_id)
        if job is None or job.status is not ImageBridgeJobStatus.PENDING:
            return False
        if job.is_overdue(self._clock.now()):
            return False
        return hmac.compare_digest(token_digest(request.token), job.token_sha256)


__all__ = ["JobInputGate", "JobInputRequest"]
