"""Every persisted timestamp column is timezone-aware.

Domain models stamp times with ``domain.clock.utc_now()`` (an aware UTC
datetime). asyncpg rejects an aware value for a ``timestamp without time zone``
parameter, so a naive ``DateTime`` column turns every insert into a 500 on
Postgres (SQLite, used by most tests, does not notice). This guard keeps the
ORM metadata consistent with the clock.

Importing the models package registers every table on ``Base.metadata``.
"""

import importlib

from sqlalchemy import DateTime

from rag_backend.infrastructure.database.config import Base

importlib.import_module("rag_backend.infrastructure.database.models")


def _naive_datetime_columns() -> list[str]:
    return sorted(
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, DateTime) and not column.type.timezone
    )


# Scenario: a naive timestamp column would reject aware domain timestamps.
def test_every_datetime_column_is_timezone_aware() -> None:
    assert _naive_datetime_columns() == []
