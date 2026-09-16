"""Rule-fires tests for the external-agent model pin + engagement check (AE-0292).

The failure classes these prove (kaizen session-2026-07-22, FC-2):
  - without ``-m``, ``opencode run`` resolves to the UNFUNDED Zen route and dies
    with "Insufficient balance" — the invocation must pin the funded model;
  - a reasoning model that goes agentic can stream NOTHING back; an empty reply
    must trigger ONE no-tools retry and then a distinct hard-failure exit code
    (never a silent empty verdict).

    Feature: external agent runs are pinned and engagement-checked
      Scenario: the opencode invocation carries the funded model pin
      Scenario: EXT_OPENCODE_MODEL overrides the default pin
      Scenario: an empty reply retries once with the no-tools preamble then fails
      Scenario: the no-tools retry that produces output succeeds

The tests stand up a throwaway PATH with a FAKE ``opencode`` shim (and a no-op
``pkill`` so the lib's clean-kill cannot touch real processes), so the seeded
behaviours are deterministic and need no real CLI.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # noqa: S404  # integrity-ok: AE-0292 — a test for a bash runner lib must invoke a subprocess (mirrors test_gate_capture.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
LIB = REPO_ROOT / "scripts" / "lib" / "external_agent.sh"
BASH = shutil.which("bash") or "bash"

PINNED_DEFAULT_MODEL = "opencode-go/glm-5.2"
NO_TOOLS_PREAMBLE_SNIPPET = "do NOT use tools"
EXIT_EMPTY_OUTPUT = 5

_DRIVER = """#!/usr/bin/env bash
set -uo pipefail
. "$EXT_LIB"
ext_run opencode "$1" "$2"
"""

# Fake opencode: records argv, counts calls, and speaks per SHIM_MODE.
_OPENCODE_SHIM = """#!/usr/bin/env bash
printf '%s\\n---CALL-END---\\n' "$*" >> "$SHIM_ARGS_LOG"
n=$(cat "$SHIM_COUNT_FILE" 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" > "$SHIM_COUNT_FILE"
case "$SHIM_MODE" in
  engaged) echo "ANALYSIS OK" ;;
  empty) : ;;
  empty-then-engaged) [ "$n" -ge 2 ] && echo "RETRY ANALYSIS OK" ;;
esac
exit 0
"""

_PKILL_NOOP = "#!/usr/bin/env bash\nexit 0\n"


def _stage(tmp_path: Path, mode: str) -> dict[str, str]:
    """Build the shim PATH + env for one ext_run invocation."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("opencode", _OPENCODE_SHIM), ("pkill", _PKILL_NOOP)):
        shim = bin_dir / name
        shim.write_text(body, encoding="utf-8")
        shim.chmod(0o755)
    driver = tmp_path / "driver.sh"
    driver.write_text(_DRIVER, encoding="utf-8")
    (tmp_path / "prompt.txt").write_text("REVIEW THIS PACKET", encoding="utf-8")
    return {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "EXT_LIB": str(LIB),
        "EXT_OPENCODE_LOG": str(tmp_path / "opencode.log"),
        "EXTERNAL_RUN_TIMEOUT_SECS": "10",
        "EXTERNAL_STREAM_WAIT_SECS": "10",
        "SHIM_ARGS_LOG": str(tmp_path / "args.log"),
        "SHIM_COUNT_FILE": str(tmp_path / "count"),
        "SHIM_MODE": mode,
        "HOME": str(tmp_path),
    }


def _run(tmp_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: AE-0292 — fixed bash path, test-controlled shims in a throwaway PATH
        [
            BASH,
            str(tmp_path / "driver.sh"),
            str(tmp_path / "prompt.txt"),
            str(tmp_path / "out.txt"),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        env=env,
    )


def _calls(env: dict[str, str]) -> list[str]:
    text = Path(env["SHIM_ARGS_LOG"]).read_text(encoding="utf-8")
    return [c for c in text.split("---CALL-END---") if c.strip()]


def test_opencode_invocation_pins_funded_model(tmp_path: Path) -> None:
    env = _stage(tmp_path, mode="engaged")

    result = _run(tmp_path, env)

    assert result.returncode == 0, result.stdout + result.stderr
    calls = _calls(env)
    assert len(calls) == 1
    # The seeded proof: the built command carries the funded -m pin + plan agent.
    assert f"-m {PINNED_DEFAULT_MODEL}" in calls[0]
    assert "--agent plan" in calls[0]
    assert "ANALYSIS OK" in (tmp_path / "out.txt").read_text(encoding="utf-8")


def test_model_env_override_wins(tmp_path: Path) -> None:
    env = _stage(tmp_path, mode="engaged")
    env["EXT_OPENCODE_MODEL"] = "custom-provider/custom-model"

    result = _run(tmp_path, env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "-m custom-provider/custom-model" in _calls(env)[0]


def test_empty_output_retries_with_preamble_then_fails_distinctly(
    tmp_path: Path,
) -> None:
    env = _stage(tmp_path, mode="empty")

    result = _run(tmp_path, env)

    # Distinct engagement-failure exit — NOT 0 (silent empty verdict) and NOT 3.
    assert result.returncode == EXIT_EMPTY_OUTPUT, result.stdout + result.stderr
    calls = _calls(env)
    assert len(calls) == 2
    # The retry (and only the retry) carries the no-tools preamble.
    assert NO_TOOLS_PREAMBLE_SNIPPET not in calls[0]
    assert NO_TOOLS_PREAMBLE_SNIPPET in calls[1]
    # The original prompt is preserved beneath the preamble.
    assert "REVIEW THIS PACKET" in calls[1]


def test_empty_then_engaged_retry_succeeds(tmp_path: Path) -> None:
    env = _stage(tmp_path, mode="empty-then-engaged")

    result = _run(tmp_path, env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(_calls(env)) == 2
    assert "RETRY ANALYSIS OK" in (tmp_path / "out.txt").read_text(encoding="utf-8")


def test_shim_env_is_isolated() -> None:
    """Control: the real funded default is what the lib documents (AE-0292)."""
    text = LIB.read_text(encoding="utf-8")
    assert 'EXT_OPENCODE_MODEL="${EXT_OPENCODE_MODEL:-' + PINNED_DEFAULT_MODEL in text
    assert os.environ.get("EXT_OPENCODE_MODEL") in (None, PINNED_DEFAULT_MODEL)
