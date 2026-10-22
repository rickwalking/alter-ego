"""Database errors never carry SQL parameter values into logs or tracebacks.

Feature: knowledge_error_detail_ae0452.feature
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

import rag_backend.infrastructure.database.config as db_config

BACKEND = Path(__file__).resolve().parents[2]
ENGINE_SCAN_ROOTS = tuple(BACKEND / name for name in ("src", "scripts", "alembic"))
ENGINE_FACTORIES = frozenset({"create_engine", "create_async_engine"})
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


def _called_name(call: ast.Call) -> str | None:
    """The called function's name, for ``f(...)`` and ``module.f(...)`` alike."""
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _engine_calls(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _called_name(node) in ENGINE_FACTORIES
    ]


def _unhidden_engines(roots: tuple[Path, ...]) -> list[str]:
    """``<file>:<line>`` of every engine factory call without hide_parameters=True."""
    return [
        f"{path}:{call.lineno}"
        for root in roots
        for path in sorted(root.rglob("*.py"))
        for call in _engine_calls(path)
        if not _hides_parameters(call)
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
        call
        for root in ENGINE_SCAN_ROOTS
        for path in root.rglob("*.py")
        for call in _engine_calls(path)
    ]

    assert len(calls) >= 8
    assert _unhidden_engines(ENGINE_SCAN_ROOTS) == []


# Scenario: every engine in the backend hides parameters
@pytest.mark.parametrize(
    "source",
    [
        "from sqlalchemy import create_engine\nengine = create_engine(url)\n",
        "import sqlalchemy\nengine = sqlalchemy.create_engine(url)\n",
        "from sqlalchemy.ext.asyncio import create_async_engine\n"
        "engine = create_async_engine(url, hide_parameters=False)\n",
    ],
)
def test_an_engine_without_hide_parameters_is_reported(
    tmp_path: Path, source: str
) -> None:
    (tmp_path / "seeded.py").write_text(source, encoding="utf-8")

    assert _unhidden_engines((tmp_path,)) == [f"{tmp_path / 'seeded.py'}:2"]
