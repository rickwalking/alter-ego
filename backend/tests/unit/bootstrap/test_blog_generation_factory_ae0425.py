"""Composition root of the blog writer run (AE-0425, ADR-0025).

Feature: backend/tests/features/blog_generate_ae0425.feature
Scenario: Drafting uses the fast model and judgement uses the reasoning model
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rag_backend.bootstrap import blog_generation
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.persona_rubric import (
    PersonaProfileModel,
)
from tests.blog_generation_fakes import FakeImageGenerator
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat


@dataclass
class _Roles:
    fast: FakeChat
    reasoning: FakeChat


@dataclass
class _Llm:
    role_models: _Roles


@dataclass
class _Provider:
    service: FakeImageGenerator


class _Registry:
    def __init__(self) -> None:
        self.resolved: list[tuple[str, str]] = []

    def resolve(self, model: str, style: str) -> _Provider:
        self.resolved.append((model, style))
        return _Provider(FakeImageGenerator())


class _Container:
    def __init__(self) -> None:
        log = CallLog()
        self.roles = _Roles(
            FakeChat(model_name="fast", log=log),
            FakeChat(model_name="reasoning", log=log),
        )
        self.registry = _Registry()

    def settings(self) -> object:
        return get_settings()

    def llm_service(self) -> _Llm:
        return _Llm(self.roles)

    def image_provider_registry(self) -> _Registry:
        return self.registry


def test_service_is_wired_with_the_role_models_and_gpt_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = _Container()
    monkeypatch.setattr(blog_generation, "get_container", lambda: container)
    monkeypatch.setattr(blog_generation, "get_session_maker", lambda: object())
    editor_image_service = object()
    monkeypatch.setattr(
        blog_generation, "build_blog_image_service", lambda: editor_image_service
    )
    service = blog_generation.build_generation_service(PersonaProfile())
    deps = service._deps
    assert deps.writer._models.fast is container.roles.fast
    assert deps.writer._models.reasoning is container.roles.reasoning
    assert (
        deps.timings.timeout_seconds == get_settings().blog_generation_timeout_seconds
    )
    # The one image path (AE-0424): the batch wraps the editor's service.
    assert deps.images._deps.images is editor_image_service
    assert deps.images._deps.concurrency == get_settings().blog_image_concurrency
    assert deps.image_cost_cap_usd == get_settings().blog_image_cost_cap


def test_reaper_and_paths() -> None:
    settings = get_settings()
    reaper = blog_generation.build_blog_generation_reaper(settings)
    assert reaper._stale.total_seconds() == settings.blog_generation_stale_seconds
    slug = blog_generation.standalone_slug("Agentes de IA: o que mudou")
    assert slug.startswith("agentes-de-ia-o-que-mudou-")


def test_settings_defaults() -> None:
    settings = get_settings()
    assert settings.blog_image_concurrency == 2
    assert settings.blog_image_cost_cap == 3.0
    assert settings.blog_generation_timeout_seconds == 900
    assert settings.blog_generation_stale_seconds == 180


@pytest.fixture
async def db(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'persona.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


async def test_persona_resolution_order(db: AsyncSession) -> None:
    # Background: the project persona "Pedro" is available
    pedro = PersonaProfileModel.from_entity(PersonaProfile(name="Pedro"))
    other = PersonaProfileModel.from_entity(PersonaProfile(name="Outra"))
    db.add_all([pedro, other])
    await db.commit()
    chosen = await blog_generation.resolve_persona(db, (None, str(other.id)))
    assert chosen.name == "Outra"
    fallback = await blog_generation.resolve_persona(db, ("missing-id",))
    assert fallback.name == "Pedro"


async def test_no_persona_falls_back_to_the_default_profile(db: AsyncSession) -> None:
    persona = await blog_generation.resolve_persona(db, ())
    assert persona.name == PersonaProfile().name
