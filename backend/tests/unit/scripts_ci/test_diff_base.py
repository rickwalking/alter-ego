"""Tests for the shared diff-base resolver (scripts/lib/diff_base.sh, AE-0177).

The resolver implements a 3-tier fallback so a missing merge base never silently
degrades a diff-scoped gate to a no-op:

    Feature: Diff-base resolution for diff-scoped gates
      Scenario: merge base present -> merge-base form
      Scenario: stacked branch, no merge base -> two-ref fallback (with warning)
      Scenario: base ref unresolvable -> advisory with a VISIBLE warning (never silent)

Each scenario builds a throwaway git repo so the resolver runs against a real
git history, then asserts on stdout (the resolved range), stderr (the warning),
and the exit code (0 = resolved, 1 = advisory).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
RESOLVER = REPO_ROOT / "scripts" / "lib" / "diff_base.sh"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "commit", "--allow-empty", "-q", "-m", "root")


def _resolve(repo: Path, base_ref: str) -> subprocess.CompletedProcess[str]:
    """Source the resolver and call resolve_diff_base in `repo`."""
    script = f'source "{RESOLVER}"; resolve_diff_base "{base_ref}"'
    return subprocess.run(
        ["bash", "-c", script],
        cwd=repo,
        capture_output=True,
        text=True,
    )


# Scenario: merge base present -> merge-base form
def test_resolves_merge_base_form_when_base_is_ancestor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _git(repo, "branch", "base")  # base == an ancestor of HEAD
    (repo / "a.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "feat")

    result = _resolve(repo, "base")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "base...HEAD"


# Scenario: stacked branch, no merge base -> two-ref fallback (with warning)
def test_falls_back_to_two_ref_when_no_merge_base(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    # Orphan branch => disjoint history => no merge base with HEAD, but the ref
    # is still resolvable (this is the stacked/diverged-base shape).
    _git(repo, "checkout", "-q", "--orphan", "disjoint")
    (repo / "b.txt").write_text("y", encoding="utf-8")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "disjoint-root")
    _git(repo, "checkout", "-q", "-b", "feature")  # HEAD on feature off disjoint

    # Use the original main-line ref (master/main) as base: resolvable but no
    # merge base with the orphan-rooted HEAD.
    base = "master"
    # git's default branch may be 'main' or 'master' depending on version/config.
    branches = subprocess.run(
        ["git", "branch", "--format=%(refname:short)"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    if "master" not in branches and "main" in branches:
        base = "main"

    result = _resolve(repo, base)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{base} HEAD"
    # The fallback must be VISIBLE, never silent.
    assert "no merge base" in result.stderr
    assert "two-ref" in result.stderr


# Scenario: base ref unresolvable -> advisory with a VISIBLE warning (never silent)
def test_degrades_to_advisory_with_visible_warning(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    result = _resolve(repo, "origin/does-not-exist")

    # Advisory: non-zero exit so callers degrade (NOT a silent pass)...
    assert result.returncode == 1
    # ...with nothing on stdout (no range to use)...
    assert result.stdout.strip() == ""
    # ...and a loud, explicit warning that this is NOT a pass.
    assert "WARNING" in result.stderr
    assert "ADVISORY" in result.stderr
    assert "NOT a pass" in result.stderr
