"""SQL store for boost requests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.boost_constants import (
    ACTOR_BOT,
    OPEN_STATUSES,
    STATUS_PENDING,
    UNCOMMITTED_STATUSES,
)
from rag_backend.modules.autopilot.domain.boost import (
    BoostAudience,
    BoostListQuery,
    BoostRequest,
    IllegalBoostTransitionError,
    MediaEligibility,
    StatusSave,
)
from rag_backend.modules.autopilot.domain.boost_state import assert_transition
from rag_backend.modules.autopilot.domain.ig_media import OpenBoost
from rag_backend.modules.autopilot.infrastructure.boost_models import (
    BoostEventModel,
    BoostRequestModel,
)
from rag_backend.modules.autopilot.infrastructure.insights_models import IgMediaModel
from rag_backend.modules.autopilot.infrastructure.run_mapping import aware

_EMPTY = MediaEligibility(posted_at=None, product_type=None, permalink=None)


class SqlBoostStore:
    """``BoostStore`` on one session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def by_key(self, key: str) -> BoostRequest | None:
        row = await self._session.scalar(
            select(BoostRequestModel).where(BoostRequestModel.idempotency_key == key)
        )
        return None if row is None else _request(row)

    async def get(self, request_id: UUID) -> BoostRequest | None:
        row = await self._session.get(BoostRequestModel, request_id)
        return None if row is None else _request(row)

    async def media(self, media_id: str) -> MediaEligibility:
        row = await self._session.get(IgMediaModel, media_id)
        if row is None:
            return _EMPTY
        posted = aware(row.posted_at)
        return MediaEligibility(
            posted_at=posted,
            product_type=row.media_product_type,
            permalink=row.permalink,
        )

    async def open_exists(self, media_id: str) -> bool:
        found = await self._session.scalar(
            select(BoostRequestModel.id)
            .where(
                BoostRequestModel.media_id == media_id,
                BoostRequestModel.status.in_(tuple(OPEN_STATUSES)),
            )
            .limit(1)
        )
        return found is not None

    async def pending_count(self) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(BoostRequestModel)
            .where(BoostRequestModel.status == STATUS_PENDING)
        )
        return int(count or 0)

    async def committed_cents(self, since: datetime) -> int:
        total = await self._session.scalar(
            select(
                func.coalesce(func.sum(BoostRequestModel.total_budget_cents), 0)
            ).where(
                BoostRequestModel.created_at >= since,
                BoostRequestModel.status.notin_(tuple(UNCOMMITTED_STATUSES)),
            )
        )
        return int(total or 0)

    async def insert(self, request: BoostRequest) -> None:
        self._session.add(_model(request))
        self._session.add(_event(_recorded(request)))
        await self._session.flush()

    async def save_status(self, change: StatusSave) -> None:
        row = await self._session.get(BoostRequestModel, change.request.id)
        if row is None or row.status != change.previous:
            raise IllegalBoostTransitionError(change.previous, change.request.status)
        assert_transition(change.previous, change.request.status)
        _copy(row, change.request)
        self._session.add(
            _event(_recorded(change.request, change.previous, change.actor))
        )
        await self._session.flush()

    async def list_requests(self, query: BoostListQuery) -> list[BoostRequest]:
        stmt = select(BoostRequestModel).order_by(BoostRequestModel.created_at.desc())
        if query.statuses:
            stmt = stmt.where(BoostRequestModel.status.in_(query.statuses))
        if query.media_id is not None:
            stmt = stmt.where(BoostRequestModel.media_id == query.media_id)
        rows = await self._session.scalars(stmt.limit(query.limit))
        return [_request(row) for row in rows]

    async def open_for(self, media_ids: tuple[str, ...]) -> dict[str, OpenBoost]:
        if not media_ids:
            return {}
        rows = await self._session.scalars(
            select(BoostRequestModel)
            .where(
                BoostRequestModel.media_id.in_(media_ids),
                BoostRequestModel.status.in_(tuple(OPEN_STATUSES)),
            )
            .order_by(BoostRequestModel.created_at.desc())
        )
        found: dict[str, OpenBoost] = {}
        for row in rows:
            found.setdefault(
                row.media_id,
                OpenBoost(request_id=str(row.id), status=row.status),
            )
        return found

    async def commit(self) -> None:
        await self._session.commit()

    async def remember_message(self, request_id: UUID, message_id: int) -> None:
        row = await self._session.get(BoostRequestModel, request_id)
        if row is None:
            return
        row.telegram_message_id = message_id
        await self._session.flush()


