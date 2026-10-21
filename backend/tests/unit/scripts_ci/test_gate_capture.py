"""Rule-fires test for the gate-capture wrapper (scripts/ci/gate-capture.sh).

The failure this wrapper fixes: `gates.sh <scope> | tail` returns the PIPE's exit
(tail = 0), masking a non-zero gate. The wrapper must instead propagate the
GATE's OWN exit code and write the output (incl. the GATES_JSON line) to a log.

    Feature: gate runs cannot be pipe-masked
      Scenario: the wrapper surfaces a failing gate's real exit code
        Given a gate that fails
        When gate-capture.sh runs that scope
        Then it exits non-zero and writes the capture log with the GATES_JSON line

The test stands up a throwaway scripts/ci tree with a STUBBED failing gates.sh so
the seeded violation is deterministic and needs no real toolchain.

_STUB_FAILING_GATES mimics a failing gates.sh run: it prints the GATES_JSON line and
exits with the fail count, as gates.sh exits `$n_fail`.
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404  # integrity-ok: a test for a bash gate wrapper must invoke a subprocess (mirrors test_diff_base.py / test_require_tool.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
WRAPPER = REPO_ROOT / "scripts" / "ci" / "gate-capture.sh"
BASH = shutil.which("bash") or "bash"

_STUB_FAILING_GATES = """#!/usr/bin/env bash
echo "================= GATE SUMMARY ================="
echo "GATES_JSON: {\\"pass\\":3,\\"fail\\":2,\\"skip\\":0,\\"results\\":[]}"
exit 2
"""

_STUB_PASSING_GATES = """#!/usr/bin/env bash
echo "GATES_JSON: {\\"pass\\":5,\\"fail\\":0,\\"skip\\":0,\\"results\\":[]}"
exit 0
"""


def _stage_wrapper(tmp_path: Path, stub_body: str) -> tuple[Path, Path]:
    """Copy the real wrapper next to a stubbed gates.sh in a throwaway ci/ tree."""
    ci_dir = tmp_path / "scripts" / "ci"
    ci_dir.mkdir(parents=True)
    wrapper = ci_dir / "gate-capture.sh"
    wrapper.write_text(WRAPPER.read_text(encoding="utf-8"), encoding="utf-8")
    (ci_dir / "gates.sh").write_text(stub_body, encoding="utf-8")
    log = tmp_path / "capture.log"
    return wrapper, log


def _run(wrapper: Path, log: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: fixed bash path, test-controlled stub script in a throwaway tree
        [BASH, str(wrapper), "backend"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env={"GATE_CAPTURE_LOG": str(log), "PATH": "/usr/bin:/bin"},
    )


def test_wrapper_surfaces_failing_gate_exit(tmp_path: Path) -> None:
    """The seeded failing gate's real exit (2) must propagate, not a pipe's 0; the capture
    log carries the GATES_JSON verdict line and the wrapper echoes it for the dev
    summary.
    """
    wrapper, log = _stage_wrapper(tmp_path, _STUB_FAILING_GATES)

    result = _run(wrapper, log)

    assert result.returncode == 2, result.stdout + result.stderr
    assert log.exists()
    assert '"fail":2' in log.read_text(encoding="utf-8")
    assert "GATES_JSON:" in result.stdout


def test_wrapper_passes_through_zero_on_green(tmp_path: Path) -> None:
    wrapper, log = _stage_wrapper(tmp_path, _STUB_PASSING_GATES)

    result = _run(wrapper, log)

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"fail":0' in log.read_text(encoding="utf-8")


def test_wrapper_rejects_missing_scope() -> None:
    result = subprocess.run(  # noqa: S603  # integrity-ok: fixed bash path, the real wrapper with no args
        [BASH, str(WRAPPER)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 2
    assert "Usage:" in result.stderr
