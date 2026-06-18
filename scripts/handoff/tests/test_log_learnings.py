"""Tests for the learnings-log helper and the pending-learnings count.

Behaviour under test (the kaizen signal side):
  * distils problems/landmines/decisions from the handoff into one JSONL record;
  * idempotent per handoff (same created_at not double-appended);
  * skips handoffs with no learnings;
  * pending count respects the kaizen watermark.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.handoff import constants as C
from scripts.handoff import log_learnings


def _write_handoff_json(cwd: Path, payload: dict) -> Path:
    directory = cwd / C.HANDOFF_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / C.HANDOFF_JSON_NAME
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _log_lines(cwd: Path) -> list[dict]:
    log = cwd / C.HANDOFF_DIR_NAME / C.LEARNINGS_LOG_NAME
    if not log.exists():
        return []
    return [json.loads(ln) for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _handoff(created_at: str = "2026-06-18T10:00:00") -> dict:
    return {
        "created_at": created_at,
        "mission": "do the thing",
        "problems": [{"problem": "p", "root_cause": "rc", "solution": "s", "status": "fixed"}],
        "landmines": ["do not merge to main casually"],
        "decisions": [{"decision": "d", "rationale": "r"}],
        "files_touched": ["x.py"],  # bookkeeping — must NOT land in the log record
    }


def test_appends_distilled_record(tmp_path: Path):
    _write_handoff_json(tmp_path, _handoff())
    assert log_learnings.run(str(tmp_path)) == 0
    records = _log_lines(tmp_path)
    assert len(records) == 1
    rec = records[0]
    assert rec["mission"] == "do the thing"
    assert rec["problems"][0]["root_cause"] == "rc"
    assert rec["landmines"] == ["do not merge to main casually"]
    assert "files_touched" not in rec  # only learning-bearing fields


def test_idempotent_same_created_at(tmp_path: Path):
    _write_handoff_json(tmp_path, _handoff())
    log_learnings.run(str(tmp_path))
    log_learnings.run(str(tmp_path))  # second call, same handoff
    assert len(_log_lines(tmp_path)) == 1


def test_new_handoff_appends_again(tmp_path: Path):
    _write_handoff_json(tmp_path, _handoff("2026-06-18T10:00:00"))
    log_learnings.run(str(tmp_path))
    _write_handoff_json(tmp_path, _handoff("2026-06-18T12:00:00"))
    log_learnings.run(str(tmp_path))
    assert len(_log_lines(tmp_path)) == 2


def test_skips_handoff_without_learnings(tmp_path: Path):
    _write_handoff_json(tmp_path, {"created_at": "t", "mission": "m"})
    assert log_learnings.run(str(tmp_path)) == 0
    assert _log_lines(tmp_path) == []


def test_missing_handoff_json_is_error(tmp_path: Path):
    assert log_learnings.run(str(tmp_path)) == 1


def test_pending_count_no_watermark(tmp_path: Path):
    _write_handoff_json(tmp_path, _handoff("2026-06-18T10:00:00"))
    log_learnings.run(str(tmp_path))
    _write_handoff_json(tmp_path, _handoff("2026-06-18T12:00:00"))
    log_learnings.run(str(tmp_path))
    assert C.pending_learnings_count(str(tmp_path)) == 2


def test_pending_count_respects_watermark(tmp_path: Path):
    _write_handoff_json(tmp_path, _handoff("2026-06-18T10:00:00"))
    log_learnings.run(str(tmp_path))
    _write_handoff_json(tmp_path, _handoff("2026-06-18T12:00:00"))
    log_learnings.run(str(tmp_path))
    # Kaizen processed up to the first record.
    (tmp_path / C.HANDOFF_DIR_NAME / C.KAIZEN_WATERMARK_NAME).write_text(
        "2026-06-18T10:00:00", encoding="utf-8"
    )
    assert C.pending_learnings_count(str(tmp_path)) == 1


def test_pending_count_zero_when_all_processed(tmp_path: Path):
    _write_handoff_json(tmp_path, _handoff("2026-06-18T10:00:00"))
    log_learnings.run(str(tmp_path))
    (tmp_path / C.HANDOFF_DIR_NAME / C.KAIZEN_WATERMARK_NAME).write_text(
        "2026-06-18T10:00:00", encoding="utf-8"
    )
    assert C.pending_learnings_count(str(tmp_path)) == 0


def test_pending_count_no_log_is_zero(tmp_path: Path):
    assert C.pending_learnings_count(str(tmp_path)) == 0
