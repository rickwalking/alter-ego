"""Graph API failure the publisher raises and the publish job classifies."""

from __future__ import annotations


class InstagramGraphError(Exception):
    """One failed Graph call, already marked transient or permanent."""

    def __init__(self, *, status_code: int, error_code: str, transient: bool) -> None:
        super().__init__(error_code)
        self.status_code = status_code
        self.error_code = error_code
        self.transient = transient
