"""Rule-fires tests for the backend:openapi-fresh gate (export_openapi.py --check).

The gate fails CI when docs/architecture/openapi.json no longer equals the live
FastAPI schema. A clean-tree pass is not enough: these tests prove a stale or
missing artifact exits 1, and that the gate is wired into gates.sh and CI.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
EXPORTER = REPO_ROOT / "backend" / "scripts" / "export_openapi.py"
GATES = REPO_ROOT / "scripts" / "ci" / "gates.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "backend-quality-gates.yml"
CI_GATE = REPO_ROOT / ".github" / "workflows" / "ci-gate.yml"
ARTIFACT_PATH_FILTER = "- 'docs/architecture/openapi.json'"
GATE_NAME = "backend:openapi-fresh"
EXIT_OK = 0
EXIT_STALE = 1


@pytest.fixture(scope="module")
def exporter() -> ModuleType:
    spec = importlib.util.spec_from_file_location("export_openapi", EXPORTER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_passes_on_a_freshly_exported_artifact(
    exporter: ModuleType, tmp_path: Path
) -> None:
    artifact = tmp_path / "openapi.json"

    assert exporter.main(["--artifact", str(artifact)]) == EXIT_OK
    assert exporter.main(["--check", "--artifact", str(artifact)]) == EXIT_OK


def test_check_fires_on_a_stale_artifact(
    exporter: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artifact = tmp_path / "openapi.json"
    exporter.main(["--artifact", str(artifact)])
    document = json.loads(artifact.read_text(encoding="utf-8"))
    document["components"]["schemas"].popitem()
    artifact.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")

    assert exporter.main(["--check", "--artifact", str(artifact)]) == EXIT_STALE
    assert "stale" in capsys.readouterr().err


def test_check_fires_on_a_missing_artifact(
    exporter: ModuleType, tmp_path: Path
) -> None:
    missing = tmp_path / "absent.json"

    assert exporter.main(["--check", "--artifact", str(missing)]) == EXIT_STALE
    assert not missing.exists()


def test_committed_artifact_is_up_to_date(exporter: ModuleType) -> None:
    assert exporter.main(["--check"]) == EXIT_OK


def test_gate_is_registered_and_runs_in_ci() -> None:
    gates = GATES.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "openapi-fresh:gate_backend_openapi_fresh" in gates
    assert "export_openapi.py --check" in gates
    assert f"bash scripts/ci/gates.sh {GATE_NAME}" in workflow


def test_an_artifact_only_change_triggers_the_gate() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    ci_gate = CI_GATE.read_text(encoding="utf-8")

    assert workflow.count(ARTIFACT_PATH_FILTER) == 2
    assert ci_gate.count(ARTIFACT_PATH_FILTER) == 2
