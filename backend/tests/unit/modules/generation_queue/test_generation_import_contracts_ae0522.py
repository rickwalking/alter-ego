"""Rule-fires tests for the generation queue's import contracts.

A clean tree is not evidence the contracts work: each test plants one violating
import in a temporary copy of the package and asserts ``lint-imports`` fails on
that contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.modules.autopilot.import_seed import (
    ImportSeed,
    run_seeded_lint,
    source_tree_has,
)


@pytest.mark.parametrize(
    ("relative_path", "source", "contract_id", "name"),
    [
        (
            "api/_generation_queue_facade_seed.py",
            "from rag_backend.modules.generation_queue.domain.models import"
            " GenerationRun\n\n_SEEDED = GenerationRun\n",
            "generation-queue-public-facade",
            "generation queue internals are private",
        ),
        (
            "modules/generation_queue/application/_isolation_seed.py",
            "import pgqueuer\n\n_SEEDED = pgqueuer\n",
            "generation-queue-application-isolation",
            "Generation queue application/domain must not import",
        ),
    ],
)
def test_contract_fires_on_a_seeded_violation(
    tmp_path: Path, relative_path: str, source: str, contract_id: str, name: str
) -> None:
    """Scenario: The dispatcher stages and hands over the queued work"""
    result = run_seeded_lint(
        ImportSeed(relative_path=relative_path, source=source, contract_id=contract_id),
        tmp_path,
    )
    assert result.returncode != 0
    assert name in result.stdout + result.stderr
    assert not source_tree_has(relative_path)
