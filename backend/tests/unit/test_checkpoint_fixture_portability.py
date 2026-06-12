"""Portability tests for the captured carousel checkpoint fixture (AE-0075).

Gherkin: tests/features/checkpoint_fixture_portability.feature
"""

from __future__ import annotations

import subprocess  # noqa: S404 — mechanical no-import isolation needs a subprocess
import sys
from pathlib import Path

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "checkpoints"
FIXTURE_BLOB = FIXTURE_DIR / "carousel_checkpoint.msgpack.bin"
PROJECT_MARKER = "rag_backend"
SERDE_TYPE = "msgpack"

_SUBPROCESS_SCRIPT = """
import sys
from pathlib import Path
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

blob = Path(sys.argv[1]).read_bytes()
decoded = JsonPlusSerializer().loads_typed(("{serde}", blob))
forbidden = [m for m in sys.modules if m.startswith("{marker}")]
assert not forbidden, f"project modules imported during decode: {{forbidden}}"
assert "{marker}" not in repr(decoded), "class-path marker found in payload"
print("PORTABLE", len(repr(decoded)))
"""


def scan_for_class_paths(obj: object, path: str = "$") -> list[str]:
    """Return key paths whose values reference project class paths."""
    findings: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            findings.extend(scan_for_class_paths(value, f"{path}.{key}"))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            findings.extend(scan_for_class_paths(value, f"{path}[{index}]"))
    elif isinstance(obj, str) and PROJECT_MARKER in obj:
        findings.append(path)
    return findings


def test_fixture_deserializes_without_project_imports() -> None:
    """Scenario: Captured checkpoint deserializes without project imports."""
    script = _SUBPROCESS_SCRIPT.format(serde=SERDE_TYPE, marker=PROJECT_MARKER)
    result = subprocess.run(  # noqa: S603 — fixed interpreter, fixture path arg
        [sys.executable, "-c", script, str(FIXTURE_BLOB)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("PORTABLE")


def test_class_path_marker_is_detected_with_key_path() -> None:
    """Scenario: Class-path-dependent payload is detected and reported."""
    payload = {
        "channel_values": {
            "ok": "plain string",
            "bad": {"nested": ["fine", "rag_backend.domain.models.Thing"]},
        }
    }
    findings = scan_for_class_paths(payload)
    assert findings == ["$.channel_values.bad.nested[1]"]


def test_fixture_payload_has_no_class_path_entries() -> None:
    """Scenario: Captured checkpoint deserializes without project imports."""
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    decoded = JsonPlusSerializer().loads_typed((SERDE_TYPE, FIXTURE_BLOB.read_bytes()))
    assert scan_for_class_paths(decoded) == []
