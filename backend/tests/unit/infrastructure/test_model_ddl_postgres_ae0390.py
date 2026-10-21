"""Every ORM table compiles to DDL that Postgres can parse.

``server_default=func.false()`` rendered ``DEFAULT false()`` (a call to a
non-existent function), so ``create_all`` on Postgres 16 failed with
``syntax error at or near "("`` in the real-Postgres heartbeat test. Boolean
server defaults must use the ``sqlalchemy.false()`` / ``true()`` literals.
"""

from __future__ import annotations

import importlib
import re

from sqlalchemy import Boolean, Column, MetaData, Table, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from rag_backend.infrastructure.database.config import Base

_MODELS_PACKAGE = "rag_backend.infrastructure.database.models"
_BOOLEAN_CALL = re.compile(r"DEFAULT (?:true|false)\(\)", re.IGNORECASE)


def _boolean_calls(table: Table) -> list[str]:
    ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
    return _BOOLEAN_CALL.findall(ddl)


def test_no_model_renders_a_boolean_default_as_a_function_call() -> None:
    importlib.import_module(_MODELS_PACKAGE)
    offenders = {
        name: calls
        for name, table in Base.metadata.tables.items()
        if (calls := _boolean_calls(table))
    }
    assert offenders == {}


def test_the_check_fires_on_a_seeded_func_false_default() -> None:
    seeded = Table(
        "seeded",
        MetaData(),
        Column("flag", Boolean, server_default=func.false()),
    )
    assert _boolean_calls(seeded) == ["DEFAULT false()"]
