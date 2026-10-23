"""Searching conversations by title is literal, case-insensitive and owner-scoped.

Feature file: tests/features/conversation_search.feature
"""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from rag_backend.infrastructure.database.conversation_repository import (
    TITLE_SEARCH_ESCAPE,
    PostgresConversationRepository,
    title_search_pattern,
)
from rag_backend.infrastructure.database.models.conversation import ConversationModel


@pytest.mark.parametrize(
    ("search", "pattern"),
    [
        ("pauta", "%pauta%"),
        ("50%", "%50\\%%"),
        ("a_b", "%a\\_b%"),
        ("c:\\temp", "%c:\\\\temp%"),
    ],
)
def test_search_pattern_matches_special_characters_literally(
    search: str, pattern: str
) -> None:
    """``%``, ``_`` and the escape character never act as wildcards.

    Scenario: Searching conversations finds older ones too
    """
    assert TITLE_SEARCH_ESCAPE == "\\"
    assert title_search_pattern(search) == pattern


def _compiled(search: str | None) -> str:
    stmt = select(ConversationModel).where(ConversationModel.owner_id == str(uuid4()))
    filtered = PostgresConversationRepository._apply_search_filter(stmt, search)
    return str(
        filtered.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def test_search_filters_titles_case_insensitively_within_the_owner() -> None:
    """The filter is an escaped ILIKE added to the owner's query.

    Scenario: Searching conversations finds older ones too
    """
    sql = _compiled("Pauta_1")

    assert "ILIKE '%%Pauta\\_1%%' ESCAPE '\\'" in sql.replace("\\\\", "\\")
    assert "owner_id" in sql


@pytest.mark.parametrize("search", [None, "", "   "])
def test_blank_search_adds_no_filter(search: str | None) -> None:
    """No search text, no title filter.

    Scenario: Searching conversations finds older ones too
    """
    assert "ILIKE" not in _compiled(search)
