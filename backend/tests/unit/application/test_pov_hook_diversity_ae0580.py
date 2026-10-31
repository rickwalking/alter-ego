"""POV hook voice diversity: v2 prompt, rotation and recent openings.

Gherkin: tests/features/carousel_pov_hook_diversity_ae0580.feature
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents import pov_outline_mixin
from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.carousel.content_mode_brief import (
    ContentModeBrief,
    brief_for_project,
)
from rag_backend.application.services.carousel.outline_by_mode import (
    HookSelection,
    attach_hook_and_checks,
)
from rag_backend.application.services.carousel.recent_hooks import (
    drop_reused_openings,
    load_recent_hooks,
)
from rag_backend.domain.constants.pov_prompts import RECENT_HOOK_LIMIT
from rag_backend.domain.models import CarouselProject, CarouselSlide
from rag_backend.domain.models.pov_prompts import PovHookRequest, PovThesis
from rag_backend.domain.protocols.recent_hooks import RecentHookQuery
from rag_backend.infrastructure.database.carousel_recent_hooks import (
    SqlRecentHookReader,
)
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)

_THESIS = "A IA escreve código. Quem decide o que construir ainda é você."
_RECENT = ["Opinião impopular: reuniões resolvem", "O que eu faço antes de codar"]
_HOOKS = ["Gancho um", "Gancho dois", "Gancho três", "Gancho quatro", "Gancho cinco"]
_OUTLINE = [{"title": "Slide 1", "key_points": ["p"]}]


def _brief(hook_text: str = "") -> ContentModeBrief:
    project = CarouselProject(topic="Julgamento técnico", audience="Devs", niche="IA")
    project.content_mode = "pov"
    project.presentation_policy_version = "pov_hook_v1"
    project.pov_thesis = _THESIS
    project.hook_text = hook_text or None
    return brief_for_project(project)


def _render_hook(recent_hooks: list[str]) -> str:
    text, _ = render_prompt(
        "carousel_pov",
        "hook",
        variables={
            "thesis": _THESIS,
            "personal_proof": "",
            "pov_format": "opiniao",
            "topic": "Julgamento técnico",
            "audience": "Devs",
            "recent_hooks": recent_hooks,
        },
        version="v2",
    )
    return text


@pytest.mark.unit
class TestHookPromptV2:
    # Scenario: Recent openings are listed and forbidden
    def test_recent_openings_listed_and_forbidden(self) -> None:
        text = _render_hook(list(_RECENT))
        for opening in _RECENT:
            assert opening in text
        assert "NÃO reutilize" in text

    # Scenario: No recent openings, no exclusion block
    def test_no_recent_openings_no_block(self) -> None:
        text = _render_hook([])
        assert "NÃO reutilize" not in text
        assert "Aberturas usadas" not in text
        assert "nunca invente" in text.lower()

    # Scenario: The hook call renders v2 with the recent openings
    @pytest.mark.asyncio
    async def test_mixin_renders_v2_with_recent_hooks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, object] = {}

        def _capture(
            domain: str,
            name: str,
            variables: dict[str, object],
            *,
            version: str,
        ) -> tuple[str, dict[str, object]]:
            seen.update(
                {
                    "domain": domain,
                    "name": name,
                    "version": version,
                    "variables": variables,
                }
            )
            raise RuntimeError("stop")

        monkeypatch.setattr(pov_outline_mixin, "render_prompt", _capture)
        agent = OutlineAgent.__new__(OutlineAgent)
        request = PovHookRequest(
            topic="t",
            audience="a",
            pov=PovThesis(thesis=_THESIS),
            recent_hooks=tuple(_RECENT),
        )
        with pytest.raises(RuntimeError):
            await agent.hook_candidates(request)
        assert seen["version"] == "v2"
        variables = seen["variables"]
        assert isinstance(variables, dict)
        assert variables["recent_hooks"] == _RECENT


@pytest.mark.unit
class TestHookRotation:
    # Scenario: The chosen hook rotates across the candidates
    def test_consecutive_carousels_do_not_repeat(self) -> None:
        chosen = [
            str(
                attach_hook_and_checks(
                    _OUTLINE, _brief(), HookSelection(candidates=list(_HOOKS), seed=seed)
                )[0]["title"]
            )
            for seed in range(len(_HOOKS))
        ]
        assert len(set(chosen)) == len(_HOOKS)

    def test_same_seed_same_pick(self) -> None:
        first = attach_hook_and_checks(_OUTLINE, _brief(), HookSelection(list(_HOOKS), 7))
        second = attach_hook_and_checks(_OUTLINE, _brief(), HookSelection(list(_HOOKS), 7))
        assert first[0]["title"] == second[0]["title"]

    # Scenario: A candidate repeating a recent opening is dropped
    def test_reused_opening_is_dropped_and_never_chosen(self) -> None:
        candidates = ["Opinião impopular: reuniões resolvem", "Gancho novo"]
        recent = ("opinião impopular:   reuniões resolvem",)
        assert drop_reused_openings(candidates, recent) == ["Gancho novo"]
        outline = attach_hook_and_checks(
            _OUTLINE,
            _brief(),
            HookSelection(candidates=drop_reused_openings(candidates, recent), seed=0),
        )
        assert outline[0]["title"] == "Gancho novo"
        assert outline[0]["hook_candidates"] == ["Gancho novo"]

    def test_all_reused_keeps_the_candidates(self) -> None:
        candidates = ["Gancho um"]
        assert drop_reused_openings(candidates, ("gancho um",)) == candidates

    def test_seed_zero_keeps_the_first_candidate(self) -> None:
        outline = attach_hook_and_checks(_OUTLINE, _brief(), HookSelection(list(_HOOKS)))
        assert outline[0]["title"] == "Gancho um"

    # Scenario: The owner's saved hook still wins
    def test_saved_hook_wins_over_rotation(self) -> None:
        outline = attach_hook_and_checks(
            _OUTLINE,
            _brief(hook_text="Meu gancho salvo"),
            HookSelection(list(_HOOKS), seed=3),
        )
        assert outline[0]["title"] == "Meu gancho salvo"

    def test_no_candidates_keeps_title(self) -> None:
        outline = attach_hook_and_checks(_OUTLINE, _brief(), HookSelection([], seed=2))
        assert outline[0]["title"] == "Slide 1"


def _project(owner_id: str | None, created_days_ago: int) -> CarouselProject:
    project = CarouselProject(topic="Tema", audience="Devs", niche="IA")
    project.owner_id = owner_id
    project.created_at -= timedelta(days=created_days_ago)
    return project


async def _with_hook(
    repo: PostgresCarouselRepository, project: CarouselProject, heading: str
) -> None:
    await repo.create_slide(
        CarouselSlide(
            project_id=project.id,
            slide_number=1,
            slide_type="intro",
            heading=heading,
            body="corpo",
        )
    )


@pytest.mark.unit
class TestRecentHookHeadings:
    # Scenario: Recent openings come from the owner's other carousels
    @pytest.mark.asyncio
    async def test_owner_recent_headings_newest_first(
        self, db_session: AsyncSession, carousel_repository: PostgresCarouselRepository
    ) -> None:
        owner = str(uuid4())
        current = await carousel_repository.create_project(_project(owner, 0))
        older = await carousel_repository.create_project(_project(owner, 2))
        newer = await carousel_repository.create_project(_project(owner, 1))
        foreign = await carousel_repository.create_project(_project(str(uuid4()), 1))
        repo = carousel_repository
        await _with_hook(repo, older, "Abertura antiga")
        await _with_hook(repo, newer, "Abertura recente")
        await _with_hook(repo, foreign, "Abertura de outro dono")
        await _with_hook(repo, current, "Gancho do projeto atual")

        recent = await load_recent_hooks(SqlRecentHookReader(db_session), str(current.id))

        assert recent.headings == ("Abertura recente", "Abertura antiga")
        assert recent.total == 2

    @pytest.mark.asyncio
    async def test_limit_caps_the_list(
        self, db_session: AsyncSession, carousel_repository: PostgresCarouselRepository
    ) -> None:
        owner = str(uuid4())
        current = await carousel_repository.create_project(_project(owner, 0))
        for days in range(1, RECENT_HOOK_LIMIT + 3):
            project = await carousel_repository.create_project(_project(owner, days))
            await _with_hook(carousel_repository, project, f"Abertura {days}")

        recent = await load_recent_hooks(SqlRecentHookReader(db_session), str(current.id))

        assert len(recent.headings) == RECENT_HOOK_LIMIT
        assert recent.total == RECENT_HOOK_LIMIT + 2

    @pytest.mark.asyncio
    async def test_skips_projects_without_a_hook_slide(
        self, db_session: AsyncSession, carousel_repository: PostgresCarouselRepository
    ) -> None:
        owner = str(uuid4())
        current = await carousel_repository.create_project(_project(owner, 0))
        empty = await carousel_repository.create_project(_project(owner, 1))
        with_hook = await carousel_repository.create_project(_project(owner, 2))
        await carousel_repository.create_slide(
            CarouselSlide(
                project_id=empty.id,
                slide_number=2,
                slide_type="content",
                heading="Não é gancho",
                body="corpo",
            )
        )
        await _with_hook(carousel_repository, with_hook, "Gancho real")

        recent = await load_recent_hooks(SqlRecentHookReader(db_session), str(current.id))

        assert recent.headings == ("Gancho real",)
        assert recent.total == 1

    # Scenario: Recent openings degrade to none without a database
    @pytest.mark.asyncio
    async def test_no_reader_or_unknown_project(self, db_session: AsyncSession) -> None:
        empty = await load_recent_hooks(None, "whatever")
        assert empty.headings == () and empty.total == 0
        reader = SqlRecentHookReader(db_session)
        missing = await load_recent_hooks(reader, "")
        assert missing.headings == () and missing.total == 0
        orphan = await reader.recent_hooks(RecentHookQuery(project_id=str(uuid4())))
        assert orphan.headings == () and orphan.total == 0
