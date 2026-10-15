"""SQLAlchemy adapter for autopilot persistence.

``transition`` is one conditional update plus one outbox row. The caller commits.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import CursorResult, Update, func, select, update
from sqlalchemy.exc import IntegrityError
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
from rag_backend.modules.autopilot.domain.gate import (
    AttachProjectCommand,
    StartAttemptCommand,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    IntegrationCredential,
    TelegramUpdate,
    ThesisConfirmCommand,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.publish import (
    PublishAttemptCommand,
    RunListQuery,
    SaveContainerCommand,
    SavePostCommand,
)
from rag_backend.modules.autopilot.domain.state_machine import assert_allowed
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    IntegrationCredentialModel,
    TelegramUpdateModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.infrastructure.run_mapping import (
    run_from_row,
    run_row,
)


class SqlAlchemyAutopilotRepository:
    """Session-scoped adapter. Structurally implements the four ports."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, run: AutopilotRun) -> None:
        """Insert a run. The topic row must already exist."""
        self._session.add(run_row(run))
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
        return run_from_row(row)

    async def transition(self, command: TransitionCommand) -> bool:
        """CAS the state. Illegal pairs raise; a stale expected state returns False."""
        assert_allowed(command.pair())
        if not await self._compare_and_set(command):
            return False
        await self._emit_state_changed(command)
        return True

    async def confirm_thesis(self, command: ThesisConfirmCommand) -> bool:
        """AE-0377: store the owner's thesis and requeue, in one CAS."""
        transition = TransitionCommand(
            run_id=command.run_id,
            expected=AutopilotRunState.AWAITING_THESIS,
            new=AutopilotRunState.QUEUED,
            reason=command.reason,
        )
        assert_allowed(transition.pair())
        statement = _transition_statement(transition).values(pov_thesis=command.thesis)
        result = await self._session.execute(statement)
        if cast(CursorResult[object], result).rowcount != 1:
            return False
        await self._emit_state_changed(transition)
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

    async def find_by_carousel(self, project_id: str) -> AutopilotRun | None:
        """Return the run linked to this carousel project, or None."""
        result = await self._session.execute(
            select(AutopilotRunModel)
            .where(AutopilotRunModel.carousel_project_id == project_id)
            .execution_options(populate_existing=True)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return run_from_row(row)

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        """Return the oldest runs in ``query.state``, capped by ``query.limit``."""
        result = await self._session.execute(
            select(AutopilotRunModel)
            .where(AutopilotRunModel.state == query.state.value)
            .order_by(AutopilotRunModel.updated_at.asc())
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        return [run_from_row(row) for row in result.scalars().all()]

    async def save_container(self, command: SaveContainerCommand) -> bool:
        """Store the container id. Refuses the write once a post id exists."""
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == command.run_id,
                AutopilotRunModel.state == AutopilotRunState.PUBLISHING.value,
                AutopilotRunModel.ig_post_id.is_(None),
            )
            .values(
                ig_container_id=command.container_id,
                ig_container_created_at=command.created_at,
                updated_at=command.created_at,
            )
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def save_post(self, command: SavePostCommand) -> bool:
        """Store the media id. A null permalink does not clear one already stored."""
        if command.ig_permalink is None:
            return await self._write_post_id(command)
        return await self._write_post_and_permalink(command)

    async def _write_post_id(self, command: SavePostCommand) -> bool:
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == command.run_id,
                AutopilotRunModel.state == AutopilotRunState.PUBLISHING.value,
            )
            .values(ig_post_id=command.ig_post_id)
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def _write_post_and_permalink(self, command: SavePostCommand) -> bool:
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == command.run_id,
                AutopilotRunModel.state == AutopilotRunState.PUBLISHING.value,
            )
            .values(
                ig_post_id=command.ig_post_id,
                ig_permalink=command.ig_permalink,
            )
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def record_attempt(self, command: PublishAttemptCommand) -> bool:
        """Remember a transient failure so the next tick waits out the backoff."""
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == command.run_id,
                AutopilotRunModel.state == AutopilotRunState.PUBLISHING.value,
            )
            .values(
                publish_attempts=command.attempts,
                state_reason=command.reason,
                updated_at=command.at,
            )
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def attach_project(self, command: AttachProjectCommand) -> bool:
        """Store the carousel id while the run is still queued, then commit."""
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == command.run_id,
                AutopilotRunModel.state == AutopilotRunState.QUEUED.value,
                AutopilotRunModel.carousel_project_id.is_(None),
            )
            .values(carousel_project_id=command.project_id)
        )
        matched = cast(CursorResult[object], result).rowcount == 1
        if matched:
            await self._session.commit()
        return matched

    async def note_start_attempt(self, command: StartAttemptCommand) -> bool:
        """Count a failed start. The run stays queued."""
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == command.run_id,
                AutopilotRunModel.state == AutopilotRunState.QUEUED.value,
            )
            .values(start_attempts=command.attempts, state_reason=command.reason)
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def commit(self) -> None:
        """Commit so a crash after container creation can reuse that container."""
        await self._session.commit()

    async def claim_update(self, update: TelegramUpdate) -> bool:
        """Insert the update id. False when it is already stored."""
        try:
            async with self._session.begin_nested():
                self._session.add(_telegram_row(update))
                await self._session.flush()
        except IntegrityError:
            return False
        return True

    async def has_telegram_update(self, update_id: int) -> bool:
        """True when this update id was already stored."""
        result = await self._session.execute(
            select(TelegramUpdateModel.update_id).where(
                TelegramUpdateModel.update_id == update_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def _compare_and_set(self, command: TransitionCommand) -> bool:
        result = await self._session.execute(_transition_statement(command))
        matched = cast(CursorResult[object], result).rowcount == 1
        return matched

    async def _emit_state_changed(self, command: TransitionCommand) -> None:
        audit, outbox = build_event_records(_state_changed_record(command))
        self._session.add(audit)
        self._session.add(outbox)
        await self._session.flush()


def _transition_statement(command: TransitionCommand) -> Update:
    """Entering ``publishing`` restarts the publish retry budget (QA r1 B2/B3)."""
    statement = (
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
    if command.new is AutopilotRunState.PUBLISHING:
        return statement.values(publish_attempts=0)
    return statement


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
        image_style=candidate.image_style,
        image_guidance=candidate.image_guidance,
        content_mode=candidate.content_mode,
        thesis_draft=candidate.thesis_draft,
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
        image_style=row.image_style,
        image_guidance=row.image_guidance,
        content_mode=row.content_mode,
        thesis_draft=row.thesis_draft,
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
