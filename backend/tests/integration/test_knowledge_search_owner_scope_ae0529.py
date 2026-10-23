"""The knowledge search API reads personal knowledge only for the site owner."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from rag_backend.domain.constants.namespaces import NAMESPACE_PERSONAL, NAMESPACE_PUBLIC
from rag_backend.domain.models import UserRole
from rag_backend.infrastructure.config.settings import Settings, get_settings
from tests.integration.test_knowledge_safety_net import KnowledgeEnv, kb_env

__all__ = ["kb_env"]


def _site_owner(env: KnowledgeEnv, user_id: str) -> None:
    settings: Settings = get_settings().model_copy(
        update={"autopilot_owner_user_id": user_id}
    )
    env.container.settings.override(settings)


@pytest.fixture(autouse=True)
def _reset_site_owner(kb_env: KnowledgeEnv) -> Iterator[None]:
    yield
    kb_env.container.settings.reset_override()


def _searched_prefix(env: KnowledgeEnv) -> str | None:
    retriever = env.container.retriever()
    return retriever.retrieve.await_args.args[0].namespace_prefix


@pytest.mark.integration
class TestSearchOwnerScope:
    async def test_site_owner_searches_personal_and_public(
        self, kb_env: KnowledgeEnv
    ) -> None:
        """Scenario: The knowledge search API reads personal knowledge only for the site owner"""
        _site_owner(kb_env, str(kb_env.owner.id))
        kb_env.override_retriever([])
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.post("/api/search", json={"query": "career"})

        assert response.status_code == 200
        assert _searched_prefix(kb_env) == NAMESPACE_PERSONAL

    @pytest.mark.parametrize("role", [UserRole.EDITOR, UserRole.ADMIN])
    async def test_other_users_search_public_only(
        self, kb_env: KnowledgeEnv, role: UserRole
    ) -> None:
        """Scenario: The knowledge search API reads personal knowledge only for the site owner"""
        _site_owner(kb_env, str(kb_env.owner.id))
        other = await kb_env.make_user(f"kb-search-{role.value}@integration.test", role)
        kb_env.override_retriever([])
        async with kb_env.client_for(other) as client:
            response = await client.get("/api/search", params={"query": "career"})

        assert response.status_code == 200
        assert _searched_prefix(kb_env) == NAMESPACE_PUBLIC

    async def test_without_a_site_owner_the_owner_searches_public_only(
        self, kb_env: KnowledgeEnv
    ) -> None:
        """Scenario: Without a configured site owner every chat reads public knowledge only"""
        _site_owner(kb_env, "")
        kb_env.override_retriever([])
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.post("/api/search", json={"query": "career"})

        assert response.status_code == 200
        assert _searched_prefix(kb_env) == NAMESPACE_PUBLIC
