"""Rule-fires test for the autopilot facade-only contract (AE-0180 / QA r1 H5).

A clean tree is not evidence the contract works. This plants a legacy
carousel-service import inside the autopilot module and asserts
``lint-imports`` exits non-zero on ``autopilot-editorial-facade-only``.

Gherkin: tests/features/autopilot_runner.feature
  Scenario: The autopilot imports editorial code only through its facade
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[4]
_PACKAGE = _BACKEND / "src" / "rag_backend" / "modules" / "autopilot" / "infrastructure"
_SEED_NAME = "_qa_r1_facade_seed"
_SEED = _PACKAGE / f"{_SEED_NAME}.py"
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


def _remove_seed() -> None:
    _SEED.unlink(missing_ok=True)
    for compiled in (_PACKAGE / "__pycache__").glob(f"{_SEED_NAME}*"):
        compiled.unlink(missing_ok=True)
    shutil.rmtree(_BACKEND / ".grimp_cache", ignore_errors=True)


@pytest.mark.parametrize("seed", sorted(_SEEDS))
def test_contract_fires_on_seeded_legacy_import(seed: str) -> None:
    """A seeded legacy or internal import from the autopilot breaks the contract."""
    source, imported = _SEEDS[seed]
    _remove_seed()
    _SEED.write_text(source, encoding="utf-8")
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
    assert imported in output
