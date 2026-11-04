"""Put a succeeded autopilot cover on slide 1 at the drive's next gate.

The background selection (``carousel_cover_autoselect``) waits until the
workflow is paused at a gate. The autopilot drive approves each gate and
claims the next phase at once, so that wait almost never sees a pause: the
first settled state it reads is the final review, where it must skip. Its
conflict is never retried, and a restart (a deploy) loses it. The drive itself
always stands at a gate before it resumes, so the runner asks here first.

Everything is read from the database, so a restart between the cover
succeeding and the next gate changes nothing: the carousel's newest succeeded
generation the autopilot started, and slide 1's cover fields recorded when it
was scheduled (the owner-choice baseline). The selection runs once without
waiting, under the very rules and write of the background one (the
generation's own asset on this carousel, the owner's choice wins, the project
lock and the lock-version CAS), before the finalize render, so the first final
review shows the cover. Each gate asks again: a conflict is retried at the
next one, a cover already in place is a no-op. The caller decides consent.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverPolling,
    AutoCoverSelection,
    AutoCoverSelector,
)
from rag_backend.domain.constants.cover_autoselect import OUTCOME_AUTO_SELECT_SELECTED
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    EditorialAutoCoverStore,
    SessionFactory,
)

_AT_ONCE = AutoCoverPolling(max_wait_seconds=0.0)


async def _autopilot_selection(
    sessions: SessionFactory, project_id: str
) -> AutoCoverSelection | None:
    """The carousel's succeeded autopilot generation and its recorded baseline."""
    from rag_backend.modules.editorial.infrastructure.cover_generations import (
        SqlCoverGenerationRepository,
    )

    async with sessions() as session:
        return await SqlCoverGenerationRepository(session).autopilot_selection(
            project_id
        )


async def select_cover_at_gate(project_id: str) -> bool:
    """True when slide 1 just took the carousel's succeeded autopilot cover."""
    from rag_backend.infrastructure.database.config import get_session_maker

    sessions = get_session_maker()
    selection = await _autopilot_selection(sessions, project_id)
    if selection is None:
        return False
    store = EditorialAutoCoverStore(sessions)
    outcome = await AutoCoverSelector(store, _AT_ONCE).select(selection)
    return outcome == OUTCOME_AUTO_SELECT_SELECTED


__all__ = ["select_cover_at_gate"]
