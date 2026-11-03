"""Dry runs of scripts/deploy/drain-generation-worker.sh against a stub ``docker``.

The stub answers ``compose ps`` from the test's settings and runs every
``compose exec ... python -m rag_backend.worker.drain_cli <command>`` with the
real CLI on files in a temp folder, so the wait, the bound and the clear are the
real ones. Feature file: tests/features/deploy_drains_worker_ae0598.feature
"""

from __future__ import annotations

import os
import shutil
import subprocess  # noqa: S404  # integrity-ok: a test for a bash deploy step must invoke a subprocess (mirrors test_check_env_permissions.py)
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "scripts" / "deploy" / "drain-generation-worker.sh"
BASH = shutil.which("bash") or "bash"
COMPOSE_FILE = "docker-compose.prod.yml"
EXIT_OK = 0
EXIT_USAGE = 2
WARNING = "::warning::"
CLI = "rag_backend.worker.drain_cli"

STUB = """#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
if [ "$4" = ps ]; then
  [ "$STUB_RUNNING" = 1 ] && echo 4f2a9c
  exit 0
fi
if [ "$4" = exec ]; then
  [ -n "${STUB_EXEC_EXIT:-}" ] && exit "$STUB_EXEC_EXIT"
  shift 7
  exec "$STUB_PYTHON" "$@"
fi
exit 99
"""


@dataclass(frozen=True)
class _Stage:
    """The stub ``docker`` and the worker's drain files of one dry run."""

    root: Path
    log: Path
    drain: Path
    busy: Path

    def env(self, running: bool, exec_exit: str = "") -> dict[str, str]:
        env = dict(os.environ)
        env.update({
            "PATH": f"{self.root / 'bin'}{os.pathsep}{env.get('PATH', '')}",
            "STUB_LOG": str(self.log),
            "STUB_RUNNING": "1" if running else "0",
            "STUB_PYTHON": sys.executable,
            "STUB_EXEC_EXIT": exec_exit,
            "GENERATION_WORKER_DRAIN_FILE": str(self.drain),
            "GENERATION_WORKER_BUSY_FILE": str(self.busy),
        })
        return env

    def calls(self) -> list[str]:
        if not self.log.exists():
            return []
        return self.log.read_text(encoding="utf-8").splitlines()

    def cli_calls(self, command: str) -> int:
        return sum(1 for call in self.calls() if call.endswith(f"{CLI} {command}"))


def _stage(tmp_path: Path) -> _Stage:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(STUB, encoding="utf-8")
    docker.chmod(0o755)
    return _Stage(
        root=tmp_path,
        log=tmp_path / "docker.log",
        drain=tmp_path / "drain",
        busy=tmp_path / "busy",
    )


