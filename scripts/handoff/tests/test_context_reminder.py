"""Tests for the optional non-blocking Stop reminder.

Behaviour under test:
  * silent below threshold; nudges at/above threshold;
  * de-duplicated per session (once per step band, not every turn);
  * never blocks (no `decision` field — only additionalContext);
  * never raises on malformed/missing transcript.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from scripts.handoff import constants as C
from scripts.handoff import context_reminder


def _transcript(tmp_path: Path, tokens: int) -> Path:
    """Write a minimal transcript whose last assistant usage sums to `tokens`."""
    path = tmp_path / "transcript.jsonl"
    line = {
        "type": "assistant",
        "message": {
            "usage": {
                "input_tokens": tokens,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "output_tokens": 0,
            }
        },
    }
    path.write_text(json.dumps(line) + "\n", encoding="utf-8")
    return path


def _payload(tmp_path: Path, transcript: Path, *, session_id: str = "S1") -> dict:
    return {
        C.FIELD_TRANSCRIPT_PATH: str(transcript),
        C.FIELD_CWD: str(tmp_path),
        C.FIELD_SESSION_ID: session_id,
    }


def _run(monkeypatch, payload: dict) -> str:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert context_reminder.main() == 0
    return out.getvalue()


def test_silent_below_threshold(tmp_path: Path, monkeypatch):
    # 50% of a 200k window (default threshold 70%).
    transcript = _transcript(tmp_path, 100_000)
    assert _run(monkeypatch, _payload(tmp_path, transcript)).strip() == ""


def test_nudges_at_threshold(tmp_path: Path, monkeypatch):
    transcript = _transcript(tmp_path, 150_000)  # 75%
    out = _run(monkeypatch, _payload(tmp_path, transcript))
    data = json.loads(out)
    block = data[C.HOOK_OUTPUT_KEY]
    assert block[C.HOOK_EVENT_NAME_KEY] == C.STOP_EVENT
    assert "/handoff" in block[C.ADDITIONAL_CONTEXT_KEY]
    # Crucially non-blocking: no `decision` key anywhere.
    assert "decision" not in data


def test_deduped_within_same_band(tmp_path: Path, monkeypatch):
    transcript = _transcript(tmp_path, 150_000)  # 75% -> band 7
    assert _run(monkeypatch, _payload(tmp_path, transcript)).strip() != ""
    # Same session, still in band 7 -> silent.
    transcript2 = _transcript(tmp_path, 158_000)  # 79% -> still band 7
    assert _run(monkeypatch, _payload(tmp_path, transcript2)).strip() == ""


def test_nudges_again_after_next_band(tmp_path: Path, monkeypatch):
    assert _run(monkeypatch, _payload(tmp_path, _transcript(tmp_path, 150_000))).strip() != ""  # band 7
    # Climbs into band 8 (>=80%) -> nudge again.
    out = _run(monkeypatch, _payload(tmp_path, _transcript(tmp_path, 162_000)))
    assert out.strip() != ""


def test_separate_sessions_independent(tmp_path: Path, monkeypatch):
    transcript = _transcript(tmp_path, 150_000)
    assert _run(monkeypatch, _payload(tmp_path, transcript, session_id="A")).strip() != ""
    assert _run(monkeypatch, _payload(tmp_path, transcript, session_id="B")).strip() != ""


def test_env_threshold_override(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(C.REMINDER_THRESHOLD_ENV, "0.40")
    transcript = _transcript(tmp_path, 100_000)  # 50% -> above 40%
    assert _run(monkeypatch, _payload(tmp_path, transcript)).strip() != ""


def test_missing_transcript_is_silent(tmp_path: Path, monkeypatch):
    payload = {
        C.FIELD_TRANSCRIPT_PATH: str(tmp_path / "nope.jsonl"),
        C.FIELD_CWD: str(tmp_path),
        C.FIELD_SESSION_ID: "S1",
    }
    assert _run(monkeypatch, payload).strip() == ""


def test_transcript_without_usage_is_silent(tmp_path: Path, monkeypatch):
    path = tmp_path / "t.jsonl"
    path.write_text(json.dumps({"type": "assistant", "message": {}}) + "\n", encoding="utf-8")
    assert _run(monkeypatch, _payload(tmp_path, path)).strip() == ""


def test_malformed_stdin_never_raises(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("{{{ not json"))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert context_reminder.main() == 0
    assert out.getvalue().strip() == ""
