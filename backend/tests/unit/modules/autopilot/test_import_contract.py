"""Rule-fires test for the autopilot public-facade contract (AE-0180 / AE-0350).

A clean tree is not evidence the contract works. This plants an internal
import under ``rag_backend.api`` in a temporary copy of the package and asserts ``lint-imports`` exits non-zero
on ``autopilot-public-facade``.
"""

from __future__ import annotations

from pathlib import Path

from tests.unit.modules.autopilot.import_seed import (
    ImportSeed,
    run_seeded_lint,
    source_tree_has,
)

_SEED_PATH = "api/_ae0350_autopilot_facade_seed.py"
_SEED_SOURCE = (
    "from rag_backend.modules.autopilot.domain.models import AutopilotRun\n"
    "\n"
    "_SEEDED = AutopilotRun\n"
)
_CONTRACT_ID = "autopilot-public-facade"
_CONTRACT_NAME = "autopilot internals are private"


def test_facade_contract_fires_on_seeded_internal_import(tmp_path: Path) -> None:
    """A seeded import of autopilot internals from another module breaks the contract."""
    result = run_seeded_lint(
        ImportSeed(
            relative_path=_SEED_PATH, source=_SEED_SOURCE, contract_id=_CONTRACT_ID
        ),
        tmp_path,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert _CONTRACT_NAME in output
    assert "rag_backend.modules.autopilot.domain.models" in output
    assert not source_tree_has(_SEED_PATH)