def _run(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: fixed bash path, test-controlled stub and temp files
        [BASH, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        env=env,
    )


def test_the_deploy_waits_until_the_worker_is_idle(tmp_path: Path) -> None:
    """Scenario: The deploy waits until the worker is idle, then stops it"""
    stage = _stage(tmp_path)
    stage.busy.touch()
    timer = threading.Timer(2.5, lambda: stage.busy.unlink())
    timer.start()
    started = time.monotonic()
    try:
        result = _run(stage.env(running=True), "drain", COMPOSE_FILE, "30", "1")
    finally:
        timer.cancel()
    elapsed = time.monotonic() - started
    assert result.returncode == EXIT_OK, result.stdout + result.stderr
    assert "DRAIN: generation-worker idle after" in result.stdout
    assert WARNING not in result.stdout
    assert stage.drain.exists()
    assert stage.cli_calls("drain") == 1
    assert stage.cli_calls("idle") >= 2
    assert elapsed < 20
    assert f"compose -f {COMPOSE_FILE} exec -T generation-worker" in stage.calls()[1]


def test_an_idle_worker_is_stopped_at_once(tmp_path: Path) -> None:
    """Scenario: The deploy waits until the worker is idle, then stops it"""
    stage = _stage(tmp_path)
    result = _run(stage.env(running=True), "drain", COMPOSE_FILE, "30", "1")
    assert result.returncode == EXIT_OK
    assert "idle after 0s" in result.stdout
    assert stage.cli_calls("idle") == 1


def test_the_drain_wait_is_bounded(tmp_path: Path) -> None:
    """Scenario: The deploy drain wait is bounded"""
    stage = _stage(tmp_path)
    stage.busy.touch()
    started = time.monotonic()
    result = _run(stage.env(running=True), "drain", COMPOSE_FILE, "2", "1")
    elapsed = time.monotonic() - started
    assert result.returncode == EXIT_OK, result.stdout + result.stderr
    assert f"{WARNING}DRAIN: generation-worker still busy after 2s" in result.stdout
    assert "resumes from its last checkpoint" in result.stdout
    assert 2 <= elapsed < 15
    assert stage.cli_calls("idle") >= 2
    assert stage.drain.exists()


def test_a_stopped_worker_is_not_drained(tmp_path: Path) -> None:
    """Scenario: The deploy skips the drain when the worker is not running"""
    stage = _stage(tmp_path)
    result = _run(stage.env(running=False), "drain", COMPOSE_FILE, "30", "1")
    assert result.returncode == EXIT_OK
    assert "nothing to drain" in result.stdout
    assert stage.cli_calls("drain") == 0
    assert not stage.drain.exists()


def test_a_worker_without_the_drain_cli_never_blocks_the_deploy(
    tmp_path: Path,
) -> None:
    """Scenario: A drain request the worker cannot answer never blocks the deploy"""
    stage = _stage(tmp_path)
    result = _run(
        stage.env(running=True, exec_exit="1"), "drain", COMPOSE_FILE, "30", "1"
    )
    assert result.returncode == EXIT_OK
    assert f"{WARNING}DRAIN: could not set the drain flag" in result.stdout
    assert stage.cli_calls("idle") == 0


def test_the_deploy_clears_the_drain_flag(tmp_path: Path) -> None:
    """Scenario: The deploy clears the drain flag on the new worker"""
    stage = _stage(tmp_path)
    stage.drain.touch()
    result = _run(stage.env(running=True), "clear", COMPOSE_FILE)
    assert result.returncode == EXIT_OK, result.stdout + result.stderr
    assert "DRAIN: flag cleared" in result.stdout
    assert not stage.drain.exists()
    assert stage.cli_calls("clear") == 1


def test_a_failed_clear_only_warns(tmp_path: Path) -> None:
    """Scenario: The deploy clears the drain flag on the new worker"""
    stage = _stage(tmp_path)
    failed = _run(stage.env(running=True, exec_exit="1"), "clear", COMPOSE_FILE)
    assert failed.returncode == EXIT_OK
    assert f"{WARNING}DRAIN: could not clear the drain flag" in failed.stdout
    gone = _run(stage.env(running=False), "clear", COMPOSE_FILE)
    assert gone.returncode == EXIT_OK
    assert f"{WARNING}DRAIN: generation-worker is not running" in gone.stdout


def test_a_usage_error_touches_nothing(tmp_path: Path) -> None:
    """Scenario: A drain request the worker cannot answer never blocks the deploy"""
    stage = _stage(tmp_path)
    env = stage.env(running=True)
    for args in (
        (),
        ("drain",),
        ("drain", COMPOSE_FILE),
        ("drain", COMPOSE_FILE, "soon", "1"),
        ("drain", COMPOSE_FILE, "30", "-1"),
        ("clear", COMPOSE_FILE, "extra"),
        ("stop", COMPOSE_FILE),
    ):
        result = _run(env, *args)
        assert result.returncode == EXIT_USAGE, args
        assert "usage:" in result.stderr
    assert stage.calls() == []
