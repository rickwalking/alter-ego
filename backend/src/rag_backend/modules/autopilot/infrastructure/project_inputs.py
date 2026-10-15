"""``ProjectInputs`` over the editorial ACL (PR #106 review, items 3 and 4).

The persona comes from ``AUTOPILOT_PERSONA_ID``; when that is empty (or names
no persona) the persona called "Pedro" is used. None is a recorded decision,
not an error: Radar IA runs keep running unscored (AE-0364) and POV runs
escalate with ``persona_not_scored`` at the content gate.
"""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.pov_constants import (
    AUTOPILOT_PERSONA_NAME,
    LOG_PERSONA_UNRESOLVED,
)
from rag_backend.modules.editorial.public import PovInputsAcl

logger = structlog.get_logger(__name__)


class SqlProjectInputs:
    """Persona and slide-1 photo for one worker tick's session."""

    def __init__(self, session: AsyncSession, configured_persona_id: str) -> None:
        self._acl = PovInputsAcl(session)
        self._configured = configured_persona_id.strip()

    async def persona_id(self) -> str | None:
        """The configured persona, else "Pedro" by name, else None (logged)."""
        found = await self._acl.resolve_persona_id(
            self._configured, AUTOPILOT_PERSONA_NAME
        )
        if found is None:
            logger.warning(
                LOG_PERSONA_UNRESOLVED,
                configured=bool(self._configured),
                name=AUTOPILOT_PERSONA_NAME,
            )
        return found

    async def hook_photo_id(self, owner_user_id: str) -> str | None:
        """The owner's most recently used (else newest) usable hook photo."""
        return await self._acl.hook_photo_id(owner_user_id)


__all__ = ["SqlProjectInputs"]