def _model(request: BoostRequest) -> BoostRequestModel:
    return BoostRequestModel(
        id=request.id,
        idempotency_key=request.idempotency_key,
        request_hash=request.request_hash,
        media_id=request.media_id,
        status=request.status,
        objective=request.objective,
        daily_budget_cents=request.daily_budget_cents,
        days=request.days,
        total_budget_cents=request.total_budget_cents,
        currency=request.currency,
        audience=_audience_out(request.audience),
        reason=request.reason,
        score=request.score,
        created_at=request.created_at,
        expires_at=request.expires_at,
        permalink=request.permalink,
        starts_at=request.starts_at,
        launch_attempts=request.launch_attempts,
        updated_at=request.created_at,
    )


def _copy(row: BoostRequestModel, request: BoostRequest) -> None:
    row.status = request.status
    row.decided_at = request.decided_at
    row.decided_by = request.decided_by
    row.telegram_message_id = request.telegram_message_id
    row.starts_at = request.starts_at
    row.ends_at = request.ends_at
    row.meta_campaign_id = request.meta_campaign_id
    row.meta_adset_id = request.meta_adset_id
    row.meta_creative_id = request.meta_creative_id
    row.meta_ad_id = request.meta_ad_id
    row.launch_attempts = request.launch_attempts
    row.next_attempt_at = request.next_attempt_at
    row.last_insights = request.last_insights
    row.error_code = request.error_code
    row.updated_at = request.decided_at or request.created_at


def _request(row: BoostRequestModel) -> BoostRequest:
    created = aware(row.created_at) or row.created_at
    expires = aware(row.expires_at) or row.expires_at
    return BoostRequest(
        id=row.id,
        idempotency_key=row.idempotency_key,
        request_hash=row.request_hash,
        media_id=row.media_id,
        status=row.status,
        objective=row.objective,
        daily_budget_cents=row.daily_budget_cents,
        days=row.days,
        total_budget_cents=row.total_budget_cents,
        currency=row.currency,
        audience=_audience_in(row.audience),
        reason=row.reason,
        score=row.score,
        created_at=created,
        expires_at=expires,
        decided_at=aware(row.decided_at),
        decided_by=row.decided_by,
        telegram_message_id=row.telegram_message_id,
        permalink=row.permalink,
        starts_at=aware(row.starts_at),
        ends_at=aware(row.ends_at),
        meta_campaign_id=row.meta_campaign_id,
        meta_adset_id=row.meta_adset_id,
        meta_creative_id=row.meta_creative_id,
        meta_ad_id=row.meta_ad_id,
        launch_attempts=row.launch_attempts,
        next_attempt_at=aware(row.next_attempt_at),
        last_insights=row.last_insights,
        error_code=row.error_code,
    )


def _event(recorded: _Recorded) -> BoostEventModel:
    return BoostEventModel(
        request_id=recorded.request.id,
        at=recorded.at,
        from_status=recorded.previous,
        to_status=recorded.request.status,
        actor=recorded.actor,
        detail={"error_code": recorded.request.error_code or ""},
    )


@dataclass(frozen=True, kw_only=True)
class _Recorded:
    request: BoostRequest
    previous: str
    actor: str
    at: datetime


def _recorded(
    request: BoostRequest, previous: str = "", actor: str = ACTOR_BOT
) -> _Recorded:
    return _Recorded(
        request=request,
        previous=previous,
        actor=actor,
        at=request.decided_at or request.created_at,
    )


def _audience_out(audience: BoostAudience) -> dict[str, object]:
    return {
        "countries": list(audience.countries),
        "age_min": audience.age_min,
        "age_max": audience.age_max,
    }


def _audience_in(raw: dict[str, object]) -> BoostAudience:
    countries = raw.get("countries")
    names: tuple[str, ...] = ()
    if isinstance(countries, list):
        names = tuple(item for item in countries if isinstance(item, str))
    return BoostAudience(
        countries=names,
        age_min=_int(raw.get("age_min")),
        age_max=_int(raw.get("age_max")),
    )


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


__all__ = ["SqlBoostStore"]
