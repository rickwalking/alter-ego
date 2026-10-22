"""fetch_base_main must not turn a full clone into a shallow one.

    Feature: Gate fetches of origin/main keep the clone's depth
      Scenario: a full clone stays full after the fetch
        Given a full clone whose origin/main gained a commit
        When a diff-scoped gate fetches origin/main
        Then the clone is still not shallow and keeps the whole history
      Scenario: a shallow clone stays shallow and gets the new commit
        Given a depth-1 clone (as CI checks out)
        When a diff-scoped gate fetches origin/main
        Then the clone is still shallow and origin/main is the new commit
      Scenario: no gate script fetches origin/main with a fixed depth
        Then every gate script fetches through fetch_base_main

Each scenario builds a throwaway origin repo and a clone of it.
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404  # integrity-ok: a test for a bash gate helper must invoke git and bash (mirrors test_diff_base.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
HELPER = REPO_ROOT / "scripts" / "lib" / "diff_base.sh"
GATE_SCRIPTS = [
    REPO_ROOT / "scripts" / "ci" / "gates.sh",
    REPO_ROOT / "scripts" / "ci" / "check-integrity.sh",
    REPO_ROOT / "scripts" / "ci" / "changed-backend-files.sh",
    REPO_ROOT / "scripts" / "ci" / "changed-frontend-files.sh",
]
GIT = shutil.which("git") or "git"
BASH = shutil.which("bash") or "bash"
ORIGIN_COMMITS = 3


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603  # integrity-ok: fixed `git` path, test-controlled args in a throwaway repo
        [GIT, *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _commit(repo: Path, message: str) -> None:
    _git(repo, "commit", "--allow-empty", "-q", "-m", message)


def _origin(tmp_path: Path) -> Path:
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    _git(origin, "config", "user.email", "t@example.com")
    _git(origin, "config", "user.name", "Test")
    for index in range(ORIGIN_COMMITS):
        _commit(origin, f"c{index}")
    return origin


def _clone(origin: Path, target: Path, *extra: str) -> Path:
    _git(origin.parent, "clone", "-q", *extra, f"file://{origin}", str(target))
    return target


def _fetch(repo: Path) -> subprocess.CompletedProcess[str]:
    script = f'source "{HELPER}"; fetch_base_main'
    return subprocess.run(  # noqa: S603  # integrity-ok: fixed `bash` path, test-controlled script in a throwaway repo
        [BASH, "-c", script],
        cwd=repo,
        capture_output=True,
        text=True,
    )


# Scenario: a full clone stays full after the fetch
def test_full_clone_stays_full(tmp_path: Path) -> None:
    origin = _origin(tmp_path)
    clone = _clone(origin, tmp_path / "full")
    _commit(origin, "new")

    result = _fetch(clone)

    assert result.returncode == 0, result.stderr
    assert _git(clone, "rev-parse", "--is-shallow-repository") == "false"
    assert _git(clone, "rev-list", "--count", "origin/main") == str(ORIGIN_COMMITS + 1)


# Scenario: a shallow clone stays shallow and gets the new commit
def test_shallow_clone_stays_shallow(tmp_path: Path) -> None:
    origin = _origin(tmp_path)
    clone = _clone(origin, tmp_path / "shallow", "--depth=1")
    _commit(origin, "new")

    result = _fetch(clone)

    assert result.returncode == 0, result.stderr
    assert _git(clone, "rev-parse", "--is-shallow-repository") == "true"
    assert _git(clone, "log", "-1", "--format=%s", "origin/main") == "new"


# Scenario: no gate script fetches origin/main with a fixed depth
def test_gate_scripts_fetch_through_the_helper() -> None:
    for script in GATE_SCRIPTS:
        text = script.read_text(encoding="utf-8")
        assert "git fetch origin main --depth=1" not in text, script.name
        assert "fetch_base_main" in text, script.name
