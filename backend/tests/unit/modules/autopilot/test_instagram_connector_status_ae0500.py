"""The connector block of the instagram insights report.

Feature: instagram_insights.feature (connector-status scenarios)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from rag_backend.modules.autopilot.domain.insights import (
    ConnectorStatusQuery,
    InsightMetrics,
    InsightSnapshot,
    PostInsightsRow,
    PublishedPost,
    connector_status,
)
from rag_backend.modules.autopilot.insights_constants import CHANNEL_INSTAGRAM

_MEDIA = "17900000000000001"
_NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def _row(fetched_at: datetime | None, *, stale: bool = False) -> PostInsightsRow:
    snapshot = (
        InsightSnapshot(
            media_id=_MEDIA, metrics=InsightMetrics(views=10), fetched_at=fetched_at
        )
        if fetched_at
        else None
    )
    return PostInsightsRow(
        post=PublishedPost(media_id=_MEDIA),
        metrics=snapshot.metrics if snapshot else InsightMetrics(),
        fetched_at=fetched_at,
        stale=stale,
    )


def _status(
    rows: list[PostInsightsRow], *, configured: bool = True, error: str | None = None
) -> None:
    return connector_status(
        ConnectorStatusQuery(
            channel=CHANNEL_INSTAGRAM,
            configured=configured,
            rows=rows,
            now=_NOW,
            refresh_error=error,
        )
    )


def test_last_sync_is_the_newest_fetched_at() -> None:
    """Scenario: The connector block reports the last sync."""
    connector = _status([
        _row(_NOW - timedelta(hours=2)),
        _row(_NOW - timedelta(hours=1)),
    ])

    assert connector.channel == "instagram"
    assert connector.configured is True
    assert connector.last_sync_at == _NOW - timedelta(hours=1)
    assert connector.stale is False
    assert connector.error is None


def test_stale_connector_reports_error_and_last_sync() -> None:
    """Scenario: A stale connector says when it last synced."""
    connector = _status(
        [_row(_NOW - timedelta(hours=8), stale=True)], error="graph_unavailable"
    )

    assert connector.stale is True
    assert connector.last_sync_at == _NOW - timedelta(hours=8)
    assert connector.error == "graph_unavailable"


def test_unconfigured_connector_keeps_the_stored_last_sync() -> None:
    """Scenario: An unconfigured connector is named instead of zeros."""
    connector = _status([_row(_NOW - timedelta(hours=2))], configured=False)

    assert connector.configured is False
    assert connector.stale is False
    assert connector.last_sync_at == _NOW - timedelta(hours=2)


def test_connector_without_any_sync_is_not_stale_but_has_no_last_sync() -> None:
    """Scenario: A published post whose metrics were never fetched has nothing to date yet."""
    connector = _status([_row(None)])

    assert connector.last_sync_at is None
    assert connector.stale is False
