"""SQLAlchemy adapter for autopilot persistence.

``transition`` checks the domain table, then issues one conditional
``UPDATE … WHERE id AND state = expected``. A matching row stages exactly
one ``content.autopilot.state_changed`` outbox row in the same session.
The caller owns the commit (ADR-0009 unit of work).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.events.outbox_dispatch import (
    EventRecord,
    build_event_records,
)
from rag_backend.modules.autopilot.constants import (
    AGGREGATE_TYPE_AUTOPILOT_RUN,
    EVENT_TYPE_STATE_CHANGED,
    EVENT_VERSION,
    METADATA_MODULE,
    MODULE_NAME,
    PAYLOAD_PREVIOUS_STATE,
    PAYLOAD_REASON,
    PAYLOAD_STATE,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    IntegrationCredential,
    TelegramUpdate,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.state_machine import assert_allowed
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    IntegrationCredentialModel,
    TelegramUpdateModel,
    TopicCandidateModel,
)


class SqlAlchemyAutopilotRepository:
    """Session-scoped adapter. Structurally implements the four ports."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, run: AutopilotRun) -> None:
        """Insert a run. The topic row must already exist."""
        self._session.add(_run_row(run))
        await self._session.flush()

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        """Return the run, refreshing any identity-map copy after a CAS update."""
        result = await self._session.execute(
            select(AutopilotRunModel)
            .where(AutopilotRunModel.id == run_id)
            .execution_options(populate_existing=True)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _run_from_row(row)

    async def transition(self, command: TransitionCommand) -> bool:
        """CAS the state. Illegal pairs raise; a stale expected state returns False."""
        assert_allowed(command.pair())
        if not await self._compare_and_set(command):
            return False
        await self._emit_state_changed(command)
        return True

    async def add_topic(self, candidate: TopicCandidate) -> None:
        """Insert a topic candidate."""
        self._session.add(_topic_row(candidate))
        await self._session.flush()

    async def get_topic(self, candidate_id: UUID) -> TopicCandidate | None:
        """Return the candidate, or None when the id is unknown."""
        result = await self._session.execute(
            select(TopicCandidateModel).where(TopicCandidateModel.id == candidate_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _topic_from_row(row)

    async def add_credential(self, credential: IntegrationCredential) -> None:
        """Insert a provider credential."""
        self._session.add(_credential_row(credential))
        await self._session.flush()

    async def get_credential(self, provider: str) -> IntegrationCredential | None:
        """Return the credential, or None when the provider is unknown."""
        result = await self._session.execute(
            select(IntegrationCredentialModel).where(
                IntegrationCredentialModel.provider == provider
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _credential_from_row(row)

    async def add_telegram_update(self, update: TelegramUpdate) -> None:
        """Insert an update id."""
        self._session.add(_telegram_row(update))
        await self._session.flush()

    async def has_telegram_update(self, update_id: int) -> bool:
        """True when this update id was already stored."""
        result = await self._session.execute(
            select(TelegramUpdateModel.update_id).where(
                TelegramUpdateModel.update_id == update_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def _compare_and_set(self, command: TransitionCommand) -> bool:
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == command.run_id,
                AutopilotRunModel.state == command.expected.value,
            )
            .values(
                state=command.new.value,
                state_reason=command.reason,
                updated_at=func.now(),
            )
        )
        matched = cast(CursorResult[object], result).rowcount == 1
        return matched

    async def _emit_state_changed(self, command: TransitionCommand) -> None:
        audit, outbox = build_event_records(_state_changed_record(command))
        self._session.add(audit)
        self._session.add(outbox)
        await self._session.flush()


def _state_changed_record(command: TransitionCommand) -> EventRecord:
    return EventRecord(
        event_id=str(uuid4()),
        event_type=EVENT_TYPE_STATE_CHANGED,
        aggregate_id=str(command.run_id),
        aggregate_type=AGGREGATE_TYPE_AUTOPILOT_RUN,
        version=EVENT_VERSION,
        payload={
            PAYLOAD_PREVIOUS_STATE: command.expected.value,
            PAYLOAD_STATE: command.new.value,
            PAYLOAD_REASON: command.reason,
        },
        metadata={METADATA_MODULE: MODULE_NAME},
        emitted_at=datetime.now(UTC),
    )


def _topic_row(candidate: TopicCandidate) -> TopicCandidateModel:
    return TopicCandidateModel(
        id=candidate.candidate_id,
        title=candidate.title,
        angle=candidate.angle,
        why_viral=candidate.why_viral,
        audience=candidate.audience,
        niche=candidate.niche,
        brief=candidate.brief,
        sources=list(candidate.sources),
        score=candidate.score,
        signal_hash=candidate.signal_hash,
        status=candidate.status,
    )


def _topic_from_row(row: TopicCandidateModel) -> TopicCandidate:
    return TopicCandidate(
        candidate_id=row.id,
        title=row.title,
        angle=row.angle,
        why_viral=row.why_viral,
        audience=row.audience,
        niche=row.niche,
        brief=row.brief,
        sources=tuple(row.sources),
        score=row.score,
        signal_hash=row.signal_hash,
        status=row.status,
    )


def _run_row(run: AutopilotRun) -> AutopilotRunModel:
    return AutopilotRunModel(
        id=run.run_id,
        carousel_project_id=run.carousel_project_id,
        topic_candidate_id=run.topic_candidate_id,
        state=run.state.value,
        state_reason=run.state_reason,
        attempts=run.attempts,
        telegram_message_ids=list(run.telegram_message_ids),
        ig_container_id=run.ig_container_id,
        ig_post_id=run.ig_post_id,
        ig_permalink=run.ig_permalink,
    )


def _run_from_row(row: AutopilotRunModel) -> AutopilotRun:
    return AutopilotRun(
        run_id=row.id,
        topic_candidate_id=row.topic_candidate_id,
        carousel_project_id=row.carousel_project_id,
        state=AutopilotRunState(row.state),
        state_reason=row.state_reason,
        attempts=row.attempts,
        telegram_message_ids=tuple(row.telegram_message_ids),
        ig_container_id=row.ig_container_id,
        ig_post_id=row.ig_post_id,
        ig_permalink=row.ig_permalink,
    )


def _credential_row(credential: IntegrationCredential) -> IntegrationCredentialModel:
    return IntegrationCredentialModel(
        provider=credential.provider,
        encrypted_token=credential.encrypted_token,
        expires_at=credential.expires_at,
        refreshed_at=credential.refreshed_at,
    )


def _credential_from_row(row: IntegrationCredentialModel) -> IntegrationCredential:
    return IntegrationCredential(
        provider=row.provider,
        encrypted_token=row.encrypted_token,
        expires_at=row.expires_at,
        refreshed_at=row.refreshed_at,
    )


def _telegram_row(update: TelegramUpdate) -> TelegramUpdateModel:
    return TelegramUpdateModel(
        update_id=update.update_id, received_at=update.received_at
    )
