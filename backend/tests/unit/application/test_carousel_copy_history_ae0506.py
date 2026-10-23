"""Which versions a caption / LinkedIn save records.

Feature: backend/tests/features/carousel_copy_versions_ae0506.feature
"""

from __future__ import annotations

from rag_backend.application.services.carousel.carousel_copy_history import (
    CopyChange,
    versions_for_change,
)
from rag_backend.domain.models.carousel_copy_version import NewCopyVersion

AUTHOR = "user-1"
TEXTS = {"caption": "c0", "linkedin_post_pt": "p0", "linkedin_post_en": None}


def test_first_change_keeps_the_replaced_text_first() -> None:
    """Scenario: Saving a changed caption stores the original and the new text as versions."""
    change = CopyChange(
        before=TEXTS, after={**TEXTS, "caption": "c1"}, author_id=AUTHOR
    )
    assert versions_for_change(change, set()) == [
        NewCopyVersion(field="caption", text="c0", author_id=None, summary="original"),
        NewCopyVersion(field="caption", text="c1", author_id=AUTHOR, summary="edit"),
    ]


def test_a_versioned_text_records_only_the_new_text() -> None:
    """Scenario: A later edit of the same text stores only the new text."""
    change = CopyChange(
        before=TEXTS, after={**TEXTS, "caption": "c2"}, author_id=AUTHOR
    )
    assert versions_for_change(change, {"caption"}) == [
        NewCopyVersion(field="caption", text="c2", author_id=AUTHOR, summary="edit"),
    ]


def test_an_empty_replaced_text_is_not_kept() -> None:
    """Scenario: Saving a changed caption stores the original and the new text as versions."""
    change = CopyChange(
        before=TEXTS, after={**TEXTS, "linkedin_post_en": "e1"}, author_id=AUTHOR
    )
    assert versions_for_change(change, set()) == [
        NewCopyVersion(
            field="linkedin_post_en", text="e1", author_id=AUTHOR, summary="edit"
        ),
    ]


def test_unchanged_texts_record_nothing() -> None:
    """Scenario: A text that did not change stores no version."""
    change = CopyChange(before=TEXTS, after=dict(TEXTS), author_id=AUTHOR)
    assert versions_for_change(change, set()) == []


def test_a_restore_is_recorded_as_a_restore() -> None:
    """Scenario: Restoring a version saves its text as a new version."""
    change = CopyChange(
        before=TEXTS,
        after={**TEXTS, "linkedin_post_pt": "p-old"},
        author_id=AUTHOR,
        restored_from=1,
    )
    assert versions_for_change(change, {"linkedin_post_pt"}) == [
        NewCopyVersion(
            field="linkedin_post_pt",
            text="p-old",
            author_id=AUTHOR,
            summary="restore",
            restored_from=1,
        ),
    ]


def test_an_empty_replaced_text_keeps_no_original() -> None:
    """Scenario: Saving a changed caption stores the original and the new text as versions."""
    change = CopyChange(
        before={**TEXTS, "caption": ""},
        after={**TEXTS, "caption": "c1"},
        author_id=AUTHOR,
    )
    assert versions_for_change(change, set()) == [
        NewCopyVersion(field="caption", text="c1", author_id=AUTHOR, summary="edit"),
    ]


def test_several_texts_are_recorded_in_field_order() -> None:
    """Scenario: One save of several texts stores a version of each."""
    before = {"caption": "c0", "linkedin_post_pt": "p0", "linkedin_post_en": "e0"}
    after = {"caption": "c1", "linkedin_post_pt": "p0", "linkedin_post_en": "e1"}
    change = CopyChange(before=before, after=after, author_id=AUTHOR)
    assert [
        (v.field, v.text) for v in versions_for_change(change, {"linkedin_post_en"})
    ] == [
        ("caption", "c0"),
        ("caption", "c1"),
        ("linkedin_post_en", "e1"),
    ]
