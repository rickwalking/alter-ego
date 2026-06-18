#!/usr/bin/env python3
"""Stop hook: a non-blocking nudge to checkpoint when context grows large.

This is the SAFE version of "auto-detect a full context window". It NEVER blocks
(blocking a Stop hook forces Claude to keep generating, which is not what we
want) and NEVER forces a tool call. It simply parses the transcript to estimate
context utilisation — the same trick the statusline uses — and, once utilisation
crosses a threshold, injects a one-time ``additionalContext`` reminder suggesting
the user run `/handoff` then `/clear`.

De-duplicated per session so it nudges at the threshold and then again only after
utilisation climbs another step (default +10%), rather than on every turn.

Guarantees: stdlib-only, never raises into the harness (always exit 0), and
silent on any parse error or below-threshold reading.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__:
    from scripts.handoff import constants as C
else:  # pragma: no cover - exercised only via direct CLI invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.handoff import constants as C


def _read_payload() -> dict[str, str]:
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _latest_usage_tokens(transcript_path: str) -> int:
    """Sum the most recent assistant message's usage fields (0 if unavailable)."""
    path = Path(transcript_path)
    if not path.is_file():
        return 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "assistant":
            continue
        usage = obj.get("message", {}).get("usage")
        if not isinstance(usage, dict):
            continue
        if not all(field in usage for field in C.USAGE_FIELDS):
            continue
        return sum(int(usage.get(field, 0) or 0) for field in C.USAGE_FIELDS)
    return 0


def _already_reminded_at(state_path: Path, session_id: str, band: int) -> bool:
    """True if this session was already reminded at >= `band` (in step units)."""
    if not state_path.exists():
        return False
    try:
        records = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(records, dict):
        return False
    previous = records.get(session_id)
    return isinstance(previous, int) and previous >= band


def _record_band(state_path: Path, session_id: str, band: int) -> None:
    try:
        records = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(records, dict):
            records = {}
    except (OSError, json.JSONDecodeError):
        records = {}
    records[session_id] = band
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(records), encoding="utf-8")
    except OSError:
        pass


def _message(pct: int) -> str:
    return (
        f"Context window is ~{pct}% full. Consider running `/handoff` to "
        "checkpoint this session's learnings, decisions and current state to "
        "`.agent/handoff/`, then `/clear` to continue in a fresh context "
        "(the SessionStart hook will re-seed it). Do this before auto-compact "
        "fires, so the handoff is written from full context."
    )


def _emit(message: str) -> None:
    output = {
        C.HOOK_OUTPUT_KEY: {
            C.HOOK_EVENT_NAME_KEY: C.STOP_EVENT,
            C.ADDITIONAL_CONTEXT_KEY: message,
        }
    }
    sys.stdout.write(json.dumps(output))


def run(payload: dict[str, str]) -> int:
    transcript_path = payload.get(C.FIELD_TRANSCRIPT_PATH, "")
    if not transcript_path:
        return 0

    tokens = _latest_usage_tokens(transcript_path)
    if tokens <= 0:
        return 0

    window = C.context_window()
    fraction = tokens / window
    threshold = C.reminder_threshold()
    if fraction < threshold:
        return 0

    # Quantise into step-sized bands so we nudge at the threshold and then once
    # per additional step, not every turn.
    band = int(fraction / C.REMINDER_STEP)
    cwd = payload.get(C.FIELD_CWD) or str(Path.cwd())
    session_id = payload.get(C.FIELD_SESSION_ID, "")
    state_path = C.handoff_dir(cwd) / C.REMINDER_STATE_FILE_NAME
    if session_id and _already_reminded_at(state_path, session_id, band):
        return 0

    _emit(_message(int(fraction * 100)))
    if session_id:
        _record_band(state_path, session_id, band)
    return 0


def main() -> int:
    try:
        return run(_read_payload())
    except Exception:  # noqa: BLE001 - last-resort guard; never break the turn
        return 0


if __name__ == "__main__":
    sys.exit(main())
