"""Rule-fires test for the autopilot facade-only contract (AE-0180 / QA r1 H5).

A clean tree is not evidence the contract works. This plants a legacy
carousel-service import inside a temporary copy of the autopilot module and asserts
``lint-imports`` exits non-zero on ``autopilot-editorial-facade-only``.

Gherkin: tests/features/autopilot_runner.feature
  Scenario: The autopilot imports editorial code only through its facade
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.modules.autopilot.import_seed import (
    ImportSeed,
    run_seeded_lint,
    source_tree_has,
)

_SEED_PATH = "modules/autopilot/infrastructure/_qa_r1_facade_seed.py"
_CONTRACT_ID = "autopilot-editorial-facade-only"
_CONTRACT_NAME = "autopilot reaches editorial and publishing only through"
_SEEDS = {
    "legacy_service": (
        "from rag_backend.application.services.carousel.provider_errors import (\n"
        "    classify_provider_error,\n"
        ")\n\n_SEEDED = classify_provider_error\n",
        "rag_backend.application.services.carousel.provider_errors",
    ),
    "carousel_orm": (
        "from rag_backend.infrastructure.database.models.carousel import (\n"
        "    CarouselProjectModel,\n"
        ")\n\n_SEEDED = CarouselProjectModel\n",
        "rag_backend.infrastructure.database.models.carousel",
    ),
    "editorial_internal": (
        "from rag_backend.modules.editorial.infrastructure.carousel_automation import (\n"
        "    CarouselAutomationAcl,\n"
        ")\n\n_SEEDED = CarouselAutomationAcl\n",
        "rag_backend.modules.editorial.infrastructure.carousel_automation",
    ),
}


@pytest.mark.parametrize("seed", sorted(_SEEDS))
def test_contract_fires_on_seeded_legacy_import(seed: str, tmp_path: Path) -> None:
    """A seeded legacy or internal import from the autopilot breaks the contract."""
    source, imported = _SEEDS[seed]

    result = run_seeded_lint(
        ImportSeed(relative_path=_SEED_PATH, source=source, contract_id=_CONTRACT_ID),
        tmp_path,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert _CONTRACT_NAME in output
    assert imported in output
    assert not source_tree_has(_SEED_PATH)


def test_contract_passes_on_the_unseeded_copy(tmp_path: Path) -> None:
    """The same run without a forbidden import is clean, so the seed is the cause."""
    clean = "_SEEDED = 1\n"

    result = run_seeded_lint(
        ImportSeed(relative_path=_SEED_PATH, source=clean, contract_id=_CONTRACT_ID),
        tmp_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
