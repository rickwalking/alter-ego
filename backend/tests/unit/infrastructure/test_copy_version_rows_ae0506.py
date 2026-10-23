"""Version rows read back into history entries, whatever the stored snapshot.

Feature: backend/tests/features/carousel_copy_versions_ae0506.feature
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy import Row

from rag_backend.infrastructure.database.copy_version_repository import (
    ERR_CREATED_AT_TYPE,
    _to_version,
)

AT = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)


def _row(*values: object) -> Row[tuple[object, ...]]:
    return cast("Row[tuple[object, ...]]", values)


def test_a_full_row_reads_back() -> None:
    """Scenario: Restoring a version saves its text as a new version."""
    version = _to_version(
        _row(
            3, {"field": "caption", "text": "t", "restored_from": 1}, "u1", AT, "Pedro"
        )
    )
    assert (version.version_number, version.field, version.text) == (3, "caption", "t")
    assert (version.author_id, version.author_name) == ("u1", "Pedro")
    assert version.restored_from == 1


def test_odd_snapshots_read_as_empty() -> None:
    """Scenario: Saving a changed caption stores the original and the new text as versions."""
    version = _to_version(_row(1, "not a dict", None, AT, None))
    assert (version.field, version.text, version.restored_from) == ("", "", None)
    assert (version.author_id, version.author_name) == (None, None)
    odd = _to_version(_row(2, {"restored_from": "1"}, None, AT, None))
    assert odd.restored_from is None


def test_a_row_without_a_timestamp_is_refused() -> None:
    """Scenario: Saving a changed caption stores the original and the new text as versions."""
    with pytest.raises(TypeError, match=ERR_CREATED_AT_TYPE):
        _to_version(_row(1, {}, None, "yesterday", None))
