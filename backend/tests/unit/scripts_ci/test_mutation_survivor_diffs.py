"""The CI mutation job prints and saves the diff of every surviving mutant.

    Feature: surviving mutants are reviewable from CI
      Scenario: CI writes the diff of each surviving mutant
        Given mutmut results list two survived mutants and one killed mutant
        When the survivor report runs in CI
        Then both survivor diffs are printed and saved, and the killed one is not
      Scenario: the survivor report never runs mutmut locally
        Given GITHUB_ACTIONS is not "true"
        When the survivor report runs
        Then it exits 77 and mutmut is never invoked
      Scenario: the backend workflow publishes the survivor report
        Then the mutation job runs the report and uploads it as an artifact

No real mutmut runs here: `uv` is a stub on PATH that answers `mutmut results`
and `mutmut show` from fixed text and records every call.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # noqa: S404  # integrity-ok: a test for a bash CI script must invoke a subprocess (mirrors test_mutation_ci_only.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "mutation-survivor-diffs.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "backend-quality-gates.yml"
BASH = shutil.which("bash") or "bash"

_RESULTS = (
    "    rag_backend.a.x_f__mutmut_1: survived\n"
    "    rag_backend.a.x_f__mutmut_2: killed\n"
    "    rag_backend.b.x_g__mutmut_7: survived\n"
)
_STUB = """#!/usr/bin/env bash
echo "uv $*" >> "{marker}"
if [[ "$3" == "results" ]]; then printf '%s' "{results}"; exit 0; fi
if [[ "$3" == "show" ]]; then echo "--- diff of $4"; exit 0; fi
exit 0
"""


def _env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "uv"
    stub.write_text(
        _STUB.format(marker=tmp_path / "calls.log", results=_RESULTS),
        encoding="utf-8",
    )
    stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    for key in ("GITHUB_ACTIONS", "ALLOW_LOCAL_MUTATION"):
        env.pop(key, None)
    return {**env, **overrides}


def _run(tmp_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: fixed bash path, test-controlled script
        [BASH, str(SCRIPT), str(tmp_path / "out.txt")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


# Scenario: CI writes the diff of each surviving mutant
def test_ci_writes_each_survivor_diff(tmp_path: Path) -> None:
    result = _run(tmp_path, _env(tmp_path, GITHUB_ACTIONS="true"))

    assert result.returncode == 0, result.stderr
    saved = (tmp_path / "out.txt").read_text(encoding="utf-8")
    for name in ("rag_backend.a.x_f__mutmut_1", "rag_backend.b.x_g__mutmut_7"):
        assert f"=== {name}" in saved
        assert f"--- diff of {name}" in result.stdout
    assert "mutmut_2" not in saved
    assert "Surviving mutants: 2" in result.stdout


# Scenario: the survivor report never runs mutmut locally
def test_local_run_skips_without_mutmut(tmp_path: Path) -> None:
    result = _run(tmp_path, _env(tmp_path))

    assert result.returncode == 77
    assert "mutation runs in CI only" in result.stderr
    assert not (tmp_path / "calls.log").exists()


# Scenario: the backend workflow publishes the survivor report
def test_workflow_runs_and_uploads_the_report() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert (
        "bash ../scripts/ci/mutation-survivor-diffs.sh mutmut-survivors.txt" in workflow
    )
    assert "name: mutmut-survivors" in workflow
    assert "path: backend/mutmut-survivors.txt" in workflow
