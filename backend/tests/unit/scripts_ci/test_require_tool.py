"""Seeded-violation tests for the gates.sh tool preflight (AE-0239).

The preflight (scripts/lib/require_tool.sh) tells "devDependency not installed"
apart from a real violation: a missing jscpd/knip must SKIP (exit 77) with an
actionable message — not FAIL (raw exit-127 read as a violation) and not a
swallowed false PASS on the advisory gates.

    Feature: gates.sh tells "tool missing" apart from "real violation"
      Scenario: knip is not installed locally  -> SKIP (77) + "run npm ci"
      Scenario: jscpd is installed             -> preflight passes (0)

The unit tests source the lib directly (fast, both branches). One integration
test drives the real `gates.sh frontend:dead-files` with the bin dir hidden to
prove the wiring reports SKIP locally and FAIL under GATES_REQUIRE_ALL=1.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # noqa: S404  # integrity-ok: AE-0239 — a test for a bash preflight must invoke a subprocess (mirrors test_diff_base.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
LIB = REPO_ROOT / "scripts" / "lib" / "require_tool.sh"
GATES = REPO_ROOT / "scripts" / "ci" / "gates.sh"
BASH = shutil.which("bash") or "bash"

_MESSAGE = "devDependency 'knip' not installed"


def _run(script: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: AE-0239 — fixed bash path, test-controlled script
        [BASH, "-c", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


# Scenario: tool missing -> SKIP(77) + actionable message (the rule FIRES).
def test_require_tool_skips_when_binary_absent(tmp_path: Path) -> None:
    script = f'FRONTEND_BIN_DIR="{tmp_path}"; source "{LIB}"; require_tool knip'
    result = _run(script)

    assert result.returncode == 77, result.stderr
    assert _MESSAGE in result.stderr
    assert "npm ci" in result.stderr


# Scenario: tool installed -> preflight passes (0), no message.
def test_require_tool_passes_when_binary_present(tmp_path: Path) -> None:
    fake = tmp_path / "knip"
    fake.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    fake.chmod(0o755)
    script = f'FRONTEND_BIN_DIR="{tmp_path}"; source "{LIB}"; require_tool knip'

    result = _run(script)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


# Integration: the real dead-files gate reports SKIP (not a swallowed PASS) when
# knip is hidden, and FAIL under GATES_REQUIRE_ALL=1 (CI must have the tool).
def test_dead_files_gate_skips_when_knip_hidden(tmp_path: Path) -> None:
    env = {**os.environ, "FRONTEND_BIN_DIR": str(tmp_path)}
    result = _run(f'bash "{GATES}" frontend:dead-files', env=env)

    assert ">>> frontend:dead-files: SKIP" in result.stdout, result.stdout
    assert _MESSAGE in result.stderr

    env_ci = {**env, "GATES_REQUIRE_ALL": "1"}
    result_ci = _run(f'bash "{GATES}" frontend:dead-files', env=env_ci)
    assert ">>> frontend:dead-files: FAIL" in result_ci.stdout, result_ci.stdout
