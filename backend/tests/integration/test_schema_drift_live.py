"""Live-DB integration tests for the schema-drift detector (AE-0207).

Gherkin not applicable — this is the DevOps schema-vs-models safety net, exercised
against a REAL Postgres instance (the drift detector reads ``information_schema``,
a Postgres feature SQLite does not implement the same way). Proves the exact class
that 500'd prod twice: a mapped ORM column missing from the live schema FAILS the
check, and a matching schema PASSES.

Requires a Postgres ``DATABASE_URL`` (the CI ``postgres`` service / a local
override). SKIPs when absent — mirrors the Postgres-dependent gates in
``scripts/ci/gates.sh`` so a developer without a DB is not blocked.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, text

from rag_backend.infrastructure.database.check_drift_cli import to_sync_url
from rag_backend.infrastructure.database.schema_drift import check_schema_drift

_TABLE = "ae0207_drift_probe"
_ID = "id"
_NAME = "name"
_NEW_COL = "origin"  # the real prod failure class: a model column DB never got

_async_url = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not _async_url or "postgresql" not in _async_url,
    reason="schema-drift live test needs a Postgres DATABASE_URL",
)


def _probe_metadata(columns: tuple[str, ...]) -> MetaData:
    metadata = MetaData()
    Table(
        _TABLE,
        metadata,
        *[Column(name, Integer if name == _ID else String) for name in columns],
    )
    return metadata


@pytest.fixture
def pg_engine():
    """A sync Postgres engine with the probe table created and torn down."""
    engine = create_engine(to_sync_url(_async_url or ""))
    create_metadata = _probe_metadata((_ID, _NAME))
    create_metadata.create_all(engine)
    yield engine
    create_metadata.drop_all(engine)
    engine.dispose()


# Scenario: live schema matches the mapped ORM columns -> no drift.
def test_matching_live_schema_passes(pg_engine) -> None:
    report = check_schema_drift(pg_engine, _probe_metadata((_ID, _NAME)))

    assert report.has_drift is False


# Scenario: model gains a column the live DB never got (no migration / not applied)
#           -> drift detected (the exact prod failure: caption_en/origin/distribution).
def test_mapped_column_missing_from_live_db_fails(pg_engine) -> None:
    # Simulate the live DB lacking a freshly added model column by dropping it.
    with pg_engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {_TABLE} DROP COLUMN {_NAME}"))

    # The ORM now maps an extra column the live schema does not have.
    report = check_schema_drift(pg_engine, _probe_metadata((_ID, _NAME, _NEW_COL)))

    assert report.has_drift is True
    missing = {item.column for item in report.missing if item.table == _TABLE}
    assert {_NAME, _NEW_COL} <= missing
