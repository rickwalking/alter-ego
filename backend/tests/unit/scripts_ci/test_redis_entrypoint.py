"""Rule-fires + config-integrity tests for scripts/deploy/redis-entrypoint.sh (AE-0302).

Server-side fail-closed: an empty REDIS_PASSWORD in a production-like
environment must make the container REFUSE to start — never start an open
``requirepass ""`` instance. Per AE-0180 the failing branch is tested with a
seeded violation, and the build-time config-integrity assertion (the
``rename-command`` lines are present) is the check that auth cannot be
re-opened via ``CONFIG SET requirepass ""`` (the runtime NOAUTH probe at
deploy time proves auth is required *now*; the two are deliberately separate).

    Gherkin: tests/features/redis_auth.feature —
      "missing password fails closed on the server side too"
"""

from __future__ import annotations

import os
import shutil
import subprocess  # noqa: S404  # integrity-ok: AE-0302 — a test for a shell entrypoint must invoke a subprocess (mirrors test_check_env_permissions.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ENTRYPOINT = REPO_ROOT / "scripts" / "deploy" / "redis-entrypoint.sh"
SH = shutil.which("sh") or "sh"

ENV_PRODUCTION = "production"
ENV_DEVELOPMENT = "development"
MODE_EXECUTABLE = 0o755

# Admin verbs that must be disabled in prod (config-integrity, AC part (a)).
DISABLED_COMMANDS = ("CONFIG", "FLUSHALL", "FLUSHDB", "DEBUG", "SHUTDOWN")

_FAKE_REDIS_SERVER = """#!/bin/sh
printf '%s\\n' "$@" > "$ARGS_CAPTURE"
exit 0
"""


def _run(
    env: dict[str, str], fake_bin: Path | None = None
) -> subprocess.CompletedProcess[str]:
    merged = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), **env}
    if fake_bin is not None:
        merged["PATH"] = f"{fake_bin}:{merged['PATH']}"
    return subprocess.run(  # noqa: S603  # integrity-ok: AE-0302 — fixed sh path, the real entrypoint under a test-controlled env
        [SH, str(ENTRYPOINT)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=merged,
    )


def _stage_fake_redis_server(tmp_path: Path) -> tuple[Path, Path]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    capture = tmp_path / "args.txt"
    server = fake_bin / "redis-server"
    server.write_text(_FAKE_REDIS_SERVER, encoding="utf-8")
    server.chmod(MODE_EXECUTABLE)
    return fake_bin, capture


# Scenario: missing password fails closed on the server side too
def test_fires_on_empty_password_in_production() -> None:
    result = _run({"ENVIRONMENT": ENV_PRODUCTION, "REDIS_PASSWORD": ""})

    assert result.returncode != 0, result.stdout + result.stderr
    assert "Refusing to start" in result.stderr


def test_fires_on_unset_environment_without_password() -> None:
    result = _run({})

    assert result.returncode != 0, result.stdout + result.stderr


def test_fires_on_unrecognized_environment_without_password() -> None:
    result = _run({"ENVIRONMENT": "prod"})  # typo'd value must fail closed

    assert result.returncode != 0, result.stdout + result.stderr


def test_production_with_password_passes_requirepass_and_renames(
    tmp_path: Path,
) -> None:
    fake_bin, capture = _stage_fake_redis_server(tmp_path)

    result = _run(
        {
            "ENVIRONMENT": ENV_PRODUCTION,
            "REDIS_PASSWORD": "s3cret",
            "ARGS_CAPTURE": str(capture),
        },
        fake_bin=fake_bin,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    args = capture.read_text(encoding="utf-8").splitlines()
    assert "--requirepass" in args
    assert "s3cret" in args
    for command in DISABLED_COMMANDS:
        assert command in args, f"rename-command {command} missing"


def test_development_without_password_starts_unauthenticated(
    tmp_path: Path,
) -> None:
    fake_bin, capture = _stage_fake_redis_server(tmp_path)

    result = _run(
        {
            "ENVIRONMENT": ENV_DEVELOPMENT,
            "REDIS_PASSWORD": "",
            "ARGS_CAPTURE": str(capture),
        },
        fake_bin=fake_bin,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "--requirepass" not in capture.read_text(encoding="utf-8").splitlines()


# Build-time config-integrity assertion (AC part (a)): the rename-command
# lines are present in the shipped entrypoint, so auth cannot be re-opened at
# runtime via CONFIG SET — independent of the runtime NOAUTH probe.
def test_entrypoint_ships_the_rename_command_lockdown() -> None:
    text = ENTRYPOINT.read_text(encoding="utf-8")

    for command in DISABLED_COMMANDS:
        assert f'--rename-command {command} ""' in text, command
