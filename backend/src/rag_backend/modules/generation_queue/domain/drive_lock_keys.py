"""Canonical executor lock-key builders shared with manual takeover."""

from __future__ import annotations

AUTOPILOT_KEY = "autopilot:{run_id}"
PROJECT_KEY = "project:{project_id}"


def project_key(project_id: str) -> str:
    """The drive-lock key of a carousel project."""
    return PROJECT_KEY.format(project_id=project_id)


def autopilot_lock_keys(run_id: str, project_id: str | None) -> list[str]:
    """The autopilot run key plus its currently attributed project key."""
    keys = [AUTOPILOT_KEY.format(run_id=run_id)]
    if project_id:
        keys.append(project_key(project_id))
    return keys


__all__ = ["autopilot_lock_keys", "project_key"]
