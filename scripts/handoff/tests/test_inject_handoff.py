"""Tests for the SessionStart handoff-injection hook.

Behaviour under test (the read-side of smart handoff):
  * injects the latest handoff into a fresh/resumed/cleared session;
  * skips compaction (same session already holds the context);
  * dedupes per (handoff-content, session) — at most once per handoff per session;
  * re-offers a NEWLY written handoff (different content hash) to everyone;
  * is cwd-scoped and never raises on malformed input.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from scripts.handoff import constants as C
from scripts.handoff import inject_handoff


def _write_handoff(cwd: Path, text: str = "# Handoff\nprior state") -> Path:
    directory = cwd / C.HANDOFF_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    md = directory / C.HANDOFF_MARKDOWN_NAME
    md.write_text(text, encoding="utf-8")
    return md


def _payload(cwd: Path, *, source: str = C.SOURCE_STARTUP, session_id: str = "S1") -> dict:
    return {
        C.FIELD_SOURCE: source,
        C.FIELD_CWD: str(cwd),
        C.FIELD_SESSION_ID: session_id,
    }


def _run(monkeypatch, payload: dict) -> str:
    """Drive main() with a stdin payload; return captured stdout."""
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert inject_handoff.main() == 0
    return out.getvalue()


def _injected_context(stdout: str) -> str | None:
    if not stdout.strip():
        return None
    data = json.loads(stdout)
    return data[C.HOOK_OUTPUT_KEY][C.ADDITIONAL_CONTEXT_KEY]


def test_injects_handoff_on_fresh_session(tmp_path: Path, monkeypatch):
    _write_handoff(tmp_path, "# Handoff\nthe prior session state")
    out = _run(monkeypatch, _payload(tmp_path))
    ctx = _injected_context(out)
    assert ctx is not None
    assert "the prior session state" in ctx
    assert C.HANDOFF_JSON_NAME in ctx  # points at the machine-readable twin


@pytest.mark.parametrize("source", [C.SOURCE_STARTUP, C.SOURCE_RESUME, C.SOURCE_CLEAR])
def test_injects_for_all_non_compact_sources(tmp_path: Path, monkeypatch, source: str):
    _write_handoff(tmp_path)
    out = _run(monkeypatch, _payload(tmp_path, source=source, session_id=f"sess-{source}"))
    assert _injected_context(out) is not None


def test_skips_compaction_source(tmp_path: Path, monkeypatch):
    _write_handoff(tmp_path)
    out = _run(monkeypatch, _payload(tmp_path, source=C.SOURCE_COMPACT))
    assert out.strip() == ""


def test_no_handoff_file_is_silent(tmp_path: Path, monkeypatch):
    out = _run(monkeypatch, _payload(tmp_path))
    assert out.strip() == ""


def test_empty_handoff_file_is_silent(tmp_path: Path, monkeypatch):
    _write_handoff(tmp_path, "   \n  ")
    out = _run(monkeypatch, _payload(tmp_path))
    assert out.strip() == ""


def test_dedupes_same_session_same_handoff(tmp_path: Path, monkeypatch):
    _write_handoff(tmp_path)
    first = _run(monkeypatch, _payload(tmp_path, session_id="S1"))
    assert _injected_context(first) is not None
    # Same session resumes — must NOT be re-injected.
    second = _run(monkeypatch, _payload(tmp_path, source=C.SOURCE_RESUME, session_id="S1"))
    assert second.strip() == ""


def test_different_session_still_gets_same_handoff(tmp_path: Path, monkeypatch):
    _write_handoff(tmp_path)
    _run(monkeypatch, _payload(tmp_path, session_id="S1"))
    out = _run(monkeypatch, _payload(tmp_path, session_id="S2"))
    assert _injected_context(out) is not None


def test_new_handoff_resets_dedupe(tmp_path: Path, monkeypatch):
    _write_handoff(tmp_path, "# Handoff\nversion one")
    first = _run(monkeypatch, _payload(tmp_path, session_id="S1"))
    assert _injected_context(first) is not None
    assert _run(monkeypatch, _payload(tmp_path, source=C.SOURCE_RESUME, session_id="S1")).strip() == ""
    # A new checkpoint is written -> content hash changes -> S1 may consume again.
    _write_handoff(tmp_path, "# Handoff\nversion two")
    out = _run(monkeypatch, _payload(tmp_path, source=C.SOURCE_RESUME, session_id="S1"))
    ctx = _injected_context(out)
    assert ctx is not None
    assert "version two" in ctx


def test_cwd_scoped(tmp_path: Path, monkeypatch):
    other = tmp_path / "other-repo"
    other.mkdir()
    _write_handoff(tmp_path, "# Handoff\nrepo A state")
    # Session whose cwd is a different repo with no handoff -> silent.
    out = _run(monkeypatch, _payload(other))
    assert out.strip() == ""


def test_large_handoff_is_truncated(tmp_path: Path, monkeypatch):
    big = "# Handoff\n" + ("x" * (C.MAX_INJECT_CHARS + 5000))
    _write_handoff(tmp_path, big)
    ctx = _injected_context(_run(monkeypatch, _payload(tmp_path)))
    assert ctx is not None
    assert "truncated" in ctx
    assert len(ctx) < len(big) + 2000


def test_malformed_stdin_never_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json at all {{{"))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert inject_handoff.main() == 0
    assert out.getvalue().strip() == ""


def test_missing_session_id_still_injects(tmp_path: Path, monkeypatch):
    _write_handoff(tmp_path)
    payload = {C.FIELD_SOURCE: C.SOURCE_STARTUP, C.FIELD_CWD: str(tmp_path)}
    out = _run(monkeypatch, payload)
    assert _injected_context(out) is not None


# --- kaizen nudge integration ------------------------------------------------

def _write_learnings(tmp_path: Path, created_at: str = "2026-06-18T10:00:00") -> None:
    directory = tmp_path / C.HANDOFF_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    rec = {"created_at": created_at, "mission": "m", "problems": [{"problem": "p"}]}
    (directory / C.LEARNINGS_LOG_NAME).write_text(json.dumps(rec) + "\n", encoding="utf-8")


def test_nudge_rides_with_handoff(tmp_path: Path, monkeypatch):
    _write_handoff(tmp_path, "# Handoff\nstate")
    _write_learnings(tmp_path)
    ctx = _injected_context(_run(monkeypatch, _payload(tmp_path)))
    assert ctx is not None
    assert "state" in ctx
    assert "/kaizen-skill session" in ctx


def test_standalone_nudge_when_no_handoff(tmp_path: Path, monkeypatch):
    # No handoff file, but pending learnings -> emit just the nudge.
    _write_learnings(tmp_path)
    ctx = _injected_context(_run(monkeypatch, _payload(tmp_path)))
    assert ctx is not None
    assert "/kaizen-skill session" in ctx
    assert "Kaizen pending" in ctx


def test_no_nudge_when_watermark_current(tmp_path: Path, monkeypatch):
    _write_learnings(tmp_path, "2026-06-18T10:00:00")
    (tmp_path / C.HANDOFF_DIR_NAME / C.KAIZEN_WATERMARK_NAME).write_text(
        "2026-06-18T10:00:00", encoding="utf-8"
    )
    # No handoff, no pending learnings -> fully silent.
    assert _run(monkeypatch, _payload(tmp_path)).strip() == ""


def test_no_nudge_on_compact(tmp_path: Path, monkeypatch):
    _write_handoff(tmp_path)
    _write_learnings(tmp_path)
    assert _run(monkeypatch, _payload(tmp_path, source=C.SOURCE_COMPACT)).strip() == ""
