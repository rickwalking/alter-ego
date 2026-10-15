""" "Ponto de Vista" prompts, outline by mode and POV rubric (AE-0375).

Gherkin: tests/features/carousel_pov_prompts.feature
"""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from rag_backend.agents.content_draft_agent import (
    ContentDraftAgent,
    _render_content_prompt,
)
from rag_backend.agents.pov_outline_mixin import (
    parse_hook_candidates,
    parse_pov_outline,
)
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.carousel.content_mode_brief import (
    ContentModeBrief,
    brief_for_project,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.outline_by_mode import (
    ModeOutlineRequest,
    attach_hook_and_checks,
    generate_outline_for_mode,
)
from rag_backend.application.services.carousel.pov_checks import (
    first_person_slide_count,
    hook_too_long,
    thesis_appears_early,
    thesis_keywords,
)
from rag_backend.application.services.carousel.presentation_deck_rules import (
    deck_violations,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.slide_policy_context import (
    slide_policy_context,
)
from rag_backend.application.services.carousel_template.prompts import (
    build_caption_prompt,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.pov_prompts import (
    PovHookRequest,
    PovOutlineRequest,
    RadarHookRequest,
    SlidePolicyContext,
)

_THESIS = "A IA escreve código. Quem decide o que construir ainda é você."
_NEVER_INVENT = "nunca invente"


def _project(**changes: object) -> CarouselProject:
    project = CarouselProject(topic="Julgamento técnico", audience="Devs", niche="IA")
    project.content_mode = "pov"
    project.presentation_policy_version = "pov_hook_v1"
    project.pov_thesis = _THESIS
    project.pov_format = "opiniao"
    project.slide_count = 9
    project.cta_goal = "send"
    project.creator_handle = "pedromarins.ai"
    for key, value in changes.items():
        setattr(project, key, value)
    return project


def _brief(**changes: object) -> ContentModeBrief:
    return brief_for_project(_project(**changes))


def _workflow_input() -> EditorialWorkflowStartInput:
    return EditorialWorkflowStartInput(
        topic="Julgamento técnico",
        audience="Devs",
        brief="Por que decidir importa",
        sources=[{"content": "fonte"}],
    )


class _FakeAgent:
    """Records calls; returns a 9-slide outline with wrong/missing roles."""

    def __init__(self, hooks: list[str] | Exception | None = None) -> None:
        self.calls: list[tuple[str, object]] = []
        self._hooks = hooks if hooks is not None else ["Gancho um", "Gancho dois"]

    async def generate_outline(
        self,
        topic: str,
        audience: str,
        brief: str,
        sources: list[str],
        *,
        sizing: SlidePolicyContext | None = None,
    ) -> list[dict[str, object]]:
        self.calls.append(("outline", sizing))
        count = sizing.slide_count if sizing else 7
        return [
            {"title": f"Slide {i}", "key_points": ["p"]} for i in range(1, count + 1)
        ]

    async def generate_pov_outline(
        self, request: PovOutlineRequest
    ) -> list[dict[str, object]]:
        self.calls.append(("pov", request))
        outline: list[dict[str, object]] = [
            {"title": f"Slide {i}", "key_points": ["p"], "role": "news"}
            for i in range(1, len(request.roles) + 1)
        ]
        outline[1]["title"] = "Quem decide o que construir ainda é você"
        return outline

    async def hook_candidates(self, request: PovHookRequest) -> list[str]:
        self.calls.append(("hook", request))
        if isinstance(self._hooks, Exception):
            raise self._hooks
        return self._hooks

    async def radar_hook_candidates(self, request: RadarHookRequest) -> list[str]:
        self.calls.append(("radar_hook", request))
        return ["Todo mundo falou disso"]


@pytest.mark.unit
class TestPromptsNeverInvent:
    # Scenario: Every POV prompt carries the never-invent rule
    @pytest.mark.parametrize("name", ["hook", "outline", "content", "caption"])
    def test_rule_present(self, name: str) -> None:
        text, _ = render_prompt(
            "carousel_pov",
            name,
            variables={
                "thesis": _THESIS,
                "personal_proof": "",
                "roles": ["hook", "cta"],
                "slide_count": 2,
                "slide_headings": [(1, "Gancho")],
                "role": "point",
            },
            version="v1",
        )
        assert _NEVER_INVENT in text.lower()
        assert _THESIS in text

    # Scenario: No proof means no anecdotes
    def test_no_proof_means_reasoning(self) -> None:
        text, _ = render_prompt(
            "carousel_pov",
            "content",
            variables={"thesis": _THESIS, "personal_proof": "", "role": "pov"},
            version="v1",
        )
        assert "argumente pelo raciocínio" in text
        assert "sem inventar um caso" in text

    # Scenario: The outline prompt lists the contract roles in order
    def test_outline_lists_roles(self) -> None:
        roles = [s.role for s in _brief().policy.slides]
        text, _ = render_prompt(
            "carousel_pov",
            "outline",
            variables={"thesis": _THESIS, "roles": roles, "slide_count": 9},
            version="v1",
        )
        assert "EXATAMENTE\n  9 slides" in text or "EXATAMENTE 9" in text
        listed = [
            line.strip()
            for line in text.splitlines()
            if line.strip()[:2] in {f"{i}." for i in range(1, 10)}
        ]
        assert [line.split(". ", 1)[1] for line in listed] == roles

    @pytest.mark.parametrize(
        ("pov_format", "marker"),
        [
            ("opiniao", "contraponto"),
            ("como_eu_faco", "passos"),
            ("erros_e_mitos", "correção"),
            ("comparacao", "nunca invente benchmarks"),
        ],
    )
    def test_format_narrative(self, pov_format: str, marker: str) -> None:
        text, _ = render_prompt(
            "carousel_pov",
            "outline",
            variables={"thesis": _THESIS, "roles": [], "pov_format": pov_format},
            version="v1",
        )
        assert marker in text


@pytest.mark.unit
class TestParsers:
    def test_hook_candidates_dedupe_and_cap(self) -> None:
        raw = (
            '{"candidates": [{"formula": "a", "text": " Um "}, {"text": "Um"},'
            ' "Dois", {"text": ""}, {"text": "Tres"}, {"text": "Quatro"},'
            ' {"text": "Cinco"}, {"text": "Seis"}]}'
        )
        assert parse_hook_candidates(raw) == ["Um", "Dois", "Tres", "Quatro", "Cinco"]

    @pytest.mark.parametrize("raw", ['{"candidates": []}', "[]", "nope", '{"x": 1}'])
    def test_hook_candidates_invalid(self, raw: str) -> None:
        with pytest.raises((ValueError, TypeError)):
            parse_hook_candidates(raw)

    def test_outline_parse(self) -> None:
        assert parse_pov_outline('[{"title": "a"}, 3]') == [{"title": "a"}]
        with pytest.raises((ValueError, TypeError)):
            parse_pov_outline("{}")


@pytest.mark.unit
class TestOutlineByMode:
    # Scenario: Hook candidates on the outline
    @pytest.mark.asyncio
    async def test_pov_outline(self) -> None:
        agent = _FakeAgent()
        outline = await generate_outline_for_mode(
            agent, ModeOutlineRequest(workflow_input=_workflow_input(), brief=_brief())
        )
        brief = _brief()
        assert [s["role"] for s in outline] == [s.role for s in brief.policy.slides]
        assert len(outline) == 9
        assert outline[0]["hook_candidates"] == ["Gancho um", "Gancho dois"]
        assert outline[0]["title"] == "Gancho um"
        assert outline[0]["outline_checks"] == {"thesis_early": True}
        kinds = [kind for kind, _ in agent.calls]
        assert kinds == ["pov", "hook"]
        request = agent.calls[0][1]
        assert isinstance(request, PovOutlineRequest)
        assert request.pov.thesis == _THESIS
        assert request.sources == ["fonte"]

    # Scenario: A failed hook call keeps the outline
    @pytest.mark.asyncio
    async def test_failed_hooks_keep_outline(self) -> None:
        agent = _FakeAgent(hooks=ValueError("invalid_json"))
        outline = await generate_outline_for_mode(
            agent, ModeOutlineRequest(workflow_input=_workflow_input(), brief=_brief())
        )
        assert outline[0]["hook_candidates"] == []
        assert outline[0]["title"] == "Slide 1"

    # Scenario: The owner's saved hook wins
    @pytest.mark.asyncio
    async def test_saved_hook_wins(self) -> None:
        outline = await generate_outline_for_mode(
            _FakeAgent(),
            ModeOutlineRequest(
                workflow_input=_workflow_input(),
                brief=_brief(hook_text="Pare de pedir código pra IA"),
            ),
        )
        assert outline[0]["title"] == "Pare de pedir código pra IA"

    # Scenario Outline: Thesis on slides 1-2 outline check
    def test_thesis_not_early(self) -> None:
        outline = [
            {"title": "Algo", "key_points": []},
            {"title": "Outra coisa", "key_points": []},
        ]
        checked = attach_hook_and_checks(outline, _brief(), [])
        assert checked[0]["outline_checks"] == {"thesis_early": False}
        assert attach_hook_and_checks([], _brief(), []) == []

    # Scenario: Radar IA v4 outline is sized and stamped
    @pytest.mark.asyncio
    async def test_v4_outline(self) -> None:
        agent = _FakeAgent()
        brief = _brief(
            content_mode="news_analysis",
            presentation_policy_version="hero_lower_third_v4",
            slide_count=8,
        )
        outline = await generate_outline_for_mode(
            agent, ModeOutlineRequest(workflow_input=_workflow_input(), brief=brief)
        )
        sizing = agent.calls[0][1]
        assert isinstance(sizing, SlidePolicyContext)
        assert sizing.slide_count == 8
        assert sizing.policy_version == "hero_lower_third_v4"
        assert "hero_lower_third_v4" in sizing.policy_context
        assert [s["role"] for s in outline][5] == "twist"
        assert len(outline) == 8
        # AE-0376: Radar IA v4 hooks come from the sources (v7 hook prompt).
        assert agent.calls[1][0] == "radar_hook"
        assert outline[0]["title"] == "Todo mundo falou disso"
        assert outline[0]["hook_candidates"] == ["Todo mundo falou disso"]

    # Scenario: Legacy projects keep the legacy outline
    @pytest.mark.asyncio
    @pytest.mark.parametrize("with_brief", [True, False])
    async def test_legacy_outline(self, with_brief: bool) -> None:
        agent = _FakeAgent()
        brief = (
            _brief(content_mode=None, presentation_policy_version="hero_lower_third_v3")
            if with_brief
            else None
        )
        outline = await generate_outline_for_mode(
            agent, ModeOutlineRequest(workflow_input=_workflow_input(), brief=brief)
        )
        assert agent.calls == [("outline", None)]
        assert all("role" not in slide for slide in outline)


@pytest.mark.unit
class TestSlidePolicyContext:
    # Scenario: POV slides are drafted with the POV prompt
    def test_pov_hook_slide(self) -> None:
        context = slide_policy_context(
            _brief(), {"slide_index": 1, "role": "hook", "title": "Gancho um"}
        )
        assert context is not None and context.pov is not None
        assert context.pov.hook_text == "Gancho um"
        assert context.pov.role == "hook"
        assert context.pov.cta_copy == "Manda pra quem precisa ouvir isso."
        assert context.slide_count == 9

    def test_saved_hook_and_role_from_position(self) -> None:
        context = slide_policy_context(
            _brief(hook_text="Meu gancho"), {"slide_index": 1, "title": "x"}
        )
        assert context is not None and context.pov is not None
        assert context.pov.role == "hook"
        assert context.pov.hook_text == "Meu gancho"

    def test_non_hook_has_no_hook_text(self) -> None:
        context = slide_policy_context(_brief(), {"slide_index": 4, "title": "x"})
        assert context is not None and context.pov is not None
        assert context.pov.role == "point"
        assert context.pov.hook_text == ""

    def test_v4_has_no_pov(self) -> None:
        brief = _brief(
            content_mode="news_analysis",
            presentation_policy_version="hero_lower_third_v4",
        )
        context = slide_policy_context(brief, {"slide_index": 1})
        assert context is not None and context.pov is None
        assert context.slide_count == 7

    def test_legacy_and_missing_brief(self) -> None:
        legacy = _brief(
            content_mode=None, presentation_policy_version="hero_lower_third_v3"
        )
        assert slide_policy_context(legacy, {}) is None
        assert slide_policy_context(None, {}) is None

    def test_content_prompt_routes_to_pov(self) -> None:
        context = slide_policy_context(
            _brief(), {"slide_index": 1, "role": "hook", "title": "Gancho um"}
        )
        assert context is not None
        text, _ = _render_content_prompt({"slide_number": 1}, context)
        assert 'EXATAMENTE: "Gancho um"' in text
        assert _THESIS in text
        legacy, _ = _render_content_prompt({"slide_number": 1}, None)
        assert "hero_lower_third contract" in legacy

    def test_content_prompt_routes_radar_v4_to_v7(self) -> None:
        brief = _brief(
            content_mode="news_analysis", presentation_policy_version="hero_lower_third_v4"
        )
        context = slide_policy_context(brief, {"slide_index": 2, "title": "x"})
        assert context is not None and context.role == "news"
        text, _ = _render_content_prompt({"slide_number": 2}, context)
        assert "ONLY slide about what happened" in text


@pytest.mark.unit
class TestCaption:
    # Scenario: POV caption
    def test_pov_caption(self) -> None:
        prompt = build_caption_prompt(_project(), [(1, "Gancho um"), (2, "Dois")])
        assert "Gancho do slide 1: Gancho um" in prompt
        assert _THESIS in prompt
        assert "Objetivo do CTA: send" in prompt

    def test_radar_caption_uses_the_goal(self) -> None:
        project = _project(content_mode="news_analysis", cta_goal="comment")
        prompt = build_caption_prompt(project, [(1, "X")])
        assert "Objetivo do CTA: comment" in prompt
        assert "Tese do autor" not in prompt


def _deck(headings: list[str], bodies: list[str]) -> list[dict[str, object]]:
    return [
        {"slide_index": i, "presentation_pt": {"heading": h, "body": b}}
        for i, (h, b) in enumerate(zip(headings, bodies, strict=True), 1)
    ]


_FIRST_PERSON = ["Eu vejo isso.", "No meu trabalho.", "Minha regra.", "Neutro."]


@pytest.mark.unit
class TestPovRubric:
    def _pov_deck(self, hook: str, bodies: list[str]) -> list[dict[str, object]]:
        headings = [hook, *[f"Titulo {i}" for i in range(2, 10)]]
        return _deck(headings, [*bodies, *["Texto."] * (9 - len(bodies))])

    # Scenario: Hook word limit fires
    def test_hook_word_limit(self) -> None:
        hook = " ".join(["palavra"] * 11)
        violations = deck_violations(
            self._pov_deck(hook, _FIRST_PERSON), load_presentation_policy("pov_hook_v1")
        )
        fired = {v.code: v for v in violations}
        assert set(fired) == {"hook_word_limit"}
        assert fired["hook_word_limit"].is_blocker
        assert fired["hook_word_limit"].slide_index == 1

    # Scenario: First person warning
    def test_first_person_warning(self) -> None:
        violations = deck_violations(
            self._pov_deck("Gancho curto", _FIRST_PERSON[:2]),
            load_presentation_policy("pov_hook_v1"),
        )
        assert [v.code for v in violations] == ["first_person_missing"]
        assert not violations[0].is_blocker

    def test_clean_pov_deck(self) -> None:
        assert (
            deck_violations(
                self._pov_deck("Gancho curto", _FIRST_PERSON),
                load_presentation_policy("pov_hook_v1"),
            )
            == []
        )

    # Scenario: Radar IA v4 decks do not get the POV rules
    def test_v4_has_no_pov_rules(self) -> None:
        deck = _deck([" ".join(["x"] * 11)] + ["T"] * 6, ["Texto."] * 7)
        assert (
            deck_violations(deck, load_presentation_policy("hero_lower_third_v4")) == []
        )

    def test_wrong_size_skips_role_rules(self) -> None:
        deck = _deck([" ".join(["x"] * 11)] * 11, ["Texto."] * 11)
        codes = [
            v.code
            for v in deck_violations(deck, load_presentation_policy("pov_hook_v1"))
        ]
        assert codes == ["slide_count_invalid"]


@pytest.mark.unit
class TestPovChecks:
    def test_hook_too_long(self) -> None:
        assert not hook_too_long(" ".join(["a"] * 10))
        assert hook_too_long(" ".join(["a"] * 11))

    def test_first_person(self) -> None:
        assert (
            first_person_slide_count(["Eu acho", "<strong>Meu</strong> ponto", "ele"])
            == 2
        )
        assert first_person_slide_count(["Comigo não", "Eutanásia"]) == 1

    def test_thesis_keywords_fold_accents(self) -> None:
        assert "decisao" in thesis_keywords("A decisão é sua")
        assert thesis_keywords("é a do") == frozenset()

    def test_thesis_early(self) -> None:
        assert thesis_appears_early(["Quem DECIDE?"], "Quem decide é você")
        assert not thesis_appears_early(["Outra coisa"], "Quem decide é você")
        assert thesis_appears_early(["x"], "é o")


@pytest.mark.unit
def test_brief_properties() -> None:
    brief = _brief()
    assert brief.is_pov and brief.has_roles
    assert brief.role_at(9) == "cta"
    assert brief.role_at(42) is None
    legacy = replace(brief, content_mode="news_analysis")
    assert not legacy.is_pov


_VOCAB = (
    ("alfa", "bravo", "charlie"),
    ("delta", "echo", "foxtrot"),
    ("golf", "hotel", "india"),
    ("juliet", "kilo", "lima"),
    ("mike", "november", "oscar"),
    ("papa", "quebec", "romeo"),
    ("sierra", "tango", "uniform"),
    ("victor", "whiskey", "xray"),
    ("yankee", "zulu", "ambar"),
    ("bronze", "cobre", "diamante"),
)


class _FakeContentAgent:
    """Captures the policy context each slide is drafted with."""

    def __init__(self) -> None:
        self.policies: list[SlidePolicyContext | None] = []

    async def draft_slide(self, **kwargs: object) -> dict[str, object]:
        policy = kwargs.get("policy")
        assert policy is None or isinstance(policy, SlidePolicyContext)
        self.policies.append(policy)
        index = int(str(kwargs.get("slide_index", 1)))
        return {"draft_text": " ".join(_VOCAB[index % len(_VOCAB)])}


@pytest.mark.unit
class TestDraftingByMode:
    # Scenario: POV slides are drafted with the POV prompt
    @pytest.mark.asyncio
    async def test_pov_drafts_carry_the_pov_context(self) -> None:
        from rag_backend.application.services.carousel.editorial_workflow_generators import (
            SlideDraftGenerationParams,
            generate_slide_drafts,
        )

        brief = _brief()
        outline = [
            {
                "slide_index": s.slide_number,
                "title": f"T{s.slide_number}",
                "role": s.role,
            }
            for s in brief.policy.slides
        ]
        agent = _FakeContentAgent()
        await generate_slide_drafts(
            cast(ContentDraftAgent, agent),
            SlideDraftGenerationParams(outline=outline, mode=brief),
        )
        assert len(agent.policies) == 9
        first = agent.policies[0]
        assert first is not None and first.pov is not None
        assert first.pov.role == "hook"
        assert first.pov.hook_text == "T1"
        assert agent.policies[-1] is not None
        last_pov = agent.policies[-1].pov
        assert last_pov is not None and last_pov.role == "cta"

    @pytest.mark.asyncio
    async def test_legacy_drafts_have_no_policy(self) -> None:
        from rag_backend.application.services.carousel.editorial_workflow_generators import (
            SlideDraftGenerationParams,
            generate_slide_drafts,
        )

        agent = _FakeContentAgent()
        await generate_slide_drafts(
            cast(ContentDraftAgent, agent),
            SlideDraftGenerationParams(
                outline=[{"slide_index": 1, "title": "T"}], mode=None
            ),
        )
        assert agent.policies == [None]
