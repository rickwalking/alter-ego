"""Schema-vs-models drift detection (AE-0207).

Production was bootstrapped via SQLAlchemy ``create_all`` and never ran Alembic.
``create_all`` creates *missing tables* but NEVER ``ALTER``s an existing one, so a
column added to an ORM model after the table already existed silently 500s prod
the first time it is referenced (hit live twice: ``carousel_projects.caption_en``
and ``blog_posts.origin``/``distribution``).

This module compares the mapped ``Base.metadata`` columns against the columns the
live database actually reports via ``information_schema.columns`` and FAILS when a
mapped column is absent. It is the exact-class detector for "model column with no
migration / migration not applied". It is wired as the ``schema-drift`` backend
gate (``scripts/ci/gates.sh``) and runs on deploy before the app serves traffic.

Pure comparison logic (``find_missing_columns``) is separated from I/O so it can
be unit-tested without a database; the DB-touching path is covered by an
integration test against a real Postgres instance.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import Engine, MetaData, text

# information_schema query: the public-schema columns the live DB actually has.
_INFORMATION_SCHEMA_QUERY = text(
    """
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
    """
)

# Message fragments (no magic strings).
_MSG_NO_DRIFT = "OK: live schema matches all mapped ORM columns."
_MSG_MISSING_TABLE = "table absent from live DB"
_MSG_COLUMN_ABSENT = "column absent"
_MSG_DRIFT_HEADER = (
    "Schema drift: mapped ORM columns are missing from the live database. "
    "A migration is missing or has not been applied (AE-0207)."
)


@dataclass(frozen=True)
class MissingColumn:
    """A mapped ORM column that the live database does not have."""

    table: str
    column: str
    reason: str


@dataclass(frozen=True)
class DriftReport:
    """Result of comparing mapped ORM columns against the live schema."""

    missing: tuple[MissingColumn, ...] = field(default_factory=tuple)

    @property
    def has_drift(self) -> bool:
        """True when at least one mapped column is absent from the live DB."""
        return len(self.missing) > 0

    def render(self) -> str:
        """Human-readable, deploy/CI-log-friendly summary."""
        if not self.has_drift:
            return _MSG_NO_DRIFT
        lines = [_MSG_DRIFT_HEADER]
        lines.extend(
            f"  - {item.table}.{item.column} ({item.reason})" for item in self.missing
        )
        return "\n".join(lines)


def expected_columns(metadata: MetaData) -> dict[str, frozenset[str]]:
    """Map each mapped table name to the set of its mapped column names."""
    return {
        table.name: frozenset(column.name for column in table.columns)
        for table in metadata.sorted_tables
    }


def find_missing_columns(
    expected: Mapping[str, frozenset[str]],
    actual: Mapping[str, frozenset[str]],
) -> DriftReport:
    """Compare expected (ORM) columns against actual (live DB) columns.

    A table that the ORM maps but the DB lacks entirely is reported as every one
    of its columns being missing with the table-absent reason — that is the same
    failure class (the app will 500 on first reference) and must block.
    """
    missing: list[MissingColumn] = []
    for table_name in sorted(expected):
        expected_cols = expected[table_name]
        actual_cols = actual.get(table_name)
        if actual_cols is None:
            missing.extend(
                MissingColumn(table_name, column, _MSG_MISSING_TABLE)
                for column in sorted(expected_cols)
            )
            continue
        missing.extend(
            MissingColumn(table_name, column, _MSG_COLUMN_ABSENT)
            for column in sorted(expected_cols - actual_cols)
        )
    return DriftReport(missing=tuple(missing))


def reflect_live_columns(engine: Engine) -> dict[str, frozenset[str]]:
    """Read the live ``public``-schema columns via ``information_schema``."""
    grouped: dict[str, set[str]] = {}
    with engine.connect() as connection:
        for table_name, column_name in connection.execute(_INFORMATION_SCHEMA_QUERY):
            grouped.setdefault(table_name, set()).add(column_name)
    return {name: frozenset(cols) for name, cols in grouped.items()}


def check_schema_drift(engine: Engine, metadata: MetaData) -> DriftReport:
    """Compare ``metadata``'s mapped columns against the engine's live schema."""
    expected = expected_columns(metadata)
    actual = reflect_live_columns(engine)
    return find_missing_columns(expected, actual)
