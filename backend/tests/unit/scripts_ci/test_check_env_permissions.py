"""Rule-fires tests for scripts/deploy/check-env-permissions.sh (AE-0301).

The deploy writes production secret files; they were world-readable (644) on
the droplet for ~2 months. The check must FAIL the deploy (non-zero exit) on a
seeded violation — a green run on healthy files proves nothing (AE-0180).

    Feature: production secret files are never world-readable
      Scenario: a world-readable env file fails the deploy
        Given an env file with mode 644
        When check-env-permissions.sh runs against it
        Then it exits non-zero and names the offending file

      Scenario: a plaintext .env.backup copy fails the deploy
        Given a 600 env file but a .env.backup.* file in the deploy dir
        When the check runs
        Then it exits non-zero (the 2026-06-02 backup incident must not recur)

      Scenario: healthy 600 files with no backups pass
"""

from __future__ import annotations

import os
import shutil
import subprocess  # noqa: S404  # integrity-ok: AE-0301 — a test for a bash deploy assertion must invoke a subprocess (mirrors test_gate_capture.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CHECK_SCRIPT = REPO_ROOT / "scripts" / "deploy" / "check-env-permissions.sh"
BASH = shutil.which("bash") or "bash"

MODE_SECRET = 0o600
MODE_WORLD_READABLE = 0o644
EXIT_VIOLATION = 1
EXIT_USAGE = 2
FAIL_MARKER = "ENV-PERMS FAIL:"
OK_MARKER = "ENV-PERMS OK:"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: AE-0301 — fixed bash path, test-controlled temp files
        [BASH, str(CHECK_SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def _seed_env(tmp_path: Path, mode: int) -> Path:
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET_KEY=not-a-real-secret\n", encoding="utf-8")
    os.chmod(env_file, mode)
    return env_file


def test_fires_on_world_readable_env_file(tmp_path: Path) -> None:
    env_file = _seed_env(tmp_path, MODE_WORLD_READABLE)

    result = _run(str(tmp_path), str(env_file))

    assert result.returncode == EXIT_VIOLATION, result.stdout + result.stderr
    assert FAIL_MARKER in result.stderr
    assert str(env_file) in result.stderr


def test_fires_on_plaintext_backup_present(tmp_path: Path) -> None:
    env_file = _seed_env(tmp_path, MODE_SECRET)
    backup = tmp_path / ".env.backup.20260602-211752"
    backup.write_text("SECRET_KEY=stale-copy\n", encoding="utf-8")

    result = _run(str(tmp_path), str(env_file))

    assert result.returncode == EXIT_VIOLATION, result.stdout + result.stderr
    assert FAIL_MARKER in result.stderr
    assert backup.name in result.stderr


def test_fires_on_missing_env_file(tmp_path: Path) -> None:
    missing = tmp_path / ".env"

    result = _run(str(tmp_path), str(missing))

    assert result.returncode == EXIT_VIOLATION, result.stdout + result.stderr
    assert FAIL_MARKER in result.stderr


def test_fires_on_wrong_owner_expectation(tmp_path: Path) -> None:
    env_file = _seed_env(tmp_path, MODE_SECRET)

    result = subprocess.run(  # noqa: S603  # integrity-ok: AE-0301 — fixed bash path, test-controlled temp files
        [BASH, str(CHECK_SCRIPT), str(tmp_path), str(env_file)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env={**os.environ, "ENV_PERMS_EXPECTED_OWNER": "root"},
    )

    assert result.returncode == EXIT_VIOLATION, result.stdout + result.stderr
    assert FAIL_MARKER in result.stderr


def test_passes_on_healthy_600_files(tmp_path: Path) -> None:
    env_file = _seed_env(tmp_path, MODE_SECRET)
    backend_env = tmp_path / "backend.env"
    backend_env.write_text("DEBUG=false\n", encoding="utf-8")
    os.chmod(backend_env, MODE_SECRET)

    result = _run(str(tmp_path), str(env_file), str(backend_env))

    assert result.returncode == 0, result.stdout + result.stderr
    assert OK_MARKER in result.stdout


def test_rejects_missing_arguments() -> None:
    result = _run()

    assert result.returncode == EXIT_USAGE
    assert "Usage:" in result.stderr
