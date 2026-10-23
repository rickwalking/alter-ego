"""Searching conversations through the API: owner-scoped and literal.

Feature file: tests/features/conversation_search.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import Response

from tests.integration.conversation_access_support import (
    CALLER_OTHER,
    CALLER_OWNER,
    OwnershipEnv,
    ownership_env,
    reset_rate_limits,
)

_OWNER_TITLES = (
    "Pauta de outubro",
    "50% off ideas",
    "500 visitors",
    "a_b plan",
    "axb plan",
)


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    reset_rate_limits()


@pytest_asyncio.fixture
async def env(tmp_path: Path) -> AsyncIterator[OwnershipEnv]:
    """The shared app, plus titled conversations for the owner and another user."""
    async with ownership_env(tmp_path) as built:
        async with built.client(CALLER_OWNER) as owner:
            for title in _OWNER_TITLES:
                created = await owner.post("/", json={"title": title})
                assert created.status_code == 201
        async with built.client(CALLER_OTHER) as other:
            created = await other.post("/", json={"title": "Pauta secreta"})
            assert created.status_code == 201
        yield built


def _titles(response: Response) -> list[str]:
    assert response.status_code == 200
    return sorted(item["title"] for item in response.json()["items"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("search", "titles"),
    [
        ("PAUTA", ["Pauta de outubro"]),
        ("50%", ["50% off ideas"]),
        ("a_b", ["a_b plan"]),
    ],
)
async def test_search_matches_only_the_owners_titles_literally(
    env: OwnershipEnv, search: str, titles: list[str]
) -> None:
    """Case-insensitive, only the caller's, and ``%``/``_`` are not wildcards.

    Scenario: Searching conversations finds older ones too
    """
    async with env.client(CALLER_OWNER) as owner:
        found = await owner.get("/", params={"search": search, "limit": 100})

    assert _titles(found) == titles
    assert found.json()["total"] == len(titles)


@pytest.mark.asyncio
async def test_search_longer_than_the_limit_is_rejected(env: OwnershipEnv) -> None:
    """A search over 100 characters is a validation error.

    Scenario: Searching conversations finds older ones too
    """
    async with env.client(CALLER_OWNER) as owner:
        response = await owner.get("/", params={"search": "x" * 101})

    assert response.status_code == 422
