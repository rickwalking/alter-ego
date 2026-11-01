"""The failure event keeps Meta's error details on real Postgres (JSONB ``detail``).

Gherkin: tests/features/boost_meta_payload_ae0591.feature
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.boost_constants import (
    ACTOR_WORKER,
    STATUS_FAILED,
    STATUS_LAUNCHING,
    STATUS_PENDING,
)
from rag_backend.modules.autopilot.domain.boost import (
    BoostAudience,
    BoostRequest,
    StatusSave,
)
from rag_backend.modules.autopilot.infrastructure.boost_models import (
    BoostEventModel,
    BoostRequestModel,
)
from rag_backend.modules.autopilot.infrastructure.boost_store import SqlBoostStore
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_TABLES = ("ig_media", "boost_requests", "boost_request_events")
_DETAIL = {
    "call": "creative",
    "http_status": "400",
    "code": "100",
    "error_subcode": "1885183",
    "type": "OAuthException",
    "message": "Invalid parameter",
    "error_user_title": "Ads creative post was created by an app that is in development mode",
    "error_user_msg": "It must be in public to create this ad.",
    "fbtrace_id": "AbCdEf123",
}


def _pending() -> BoostRequest:
    now = datetime.now(UTC)
    return BoostRequest(
        id=uuid4(),
        idempotency_key="media-20261101",
        request_hash="hash",
        media_id="18034567890123456",
        status=STATUS_PENDING,
        objective="engagement",
        daily_budget_cents=2000,
        days=1,
        total_budget_cents=2000,
        currency="BRL",
        audience=BoostAudience(countries=("BR",), age_min=18, age_max=65),
        reason="Alcance acima da mediana da conta",
        score=1.6,
        created_at=now,
        expires_at=now + timedelta(hours=12),
    )


async def _fail(session: AsyncSession, request: BoostRequest) -> None:
    store = SqlBoostStore(session)
    await store.insert(request)
    await session.execute(
        BoostRequestModel.__table__
        .update()
        .where(BoostRequestModel.id == request.id)
        .values(status=STATUS_LAUNCHING)
    )
    failed = replace(
        request,
        status=STATUS_FAILED,
        error_code="meta_app_dev_mode",
        error_detail=_DETAIL,
        decided_at=request.created_at + timedelta(minutes=5),
    )
    await store.save_status(
        StatusSave(previous=STATUS_LAUNCHING, request=failed, actor=ACTOR_WORKER)
    )
    await store.commit()


@requires_postgres
async def test_failure_event_on_postgres_stores_meta_error_details() -> None:
    """Scenario: The failure event on Postgres stores Meta's error details"""
    request = _pending()
    async with isolated_schema(_TABLES) as engine:
        async with AsyncSession(engine) as session:
            await _fail(session, request)
        async with AsyncSession(engine) as session:
            events = (
                await session.scalars(
                    select(BoostEventModel)
                    .where(BoostEventModel.request_id == request.id)
                    .order_by(BoostEventModel.id)
                )
            ).all()
            row = await session.get(BoostRequestModel, request.id)

    assert row is not None
    assert row.error_code == "meta_app_dev_mode"
    assert [event.to_status for event in events] == [STATUS_PENDING, STATUS_FAILED]
    assert events[0].detail == {"error_code": ""}
    assert events[-1].detail == {**_DETAIL, "error_code": "meta_app_dev_mode"}
