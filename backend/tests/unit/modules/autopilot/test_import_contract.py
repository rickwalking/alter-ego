"""Rule-fires test for the autopilot public-facade contract (AE-0180 / AE-0350).

A clean tree is not evidence the contract works. This plants an internal
import under ``rag_backend.api`` and asserts ``lint-imports`` exits non-zero
on ``autopilot-public-facade``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[4]
_SEED = (
    _BACKEND
    / "src"
    / "rag_backend"
    / "api"
    / "_ae0350_autopilot_facade_seed.py"
)
_SEED_SOURCE = (
    "from rag_backend.modules.autopilot.domain.models import AutopilotRun\n"
    "\n"
    "_SEEDED = AutopilotRun\n"
)
_CONTRACT_NAME = "autopilot internals are private"


def _remove_seed() -> None:
    _SEED.unlink(missing_ok=True)
    cache = _SEED.parent / "__pycache__"
    for compiled in cache.glob("_ae0350_autopilot_facade_seed*"):
        compiled.unlink(missing_ok=True)
    shutil.rmtree(_BACKEND / ".grimp_cache", ignore_errors=True)


def test_facade_contract_fires_on_seeded_internal_import() -> None:
    """A seeded import of autopilot internals from another module breaks the contract."""
    _remove_seed()
    _SEED.write_text(_SEED_SOURCE, encoding="utf-8")
    try:
        result = subprocess.run(
            ["uv", "run", "lint-imports"],
            cwd=_BACKEND,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        _remove_seed()

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert _CONTRACT_NAME in output
    assert "rag_backend.modules.autopilot.domain.models" in output
