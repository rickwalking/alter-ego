"""The drift-check CLI opens its engine with SQL parameters hidden.

Feature: knowledge_error_detail_ae0452.feature
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine

from rag_backend.infrastructure.database import check_drift_cli
from rag_backend.infrastructure.database.schema_drift import DriftReport

_EXIT_OK = 0


def _no_drift(engine: Engine, metadata: MetaData) -> DriftReport:
    return DriftReport()


# Scenario: every engine in the backend hides parameters
def test_drift_check_engine_hides_parameters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[dict[str, object]] = []

    def recording_create_engine(url: str, **kwargs: bool) -> Engine:
        opened.append({"url": url, **kwargs})
        return create_engine(url, **kwargs)

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'empty.db'}")
    monkeypatch.setattr(check_drift_cli, "create_engine", recording_create_engine)
    monkeypatch.setattr(check_drift_cli, "check_schema_drift", _no_drift)

    assert check_drift_cli.main() == _EXIT_OK
    assert opened == [
        {"url": f"sqlite:///{tmp_path / 'empty.db'}", "hide_parameters": True}
    ]
