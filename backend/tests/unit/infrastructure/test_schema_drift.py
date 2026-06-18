"""Unit tests for the schema-vs-models drift detector (AE-0207).

Gherkin not applicable to the pure comparison core — this is the algorithmic
sensor for a DevOps safety net (no behavioral user scenario). The DB-touching
path is covered by the integration test against a real Postgres instance
(``tests/integration/test_schema_drift_live.py``). These tests pin the exact
failure class that hit prod: a mapped ORM column absent from the live schema.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table

from rag_backend.infrastructure.database.schema_drift import (
    DriftReport,
    MissingColumn,
    expected_columns,
    find_missing_columns,
)

_TABLE = "widgets"
_ID = "id"
_NAME = "name"
_NEW_COL = "origin"  # mirrors the real blog_posts.origin that 500'd prod


def _metadata_with(columns: tuple[str, ...]) -> MetaData:
    metadata = MetaData()
    Table(
        _TABLE,
        metadata,
        *[Column(name, Integer if name == _ID else String) for name in columns],
    )
    return metadata


def test_expected_columns_maps_table_to_its_columns() -> None:
    metadata = _metadata_with((_ID, _NAME))
    assert expected_columns(metadata) == {_TABLE: frozenset({_ID, _NAME})}


def test_matching_schema_has_no_drift() -> None:
    expected = {_TABLE: frozenset({_ID, _NAME})}
    actual = {_TABLE: frozenset({_ID, _NAME})}

    report = find_missing_columns(expected, actual)

    assert report.has_drift is False
    assert report.missing == ()
    assert "OK" in report.render()


def test_mapped_column_missing_from_db_is_drift() -> None:
    # The model gained ``origin`` (a new column); the live DB never got it.
    expected = {_TABLE: frozenset({_ID, _NAME, _NEW_COL})}
    actual = {_TABLE: frozenset({_ID, _NAME})}

    report = find_missing_columns(expected, actual)

    assert report.has_drift is True
    assert report.missing == (MissingColumn(_TABLE, _NEW_COL, "column absent"),)
    rendered = report.render()
    assert f"{_TABLE}.{_NEW_COL}" in rendered


def test_table_absent_reports_every_mapped_column() -> None:
    expected = {_TABLE: frozenset({_ID, _NAME})}
    actual: dict[str, frozenset[str]] = {}

    report = find_missing_columns(expected, actual)

    assert report.has_drift is True
    missing_cols = sorted(item.column for item in report.missing)
    assert missing_cols == [_ID, _NAME]
    assert all(item.reason == "table absent from live DB" for item in report.missing)


def test_extra_db_column_is_not_drift() -> None:
    # A column the DB has but the ORM does not map is NOT drift — create_all/
    # migrations only ever add; dropped-from-model columns are out of scope here.
    expected = {_TABLE: frozenset({_ID})}
    actual = {_TABLE: frozenset({_ID, "legacy_col"})}

    report = find_missing_columns(expected, actual)

    assert report.has_drift is False


def test_missing_columns_are_reported_in_stable_order() -> None:
    expected = {
        "b_table": frozenset({"z", "a"}),
        "a_table": frozenset({"y"}),
    }
    actual: dict[str, frozenset[str]] = {}

    report = find_missing_columns(expected, actual)

    located = [(item.table, item.column) for item in report.missing]
    assert located == [("a_table", "y"), ("b_table", "a"), ("b_table", "z")]


@pytest.mark.parametrize(
    ("missing", "expected_flag"),
    [((), False), ((MissingColumn(_TABLE, _NEW_COL, "column absent"),), True)],
)
def test_drift_report_has_drift_flag(
    missing: tuple[MissingColumn, ...], expected_flag: bool
) -> None:
    assert DriftReport(missing=missing).has_drift is expected_flag
