"""The queue schema one-shot compiles the events DDL in a bare deploy process."""

from __future__ import annotations

import subprocess  # noqa: S404  # integrity-ok: a bare interpreter is the only way to load no other model
import sys

_COMPILE_IN_A_BARE_PROCESS = (
    "from sqlalchemy.dialects import postgresql\n"
    "from rag_backend.modules.generation_queue.infrastructure.schema import "
    "generation_events_ddl\n"
    "print(generation_events_ddl(postgresql.dialect())[0])\n"
)


def test_events_ddl_compiles_in_a_process_that_loaded_no_other_model() -> None:
    """Scenario: The events DDL compiles in a process that loaded no other model"""
    result = subprocess.run(  # noqa: S603  # integrity-ok: fixed interpreter, constant script
        [sys.executable, "-c", _COMPILE_IN_A_BARE_PROCESS],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "NoReferencedTableError" not in result.stderr
    assert "REFERENCES carousel_projects (id) ON DELETE CASCADE" in result.stdout
    assert "REFERENCES generation_runs (id) ON DELETE CASCADE" in result.stdout
