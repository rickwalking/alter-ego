"""Outbound ports for autopilot persistence.

Infrastructure adapters implement these Protocols. The domain does not
import the adapters (ADR-0009 §9).
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    IntegrationCredential,
    TelegramUpdate,
    TopicCandidate,
    TransitionCommand,
)


class AutopilotRunRepository(Protocol):
    """Persistence port for autopilot runs, including conditional transition."""

    async def add(self, run: AutopilotRun) -> None:
        """Insert a run. The topic row must already exist."""
        ...

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        """Return the run, or None when the id is unknown."""
        ...

    async def transition(self, command: TransitionCommand) -> bool:
        """Compare-and-set the state. False when the expected state is stale."""
        ...


class TopicCandidateRepository(Protocol):
    """Persistence port for scout topic candidates."""

    async def add_topic(self, candidate: TopicCandidate) -> None:
        """Insert a topic candidate."""
        ...

    async def get_topic(self, candidate_id: UUID) -> TopicCandidate | None:
        """Return the candidate, or None when the id is unknown."""
        ...


class IntegrationCredentialRepository(Protocol):
    """Persistence port for encrypted provider tokens."""

    async def add_credential(self, credential: IntegrationCredential) -> None:
        """Insert a provider credential."""
        ...

    async def get_credential(self, provider: str) -> IntegrationCredential | None:
        """Return the credential, or None when the provider is unknown."""
        ...


class TelegramUpdateRepository(Protocol):
    """Persistence port for webhook ``update_id`` dedupe."""

    async def add_telegram_update(self, update: TelegramUpdate) -> None:
        """Insert an update id."""
        ...

    async def has_telegram_update(self, update_id: int) -> bool:
        """True when this update id was already stored."""
        ...
