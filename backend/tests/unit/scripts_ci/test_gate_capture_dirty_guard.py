"""Rule-fires tests for the gate-capture dirty-tree guard (AE-0322).

The failure class this closes (kaizen session-2026-07-22, FC-1): diff-based
gates (lint-diff, strict-diff, integrity) compare COMMITTED HEAD vs origin/main,
so uncommitted/untracked source files are invisible — a green wrapper run over a
dirty tree was a FALSE green (the AE-0301 incident: 2 real ruff violations hid
behind "No changed Python files").

    Feature: gate runs cannot silently ignore uncommitted in-scope work
      Scenario: an untracked in-scope source file refuses the run (exit 2)
      Scenario: GATE_CAPTURE_ALLOW_DIRTY=1 runs and stamps "dirty":N
      Scenario: a clean tree behaves byte-identically to before
      Scenario: non-source and out-of-scope files do not trip the guard
      Scenario: a failing gate's exit still propagates under ALLOW_DIRTY

The test stands up a throwaway git repo with the REAL wrapper and a STUBBED
gates.sh, so the seeded violations are deterministic and need no toolchain.
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404  # integrity-ok: AE-0322 — a test for a bash gate wrapper must invoke a subprocess (mirrors test_gate_capture.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
WRAPPER = REPO_ROOT / "scripts" / "ci" / "gate-capture.sh"
BASH = shutil.which("bash") or "bash"
GIT = shutil.which("git") or "git"

_STUB_PASSING_GATES = """#!/usr/bin/env bash
echo "GATES_JSON: {\\"pass\\":5,\\"fail\\":0,\\"skip\\":0,\\"results\\":[]}"
exit 0
"""

_STUB_FAILING_GATES = """#!/usr/bin/env bash
echo "GATES_JSON: {\\"pass\\":3,\\"fail\\":2,\\"skip\\":0,\\"results\\":[]}"
exit 2
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603  # integrity-ok: AE-0322 — fixed git path, throwaway test repo
        [GIT, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        timeout=30,
    )


def _stage_repo(tmp_path: Path, stub_body: str = _STUB_PASSING_GATES) -> Path:
    """Throwaway git repo holding the real wrapper + a stubbed gates.sh."""
    ci_dir = tmp_path / "scripts" / "ci"
    ci_dir.mkdir(parents=True)
    (ci_dir / "gate-capture.sh").write_text(
        WRAPPER.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (ci_dir / "gates.sh").write_text(stub_body, encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(
        tmp_path,
        "-c",
        "user.email=test@test",
        "-c",
        "user.name=test",
        "commit",
        "-q",
        "-m",
        "seed",
    )
    return tmp_path


def _run(
    repo: Path, scope: str = "backend", allow_dirty: bool = False
) -> subprocess.CompletedProcess[str]:
    env = {"GATE_CAPTURE_LOG": str(repo / "capture.log"), "PATH": "/usr/bin:/bin"}
    if allow_dirty:
        env["GATE_CAPTURE_ALLOW_DIRTY"] = "1"
    return subprocess.run(  # noqa: S603  # integrity-ok: AE-0322 — fixed bash path, test-controlled stub in a throwaway repo
        [BASH, str(repo / "scripts" / "ci" / "gate-capture.sh"), scope],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=env,
    )


# Scenario: an untracked in-scope source file refuses the run (rule FIRES)
def test_untracked_source_file_refuses_run(tmp_path: Path) -> None:
    repo = _stage_repo(tmp_path)
    (repo / "backend").mkdir()
    (repo / "backend" / "seeded_violation.py").write_text("x = 1\n", encoding="utf-8")

    result = _run(repo)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "DIRTY TREE" in result.stderr
    assert "backend/seeded_violation.py" in result.stderr
    # The gate itself must NOT have run.
    assert not (repo / "capture.log").exists()


# Scenario: a modified tracked source file also refuses the run
def test_modified_tracked_source_file_refuses_run(tmp_path: Path) -> None:
    repo = _stage_repo(tmp_path)
    (repo / "backend").mkdir()
    tracked = repo / "backend" / "module.py"
    tracked.write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "backend/module.py")
    _git(
        repo,
        "-c",
        "user.email=test@test",
        "-c",
        "user.name=test",
        "commit",
        "-q",
        "-m",
        "add module",
    )
    tracked.write_text("x = 2\n", encoding="utf-8")

    result = _run(repo)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "backend/module.py" in result.stderr


# Scenario: GATE_CAPTURE_ALLOW_DIRTY=1 runs and stamps "dirty":N
def test_allow_dirty_runs_and_stamps_dirty_count(tmp_path: Path) -> None:
    repo = _stage_repo(tmp_path)
    (repo / "backend").mkdir()
    (repo / "backend" / "a.py").write_text("a = 1\n", encoding="utf-8")
    (repo / "backend" / "b.py").write_text("b = 1\n", encoding="utf-8")

    result = _run(repo, allow_dirty=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"dirty":2' in result.stdout
    assert "WARNING" in result.stderr


# Scenario: a clean tree behaves byte-identically to before (control)
def test_clean_tree_runs_without_dirty_field(tmp_path: Path) -> None:
    repo = _stage_repo(tmp_path)

    result = _run(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "GATES_JSON:" in result.stdout
    assert '"dirty"' not in result.stdout


# Scenario: non-source files do not trip the guard
def test_non_source_dirty_file_is_ignored(tmp_path: Path) -> None:
    repo = _stage_repo(tmp_path)
    (repo / "backend").mkdir()
    (repo / "backend" / "notes.md").write_text("notes\n", encoding="utf-8")

    result = _run(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"dirty"' not in result.stdout


# Scenario: frontend gate-checker sources are in the frontend scope (QA F-1:
# frontend/scripts holds the .mjs checkers; uncommitted edits must not evade)
def test_untracked_frontend_scripts_checker_trips_frontend_scope(
    tmp_path: Path,
) -> None:
    repo = _stage_repo(tmp_path)
    (repo / "frontend" / "scripts").mkdir(parents=True)
    (repo / "frontend" / "scripts" / "seeded-checker.mjs").write_text(
        "export const x = 1;\n", encoding="utf-8"
    )

    result = _run(repo, scope="frontend")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "frontend/scripts/seeded-checker.mjs" in result.stderr


# Scenario: out-of-scope files do not trip the other scope's run
def test_backend_dirty_file_does_not_trip_frontend_scope(tmp_path: Path) -> None:
    repo = _stage_repo(tmp_path)
    (repo / "backend").mkdir()
    (repo / "backend" / "seeded.py").write_text("x = 1\n", encoding="utf-8")

    result = _run(repo, scope="frontend")

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"dirty"' not in result.stdout


# Scenario: a failing gate's exit still propagates under ALLOW_DIRTY (AE-0259
# exit-code fidelity is preserved by the AE-0322 guard)
def test_failing_gate_exit_propagates_with_dirty_stamp(tmp_path: Path) -> None:
    repo = _stage_repo(tmp_path, stub_body=_STUB_FAILING_GATES)
    (repo / "backend").mkdir()
    (repo / "backend" / "seeded.py").write_text("x = 1\n", encoding="utf-8")

    result = _run(repo, allow_dirty=True)

    assert result.returncode == 2, result.stdout + result.stderr
    assert '"dirty":1' in result.stdout
    assert '"fail":2' in result.stdout
