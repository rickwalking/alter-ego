"""Database errors never carry SQL parameter values into logs or tracebacks.

Feature: SQL parameters stay out of logs
  Scenario: a failed parameterized statement omits the values
    Given the app engine
    When a statement with a parameter fails
    Then the error text names the statement but not the parameter value
  Scenario: every engine in the backend hides parameters
    Then each create_async_engine call passes hide_parameters=True
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

import rag_backend.infrastructure.database.config as db_config

SRC = Path(__file__).resolve().parents[3] / "src" / "rag_backend"
SECRET = "top-secret-document-content"


# Scenario: a failed parameterized statement omits the values
async def test_failed_statement_error_omits_parameter_values(tmp_path: Path) -> None:
    previous = db_config.c_engine
    db_config.c_engine = None
    await db_config.init_db(f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")
    engine = db_config.c_engine
    assert engine is not None
    try:
        with pytest.raises(OperationalError) as caught:
            async with engine.begin() as conn:
                await conn.execute(
                    text("INSERT INTO no_such_table VALUES (:body)"), {"body": SECRET}
                )
    finally:
        await engine.dispose()
        db_config.c_engine = previous

    message = str(caught.value)
    assert "no_such_table" in message
    assert SECRET not in message
    assert "hide_parameters=True" in message


def _engine_calls(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "create_async_engine"
    ]


def _hides_parameters(call: ast.Call) -> bool:
    return any(
        keyword.arg == "hide_parameters"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
        for keyword in call.keywords
    )


# Scenario: every engine in the backend hides parameters
def test_every_engine_hides_parameters() -> None:
    calls = [
        (path.name, call) for path in SRC.rglob("*.py") for call in _engine_calls(path)
    ]

    assert len(calls) >= 5
    for name, call in calls:
        assert _hides_parameters(call), name
