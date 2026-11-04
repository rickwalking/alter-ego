"""Put a succeeded autopilot cover on slide 1 at the drive's next gate.

The background selection (``carousel_cover_autoselect``) waits until the
workflow is paused at a gate. The autopilot drive approves each gate and
claims the next phase at once, so that wait almost never sees a pause: the
first settled state it reads is the final review, where it must skip, and the
owner's first review shows the default slide 1. The drive itself always
stands at a gate before it resumes, so the runner asks here first.

An autopilot generation that succeeded is remembered in this process, with
its scheduling baseline, until a selection settled it. At a gate the
selection runs once without waiting, under the very rules and write of the
background one (the generation's own asset on this carousel, the owner's
choice wins, the project lock and the lock-version CAS), before the finalize
render, so the first final review shows the cover. A conflict, a held lock or
a wait that ran out keeps it for the next gate; any other outcome forgets it.
A restart forgets it too: the cover then stays a picker option, as when the
background wait is lost. The caller decides consent.
"""

from __future__ import annotations

import typing
from collections.abc import Awaitable, Callable

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverPolling,
    AutoCoverSelection,
    AutoCoverSelector,
)
from rag_backend.domain.constants.cover_autoselect import (
    OUTCOME_AUTO_SELECT_SELECTED,
    REASON_AUTO_SELECT_CONFLICT,
    REASON_AUTO_SELECT_TIMED_OUT,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.cover_generation import CoverGenerationStatus
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    EditorialAutoCoverStore,
    cover_selection,
    select_logged,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_generation import (
    CoverRunWiring,
    cover_generation_task,
)

if typing.TYPE_CHECKING:
    from rag_backend.application.services.carousel.cover_generation import (
        CoverGenerationRun,
    )

_RETRIED = frozenset({REASON_AUTO_SELECT_CONFLICT, REASON_AUTO_SELECT_TIMED_OUT})
_AT_ONCE = AutoCoverPolling(max_wait_seconds=0.0)
_pending: dict[str, AutoCoverSelection] = {}


def _settle(selection: AutoCoverSelection, outcome: str) -> None:
    """Forget ``selection`` unless ``outcome`` may change at a later gate."""
    if outcome in _RETRIED:
        return
    if _pending.get(selection.project_id) == selection:
        del _pending[selection.project_id]


async def select_cover_at_gate(project_id: str) -> bool:
    """True when slide 1 just took the carousel's succeeded autopilot cover."""
    from rag_backend.infrastructure.database.config import get_session_maker

    selection = _pending.get(project_id)
    if selection is None:
        return False
    store = EditorialAutoCoverStore(get_session_maker())
    outcome = await AutoCoverSelector(store, _AT_ONCE).select(selection)
    _settle(selection, outcome)
    return outcome == OUTCOME_AUTO_SELECT_SELECTED


def remembering_cover_task(
    wiring: CoverRunWiring, run: CoverGenerationRun, project: CarouselProject
) -> Callable[[], Awaitable[CoverGenerationStatus]]:
    """The autopilot's run of ``run``: remembered once it succeeded, then the
    background selection, which settles it like the drive's gate does."""
    generate = cover_generation_task(wiring, run)
    selection = cover_selection(run, project)

    async def _execute() -> CoverGenerationStatus:
        status = await generate()
        if status is CoverGenerationStatus.SUCCEEDED:
            _pending[selection.project_id] = selection
            _settle(selection, await select_logged(selection))
        return status

    return _execute


__all__ = ["remembering_cover_task", "select_cover_at_gate"]
