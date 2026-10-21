"""Tests for the strict diff ruff gate (scripts/ci/ruff-strict-changed.sh).

    Feature: Strict diff ruff on changed lines
      Scenario: listing the changed files drops the merge base -> the gate still runs
      Scenario: a seeded too-many-arguments violation on a changed line still fires

Review round 2: ``changed-backend-files.sh`` runs
``git fetch origin main --depth=1``. On a stacked PR that shallow fetch can
remove the merge base AFTER the gate resolved ``origin/main...HEAD``; every
per-file ``git diff`` then failed, ``grep`` returned 1 under ``set -e`` /
``pipefail`` and the gate died with no violation printed. The gate now lists
the files first, then resolves the range, and treats a file without hunks as
"nothing to check".

Each scenario builds a throwaway repo with copies of the gate + resolver and a
stub file lister that moves ``origin/main`` to an unrelated commit (no merge
base), then runs the gate with a ``uv`` shim that executes the real ruff.

LISTER is a stub lister that prints the changed file, then points origin/main at an
unrelated commit, as the CI shallow fetch of main effectively does.
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404  # integrity-ok: a test for a bash gate must invoke a subprocess (mirrors test_diff_base.py)
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
GATE = REPO_ROOT / "scripts" / "ci" / "ruff-strict-changed.sh"
RESOLVER = REPO_ROOT / "scripts" / "lib" / "diff_base.sh"
GIT = shutil.which("git") or "git"
BASH = shutil.which("bash") or "bash"
RUFF_DIR = Path(sys.executable).parent

CLEAN_SOURCE = "def ok(a: int) -> int:\n    return a\n"
VIOLATION_SOURCE = (
    "def ok(a: int) -> int:\n    return a\n\n\n"
    "def too_many(a: int, b: int, c: int, d: int, e: int) -> int:\n"
    "    return a + b + c + d + e\n"
)
LISTER = """#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
git update-ref refs/remotes/origin/main "$(cat .orphan)"
echo src/mod.py
"""
UV_SHIM = '#!/usr/bin/env bash\nshift\nexec "$@"\n'


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603  # integrity-ok: fixed `git` path, test-controlled args in a throwaway repo
        [GIT, *args], cwd=repo, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _write(path: Path, text: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if executable:
        path.chmod(0o755)


def _build_repo(repo: Path, head_source: str) -> None:
    """main has CLEAN_SOURCE; HEAD changes it; .orphan names an unrelated commit."""
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    shutil.copy(GATE, _dir(repo / "scripts" / "ci") / GATE.name)
    shutil.copy(RESOLVER, _dir(repo / "scripts" / "lib") / RESOLVER.name)
    _write(
        repo / "scripts" / "ci" / "changed-backend-files.sh", LISTER, executable=True
    )
    _write(repo / "backend" / "src" / "mod.py", CLEAN_SOURCE)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "main")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _write(repo / "backend" / "src" / "mod.py", head_source + "\n# changed\n")
    _git(repo, "commit", "-qam", "branch")
    orphan_tree = _git(repo, "mktree", "--missing")
    orphan = _git(repo, "commit-tree", orphan_tree, "-m", "unrelated main")
    _write(repo / ".orphan", orphan)


def _dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_gate(repo: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    shim_dir = _dir(tmp_path / "bin")
    _write(shim_dir / "uv", UV_SHIM, executable=True)
    path = f"{shim_dir}:{RUFF_DIR}:/usr/bin:/bin"
    return subprocess.run(  # noqa: S603  # integrity-ok: fixed `bash` path, test-controlled gate copy in a throwaway repo
        [BASH, str(repo / "scripts" / "ci" / GATE.name)],
        cwd=repo,
        capture_output=True,
        text=True,
        env={"PATH": path, "GATES_BASE_REF": "origin/main", "HOME": str(tmp_path)},
    )


# Scenario: listing the changed files drops the merge base -> the gate still runs
def test_merge_base_lost_while_listing_still_checks(tmp_path: Path) -> None:
    repo = _dir(tmp_path / "repo")
    _build_repo(repo, CLEAN_SOURCE)
    result = _run_gate(repo, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Strict ruff on 1 changed source file(s)" in result.stdout


# Scenario: a seeded too-many-arguments violation on a changed line still fires
def test_seeded_violation_still_fails_the_gate(tmp_path: Path) -> None:
    repo = _dir(tmp_path / "repo")
    _build_repo(repo, VIOLATION_SOURCE)
    result = _run_gate(repo, tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "PLR0913" in result.stdout or "src/mod.py" in result.stdout
    assert "violations found in changed lines" in result.stdout
