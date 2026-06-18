"""Shared constants for the smart-handoff harness tooling.

These scripts run as Claude Code hooks (SessionStart injection + an optional
non-blocking Stop reminder). They are stdlib-only and never raise into the
harness: any failure must degrade to a no-op so a broken handoff never blocks a
session from starting or a turn from completing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# --- Filesystem layout (relative to the repo / cwd the hook runs in) ----------
HANDOFF_DIR_NAME = ".agent/handoff"
HANDOFF_MARKDOWN_NAME = "HANDOFF-latest.md"
HANDOFF_JSON_NAME = "HANDOFF-latest.json"
CONSUMED_FILE_NAME = ".consumed"
REMINDER_STATE_FILE_NAME = ".reminder"
# Append-only kaizen signal: one distilled learnings record per handoff.
LEARNINGS_LOG_NAME = "learnings-log.jsonl"
# Watermark: `created_at` of the newest learnings record kaizen has processed.
KAIZEN_WATERMARK_NAME = ".kaizen-watermark"

# --- SessionStart `source` values (Claude Code hooks contract) ----------------
SOURCE_STARTUP = "startup"
SOURCE_RESUME = "resume"
SOURCE_CLEAR = "clear"
SOURCE_COMPACT = "compact"
# We inject on every source EXCEPT compact: compaction keeps the SAME session,
# which already holds the (about-to-be-summarised) context, so re-injecting the
# handoff there is redundant and risks a self-injection loop.
INJECT_SOURCES = frozenset({SOURCE_STARTUP, SOURCE_RESUME, SOURCE_CLEAR})

# --- Hook output contract (verbatim field names from the hooks docs) ----------
HOOK_OUTPUT_KEY = "hookSpecificOutput"
HOOK_EVENT_NAME_KEY = "hookEventName"
ADDITIONAL_CONTEXT_KEY = "additionalContext"
SESSION_START_EVENT = "SessionStart"
STOP_EVENT = "Stop"

# --- Stdin field names --------------------------------------------------------
FIELD_SOURCE = "source"
FIELD_SESSION_ID = "session_id"
FIELD_CWD = "cwd"
FIELD_TRANSCRIPT_PATH = "transcript_path"

# --- Context-window accounting (mirrors statusline-pitao.py) ------------------
# Total window in tokens. Configurable because the active model may be a 200k or
# a 1M-context build; default matches the user's existing statusline calibration.
DEFAULT_CONTEXT_WINDOW = 200_000
CONTEXT_WINDOW_ENV = "HANDOFF_CONTEXT_WINDOW"

# Stop-hook reminder fires at/above this fraction of the window, then again each
# time utilisation climbs another REMINDER_STEP. Tunable via env.
DEFAULT_REMINDER_THRESHOLD = 0.70
REMINDER_THRESHOLD_ENV = "HANDOFF_REMINDER_THRESHOLD"
REMINDER_STEP = 0.10

# usage sub-fields summed to approximate live context utilisation
USAGE_FIELDS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)

# Practical ceiling for injected context. additionalContext has no documented
# hard limit, but a multi-hundred-KB blob is wasteful and may not be attended to;
# truncate with a pointer to the on-disk file instead.
MAX_INJECT_CHARS = 24_000


def handoff_dir(cwd: str) -> Path:
    """Return the handoff directory for a given working directory."""
    return Path(cwd) / HANDOFF_DIR_NAME


def context_window() -> int:
    """Resolved context-window size in tokens (env override or default)."""
    raw = os.environ.get(CONTEXT_WINDOW_ENV, "")
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return DEFAULT_CONTEXT_WINDOW


def reminder_threshold() -> float:
    """Resolved reminder threshold fraction (env override or default)."""
    raw = os.environ.get(REMINDER_THRESHOLD_ENV, "")
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_REMINDER_THRESHOLD
    if 0.0 < value < 1.0:
        return value
    return DEFAULT_REMINDER_THRESHOLD


def pending_learnings_count(cwd: str) -> int:
    """Count learnings records newer than the kaizen watermark (0 on any error).

    Used to nudge a fresh session to run `/kaizen-skill session`. A record is
    "pending" if its `created_at` sorts after the watermark; with no watermark,
    every record is pending. Never raises — returns 0 on missing/garbled files.
    """
    directory = handoff_dir(cwd)
    log_path = directory / LEARNINGS_LOG_NAME
    if not log_path.is_file():
        return 0
    try:
        lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        return 0

    watermark = ""
    watermark_path = directory / KAIZEN_WATERMARK_NAME
    if watermark_path.is_file():
        try:
            watermark = watermark_path.read_text(encoding="utf-8").strip()
        except OSError:
            watermark = ""

    pending = 0
    for line in lines:
        try:
            created_at = str(json.loads(line).get("created_at", ""))
        except json.JSONDecodeError:
            continue
        if not watermark or created_at > watermark:
            pending += 1
    return pending
