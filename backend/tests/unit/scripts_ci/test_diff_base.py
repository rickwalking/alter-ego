"""Tests for the shared diff-base resolver (scripts/lib/diff_base.sh).

The resolver implements a 3-tier fallback so a missing merge base never silently
degrades a diff-scoped gate to a no-op:

    Feature: Diff-base resolution for diff-scoped gates
      Scenario: merge base present -> merge-base form
      Scenario: stacked branch, no merge base -> two-ref fallback (with warning)
      Scenario: base ref unresolvable -> advisory with a VISIBLE warning (never silent)

Each scenario builds a throwaway git repo so the resolver runs against a real
git history, then asserts on stdout (the resolved range), stderr (the warning),
and the exit code (0 = resolved, 1 = advisory).

Interpreters resolve to absolute paths so the tests never rely on a partial executable
name (S607); all arguments are fixed and test-controlled (S603).
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404  # integrity-ok: a test for a bash gate resolver must invoke a subprocess (mirrors test_checkpoint_fixture_portability.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
RESOLVER = REPO_ROOT / "scripts" / "lib" / "diff_base.sh"
GIT = shutil.which("git") or "git"
BASH = shutil.which("bash") or "bash"


def _git_out(repo: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603  # integrity-ok: fixed `git` path, test-controlled args in a throwaway repo
        [GIT, *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _git(repo: Path, *args: str) -> None:
    _git_out(repo, *args)


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "commit", "--allow-empty", "-q", "-m", "root")


def _resolve(repo: Path, base_ref: str) -> subprocess.CompletedProcess[str]:
    """Source the resolver and call resolve_diff_base in `repo`."""
    script = f'source "{RESOLVER}"; resolve_diff_base "{base_ref}"'
    return subprocess.run(  # noqa: S603  # integrity-ok: fixed `bash` path, test-controlled script in a throwaway repo
        [BASH, "-c", script],
        cwd=repo,
        capture_output=True,
        text=True,
    )


# Scenario: merge base present -> merge-base form
def test_resolves_merge_base_form_when_base_is_ancestor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _git(repo, "branch", "base")
    (repo / "a.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "feat")

    result = _resolve(repo, "base")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "base...HEAD"


# Scenario: stacked branch, no merge base -> two-ref fallback (with warning)
def test_falls_back_to_two_ref_when_no_merge_base(tmp_path: Path) -> None:
    """An orphan branch gives disjoint history: no merge base with HEAD, yet the ref still
    resolves (the stacked/diverged-base shape). The base is the original main-line ref,
    master or main depending on the git version/config. The fallback must be visible,
    never silent.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _git(repo, "checkout", "-q", "--orphan", "disjoint")
    (repo / "b.txt").write_text("y", encoding="utf-8")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "disjoint-root")
    _git(repo, "checkout", "-q", "-b", "feature")

    base = "master"
    branches = _git_out(repo, "branch", "--format=%(refname:short)").split()
    if "master" not in branches and "main" in branches:
        base = "main"

    result = _resolve(repo, base)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{base} HEAD"
    assert "no merge base" in result.stderr
    assert "two-ref" in result.stderr


# Scenario: base ref unresolvable -> advisory with a VISIBLE warning (never silent)
def test_degrades_to_advisory_with_visible_warning(tmp_path: Path) -> None:
    """Advisory mode exits non-zero so callers degrade (not a silent pass), prints nothing
    on stdout and emits a loud WARNING that this is not a pass.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    result = _resolve(repo, "origin/does-not-exist")

    assert result.returncode == 1
    assert result.stdout.strip() == ""
    assert "WARNING" in result.stderr
    assert "ADVISORY" in result.stderr
    assert "NOT a pass" in result.stderr
