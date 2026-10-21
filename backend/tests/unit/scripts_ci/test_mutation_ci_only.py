"""Seeded-violation tests for the CI-only mutation guard.

Pedro's call: local mutmut / Stryker runs run the dev machine out of memory, so
mutation runs in CI only. Outside GitHub Actions every local entry point must
SKIP (77) with the CI-only message BEFORE starting mutmut / Stryker; in CI
(GITHUB_ACTIONS=true) nothing changes and the mutation tools still run.

    Feature: mutation runs in CI only
      Scenario: a local gates.sh backend:mutation run is skipped
        Given GITHUB_ACTIONS is not "true"
        When gates.sh backend:mutation runs
        Then the gate reports SKIP with the CI-only message and mutmut never starts
      Scenario: a local gates.sh frontend:mutation run is skipped
        Then the gate reports SKIP and Stryker (npm run test:mutate) never starts
      Scenario: calling mutation-score-gate.sh directly is skipped
        Then it exits 77 and mutmut never starts
      Scenario: CI still runs mutation
        Given GITHUB_ACTIONS is "true"
        Then mutmut / Stryker are invoked and the CI-only message is absent
      Scenario: an explicit opt-in bypasses the guard locally
        Given ALLOW_LOCAL_MUTATION is "1"
        Then mutmut is invoked

No real mutmut / Stryker ever runs here: `uv` and `npm` are replaced by stubs on
PATH that only record that they were called.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # noqa: S404  # integrity-ok: a test for a bash gate guard must invoke a subprocess (mirrors test_require_tool.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
GATES = REPO_ROOT / "scripts" / "ci" / "gates.sh"
SCORE_GATE = REPO_ROOT / "scripts" / "ci" / "mutation-score-gate.sh"
GUARD = REPO_ROOT / "scripts" / "lib" / "mutation_ci_only.sh"
PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
BASH = shutil.which("bash") or "bash"

_EXIT_SKIP = 77
_MESSAGE = "mutation runs in CI only"
_MARKER = "invoked.log"
_STUB = '#!/usr/bin/env bash\necho "$(basename "$0") $*" >> "{marker}"\nexit 0\n'


def _stub_path(tmp_path: Path) -> Path:
    """A bin dir whose `uv` / `npm` only append their argv to a marker file."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    marker = tmp_path / _MARKER
    for tool in ("uv", "npm"):
        stub = bin_dir / tool
        stub.write_text(_STUB.format(marker=marker), encoding="utf-8")
        stub.chmod(0o755)
    return bin_dir


def _env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    """The backend tests themselves run in GitHub Actions, so the CI markers are dropped
    and each scenario sets exactly the environment it describes.
    """
    env = {**os.environ, "PATH": f"{_stub_path(tmp_path)}:{os.environ['PATH']}"}
    for key in ("GITHUB_ACTIONS", "ALLOW_LOCAL_MUTATION", "GATES_REQUIRE_ALL"):
        env.pop(key, None)
    return {**env, **overrides}


def _run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: fixed bash path, test-controlled script
        [BASH, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def _invoked(tmp_path: Path) -> str:
    marker = tmp_path / _MARKER
    return marker.read_text(encoding="utf-8") if marker.exists() else ""


# Scenario: a local gates.sh backend:mutation run is skipped (the guard FIRES).
def test_local_backend_mutation_gate_skips_without_mutmut(tmp_path: Path) -> None:
    result = _run([str(GATES), "backend:mutation"], _env(tmp_path))

    assert ">>> backend:mutation: SKIP" in result.stdout, result.stdout
    assert _MESSAGE in result.stderr
    assert "ALLOW_LOCAL_MUTATION=1" in result.stderr
    assert _invoked(tmp_path) == ""


# Scenario: a local gates.sh frontend:mutation run is skipped (not a swallowed PASS).
def test_local_frontend_mutation_gate_skips_without_stryker(tmp_path: Path) -> None:
    result = _run([str(GATES), "frontend:mutation"], _env(tmp_path))

    assert ">>> frontend:mutation: SKIP" in result.stdout, result.stdout
    assert _MESSAGE in result.stderr
    assert _invoked(tmp_path) == ""


# Scenario: the local SKIP still fails under GATES_REQUIRE_ALL=1.
def test_local_mutation_skip_fails_under_require_all(tmp_path: Path) -> None:
    env = _env(tmp_path, GATES_REQUIRE_ALL="1")
    result = _run([str(GATES), "backend:mutation"], env)

    assert ">>> backend:mutation: FAIL" in result.stdout, result.stdout
    assert result.returncode != 0
    assert _invoked(tmp_path) == ""


# Scenario: calling mutation-score-gate.sh directly is skipped.
def test_score_gate_called_directly_exits_skip(tmp_path: Path) -> None:
    result = _run([str(SCORE_GATE), "75"], _env(tmp_path))

    assert result.returncode == _EXIT_SKIP, result.stderr
    assert _MESSAGE in result.stderr
    assert _invoked(tmp_path) == ""


# Scenario: the standalone guard (what `npm run test:mutate` calls) exits 77 locally and 0 in CI, and the npm script runs it before Stryker.
def test_standalone_guard_and_npm_script_wiring(tmp_path: Path) -> None:
    local = _run([str(GUARD)], _env(tmp_path))
    ci = _run([str(GUARD)], _env(tmp_path, GITHUB_ACTIONS="true"))
    scripts = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))["scripts"]

    assert local.returncode == _EXIT_SKIP
    assert _MESSAGE in local.stderr
    assert ci.returncode == 0
    assert ci.stderr == ""
    assert scripts["test:mutate"] == (
        "bash ../scripts/lib/mutation_ci_only.sh && stryker run"
    )


# Scenario: CI still runs mutation (GITHUB_ACTIONS=true does not skip).
def test_ci_runs_backend_mutation(tmp_path: Path) -> None:
    env = _env(tmp_path, GITHUB_ACTIONS="true")
    result = _run([str(GATES), "backend:mutation"], env)

    assert "uv run mutmut run" in _invoked(tmp_path)
    assert _MESSAGE not in result.stderr
    assert ">>> backend:mutation: SKIP" not in result.stdout


def test_ci_runs_frontend_mutation(tmp_path: Path) -> None:
    env = _env(tmp_path, GITHUB_ACTIONS="true")
    result = _run([str(GATES), "frontend:mutation"], env)

    assert "npm run test:mutate" in _invoked(tmp_path)
    assert _MESSAGE not in result.stderr
    assert ">>> frontend:mutation: PASS" in result.stdout, result.stdout


# Scenario: an explicit opt-in bypasses the guard locally.
def test_allow_local_mutation_opt_in_runs_mutmut(tmp_path: Path) -> None:
    env = _env(tmp_path, ALLOW_LOCAL_MUTATION="1")
    result = _run([str(GATES), "backend:mutation"], env)

    assert "uv run mutmut run" in _invoked(tmp_path)
    assert _MESSAGE not in result.stderr
