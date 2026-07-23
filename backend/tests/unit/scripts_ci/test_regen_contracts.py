"""Rule-fires tests for the one-command contract regen script (AE-0325).

The property under test (cold-critic WARN-5): a PARTIAL regen must never look
done. A failing step aborts fail-fast with an INCOMPLETE banner and a non-zero
exit; only a full regen + read-only verification pass exits 0.

    Feature: contract regeneration is all-or-nothing
      Scenario: a failing regen step aborts with the INCOMPLETE banner (seeded)
      Scenario: a fully green run performs the read-only verify pass and exits 0
      Scenario: the script works regardless of the caller's CWD

The test stands up a throwaway tree with the REAL script and a FAKE ``uv`` shim
whose per-call behaviour is scripted, so the seeded failure is deterministic
and needs no real backend toolchain.
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404  # integrity-ok: AE-0325 — a test for a bash regen wrapper must invoke a subprocess (mirrors test_gate_capture.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "scripts" / "dev" / "regen_contracts.sh"
BASH = shutil.which("bash") or "bash"

# Fake uv: records each call, fails when its 1-based call number equals
# SHIM_FAIL_ON_CALL (0 = never fail).
_UV_SHIM = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$SHIM_CALLS_LOG"
n=$(cat "$SHIM_COUNT_FILE" 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" > "$SHIM_COUNT_FILE"
if [ "$n" -eq "${SHIM_FAIL_ON_CALL:-0}" ]; then
  echo "seeded regen failure" >&2
  exit 1
fi
exit 0
"""

TOTAL_UV_CALLS = 6  # 4 regen steps + 2 read-only verify steps


def _stage(tmp_path: Path, fail_on_call: int) -> dict[str, str]:
    dev_dir = tmp_path / "scripts" / "dev"
    dev_dir.mkdir(parents=True)
    staged = dev_dir / "regen_contracts.sh"
    staged.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "backend").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "uv"
    shim.write_text(_UV_SHIM, encoding="utf-8")
    shim.chmod(0o755)
    return {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "SHIM_CALLS_LOG": str(tmp_path / "calls.log"),
        "SHIM_COUNT_FILE": str(tmp_path / "count"),
        "SHIM_FAIL_ON_CALL": str(fail_on_call),
    }


def _run(
    tmp_path: Path, env: dict[str, str], cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: AE-0325 — fixed bash path, test-controlled shim in a throwaway tree
        [BASH, str(tmp_path / "scripts" / "dev" / "regen_contracts.sh")],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=env,
        cwd=str(cwd or tmp_path),
    )


def _call_count(env: dict[str, str]) -> int:
    log = Path(env["SHIM_CALLS_LOG"])
    if not log.exists():
        return 0
    return len(log.read_text(encoding="utf-8").splitlines())


# Scenario: a failing regen step aborts with the INCOMPLETE banner (rule FIRES)
def test_seeded_step_failure_aborts_incomplete(tmp_path: Path) -> None:
    env = _stage(tmp_path, fail_on_call=3)

    result = _run(tmp_path, env)

    assert result.returncode != 0, result.stdout + result.stderr
    assert "INCOMPLETE" in result.stderr
    # Fail-fast: nothing after the seeded failing step ran.
    assert _call_count(env) == 3


def test_first_step_failure_aborts_immediately(tmp_path: Path) -> None:
    env = _stage(tmp_path, fail_on_call=1)

    result = _run(tmp_path, env)

    assert result.returncode != 0
    assert "INCOMPLETE" in result.stderr
    assert _call_count(env) == 1


# Scenario: a fully green run performs the read-only verify pass and exits 0
def test_green_run_verifies_read_only_and_succeeds(tmp_path: Path) -> None:
    env = _stage(tmp_path, fail_on_call=0)

    result = _run(tmp_path, env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "verified read-only" in result.stdout
    assert _call_count(env) == TOTAL_UV_CALLS
    calls = Path(env["SHIM_CALLS_LOG"]).read_text(encoding="utf-8").splitlines()
    # The verify pass is read-only: no regen flags in the last two calls.
    assert "--check" in calls[4]
    assert "--snapshot-update" not in calls[5]


# Scenario: a verify-phase failure still reports INCOMPLETE (a half-verified
# state is not success)
def test_verify_phase_failure_is_incomplete(tmp_path: Path) -> None:
    env = _stage(tmp_path, fail_on_call=5)

    result = _run(tmp_path, env)

    assert result.returncode != 0
    assert "INCOMPLETE" in result.stderr
    assert _call_count(env) == 5


# Scenario: the script works regardless of the caller's CWD
def test_runs_from_any_cwd(tmp_path: Path) -> None:
    env = _stage(tmp_path, fail_on_call=0)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    result = _run(tmp_path, env, cwd=elsewhere)

    assert result.returncode == 0, result.stdout + result.stderr
