"""Ports the autopilot runner needs for one session.

Split from ``runner`` so that file stays under 400 lines; ``runner`` re-exports it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.start_spacing import StartSpacing
from rag_backend.modules.autopilot.domain.autofix import (
    ContentAutofixer,
    GateRepairer,
    SlideFixer,
)
from rag_backend.modules.autopilot.domain.cover_ports import CoverOffers, CoverSwitcher
from rag_backend.modules.autopilot.domain.gate import (
    EditorialDriver,
    OwnerReadyNotifier,
    ProjectInputs,
)
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    Clock,
    TopicCandidateRepository,
)
from rag_backend.modules.autopilot.domain.recovery import RunRecoveryStore


def _never_retryable(_exc: BaseException) -> bool:
    """Outside the generation queue every engine error is contained."""
    return False


@dataclass(frozen=True, kw_only=True)
class RunnerDependencies:
    """Ports for one session. The worker builds a new bundle each tick.

    ``autofix`` runs the owner's queued "Fix issues"; ``gate_repair`` repairs a gate
    before any revise, then ``slide_fix`` model-fixes what still fails (no revise).
    ``spacing`` keeps a queued run waiting until the previous start is old enough.
    ``retryable`` names the errors the generation queue retries instead.
    """

    runs: AutopilotRunRepository
    topics: TopicCandidateRepository
    editorial: EditorialDriver
    notices: OwnerReadyNotifier
    recovery: RunRecoveryStore
    owner_user_id: str
    inputs: ProjectInputs
    notifier_configured: bool = True
    clock: Clock = field(default_factory=SystemClock)
    autofix: ContentAutofixer | None = None
    gate_repair: GateRepairer | None = None
    slide_fix: SlideFixer | None = None
    covers: CoverOffers | None = None
    cover_switch: CoverSwitcher | None = None
    spacing: StartSpacing | None = None
    retryable: Callable[[BaseException], bool] = field(default=_never_retryable)


__all__ = ["RunnerDependencies"]
