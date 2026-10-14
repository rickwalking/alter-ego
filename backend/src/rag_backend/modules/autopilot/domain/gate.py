"""Gate snapshots and the editorial driver the runner calls.

Pure data. The infrastructure adapter fills a snapshot from workflow
state; policy decides without calling the editorial module.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class GateAction(StrEnum):
    """What the runner should do with the current gate."""

    APPROVE = "approve"
    REVISE = "revise"
    ESCALATE = "escalate"
    STOP = "stop"
    WAIT = "wait"


class StartStatus(StrEnum):
    """Outcome of an in-process workflow start."""

    STARTED = "started"
    PROVIDER_OUTAGE = "provider_outage"


class ResumeStatus(StrEnum):
    """Outcome of one approve or revise."""

    APPLIED = "applied"
    VERSION_CONFLICT = "version_conflict"
    REVISION_CAP = "revision_cap"
    PROVIDER_OUTAGE = "provider_outage"


@dataclass(frozen=True, kw_only=True)
class PolicyDecision:
    """The policy result for one snapshot."""

    action: GateAction
    reason: str


@dataclass(frozen=True, kw_only=True)
class ResearchSourceFact:
    """One research finding the research check can see."""

    content: str
    summary: str
    key_points: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class ImageFact:
    """Measured bytes for one image asset."""

    present: bool
    is_jpeg: bool
    width: int
    height: int


@dataclass(frozen=True, kw_only=True)
class SnapshotParts:
    """Inputs for one snapshot. One object keeps the assembler at one argument."""

    state: Mapping[str, object]
    images: tuple[ImageFact, ...]
    slides_total: int
    lock_version: int
    stale: bool
    # The engine's own content-approve verdict (error code), empty when it
    # would accept. Lets the policy revise instead of approving into a refusal.
    engine_blocker: str = ""


@dataclass(frozen=True, kw_only=True)
class GateSnapshot:
    """Deterministic facts for one gate. No workflow engine types."""

    phase: str
    phase_status: str
    lock_version: int
    sources: tuple[ResearchSourceFact, ...]
    outline_count: int
    slides_total: int
    persona_score: float | None
    forbidden_hits: tuple[str, ...]
    presentation_blockers: tuple[str, ...]
    images: tuple[ImageFact, ...]
    revisions_used: int
    stale: bool
    engine_blocker: str = ""


@dataclass(frozen=True, kw_only=True)
class ProjectSpec:
    """Fields the runner copies from the topic candidate onto a carousel."""

    topic: str
    audience: str
    niche: str
    brief: str
    sources: tuple[str, ...]
    owner_user_id: str


@dataclass(frozen=True, kw_only=True)
class StartCommand:
    """Start the workflow for a project that already exists."""

    project_id: str
    spec: ProjectSpec
    phase: str


@dataclass(frozen=True, kw_only=True)
class ResumeCommand:
    """One approve or revise at the current lock version."""

    project_id: str
    action: str
    expected_version: int
    feedback: str
    phase: str
    target_phase: str = ""


@dataclass(frozen=True, kw_only=True)
class ResumeResult:
    """Whether the resume was applied or must be retried later."""

    status: ResumeStatus


@dataclass(frozen=True, kw_only=True)
class AttachProjectCommand:
    """Link a carousel to a queued run. One row, still queued."""

    run_id: UUID
    project_id: str


@dataclass(frozen=True, kw_only=True)
class StartAttemptCommand:
    """Count a failed start without leaving ``queued``."""

    run_id: UUID
    attempts: int
    reason: str


@dataclass(frozen=True, kw_only=True)
class OwnerReadyNotice:
    """The owner may review this carousel. Emitted once per revision."""

    run_id: UUID
    project_id: str
    revision: int = 0
    persona_score: float | None = None
    sources_count: int = 0


class EditorialDriver(Protocol):
    """In-process editorial operations. No HTTP."""

    async def create_project(self, spec: ProjectSpec) -> str:
        """Create the carousel and return its id."""
        ...

    async def start(self, command: StartCommand) -> StartStatus:
        """Run workflow start until the first gate, or report an outage."""
        ...

    async def read_gate(self, project_id: str) -> GateSnapshot:
        """Read the current gate. Does not resume the workflow."""
        ...

    async def resume(self, command: ResumeCommand) -> ResumeResult:
        """Approve or revise once, using ``expected_version``."""
        ...


class OwnerReadyNotifier(Protocol):
    """Records ``content.autopilot.ready_for_owner``. The caller commits."""

    async def notify_ready(self, notice: OwnerReadyNotice) -> None:
        """Stage one ready event. Must not call Telegram."""
        ...
