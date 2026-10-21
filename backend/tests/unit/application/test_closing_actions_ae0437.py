"""Closing actions are drafted, kept, filled and repaired; EN stays EN.

Gherkin: tests/features/closing_actions_scoped_revisions_ae0437.feature
(sections A, B and C). The validator, the policy and the prod 5344b6c6
fixture are real; the field repair model is a fake.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.carousel_repair_projection import (
    localized_from_slides,
)
from rag_backend.application.services.carousel.closing_actions import (
    restore_closing_actions,
)
from rag_backend.application.services.carousel.content_gate_repair import (
    GateRepairCommand,
    run_gate_repair,
)
from rag_backend.application.services.carousel.content_gate_repair_targets import (
    drop_untranslated_copies,
    fill_slide_structure,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    build_localized_slide,
)
from rag_backend.application.services.carousel.owner_autofix_plan import (
    AutofixContext,
    SlideOutline,
    plan_autofix,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.structure_fill import (
    StructureFillContext,
    outline_from_state,
)
from rag_backend.domain.models.carousel import CarouselSlide
from tests.unit.application.content_gate_repair_fixtures_ae0430 import (
    POLICY_V4,
    PROD_ANSWERS,
    FakeRepairer,
    prod_slides,
)

_SKILLS = Path(__file__).parents[3] / "src/rag_backend/agents/skills/carousel-pipeline"
_POLICY = load_presentation_policy(POLICY_V4)
_CLOSING_POINTS = (
    "Teste controlado: comece com uma tarefa fácil de desfazer",
    "Leia cada passo: veja o diff antes de liberar mais acesso",
    "Aumente aos poucos: solte uma tarefa maior quando passar",
)
_SUMMARY_POINTS = (
    "Voz não é o ponto: o salto é o ambiente de execução",
    "Acesso é risco: logins e arquivos ficam no servidor",
    "Teste antes: confiança vem do histórico",
)


def _item(title: str, body: str) -> dict[str, object]:
    return {"icon_name": "wrench", "title": title, "body": body}


def _items(count: int, prefix: str) -> list[dict[str, object]]:
    return [_item(f"{prefix} {n}", f"Corpo do item {n}.") for n in range(count)]


def _payload(
    slides: list[dict[str, object]], index: int, locale: str
) -> dict[str, object]:
    slide = next(s for s in slides if s.get("slide_index") == index)
    return cast(dict[str, object], slide[f"presentation_{locale}"])


def _closing_record(pt: dict[str, object], en: dict[str, object]) -> dict[str, object]:
    base = {"slide_type": "closing", "heading": "O que fazer agora", "body": ""}
    return {
        "slide_index": 6,
        "slide_type": "closing",
        "presentation_pt": {**base, **pt},
        "presentation_en": {**base, "heading": "What to do now", **en},
    }


def _context(points: tuple[str, ...]) -> AutofixContext:
    return AutofixContext(
        policy=_POLICY,
        outline={6: SlideOutline(key_points=points, slide_type="closing")},
    )


@pytest.mark.unit
class TestClosingKey:
    def test_drafting_instructions_ask_for_actions(self) -> None:
        """Scenario: The drafting instructions ask for closing actions."""
        skill = (_SKILLS / "phases/content/SKILL.md").read_text(encoding="utf-8")
        contracts = (_SKILLS / "_shared/content-contracts.md").read_text(
            encoding="utf-8"
        )
        closing_row = next(line for line in skill.splitlines() if "`closing`" in line)
        assert "`actions` array" in closing_row
        assert "features" not in closing_row
        assert "`closing` slides as structured items (`actions:" in contracts
        assert "`features: [{icon_name, title, body}]` on the closing slide" not in (
            contracts
        )

    def test_closing_features_draft_becomes_actions(self) -> None:
        """Scenario: A closing checklist drafted as features is stored as actions."""
        draft = {
            "slide_index": 6,
            "slide_type": "closing",
            "heading": "O que fazer agora",
            "draft_text": "Três passos para começar.",
            "features": _items(3, "Passo"),
        }
        record = build_localized_slide(draft, slide_index=6)
        pt = cast(dict[str, object], record["presentation_pt"])
        assert pt["actions"] == _items(3, "Passo")
        assert "features" not in pt

        both = _closing_record(
            {"features": _items(3, "Passo")}, {"features": _items(3, "Step")}
        )
        record = build_localized_slide(both, slide_index=6)
        en = cast(dict[str, object], record["presentation_en"])
        assert en["actions"] == _items(3, "Step")
        assert "features" not in en

    def test_closing_row_reads_back_as_actions(self) -> None:
        """Scenario: A closing slide row read back from its row keeps its actions."""
        project = uuid4()
        closing = CarouselSlide(
            project_id=project,
            slide_number=6,
            slide_type="closing",
            heading="O que fazer agora",
            body="",
            extras={
                "features": _items(3, "Passo"),
                "translation_en": {"heading": "Now", "features": _items(3, "Step")},
            },
        )
        content = CarouselSlide(
            project_id=project,
            slide_number=3,
            slide_type="content",
            heading="Tese",
            body="Corpo.",
            extras={"features": _items(3, "Ponto")},
        )
        records = localized_from_slides([content, closing])
        assert _payload(records, 6, "pt")["actions"] == _items(3, "Passo")
        assert _payload(records, 6, "en")["actions"] == _items(3, "Step")
        assert "features" not in _payload(records, 6, "pt")
        assert _payload(records, 3, "pt")["features"] == _items(3, "Ponto")

    def test_real_actions_win(self) -> None:
        """Scenario: Real actions win over features."""
        payload: dict[str, object] = {
            "slide_type": "closing",
            "actions": _items(3, "Ação"),
            "features": _items(3, "Destaque"),
        }
        before = copy.deepcopy(payload)
        assert restore_closing_actions(payload) == before
        content: dict[str, object] = {"features": _items(3, "x")}
        assert restore_closing_actions(content, "content") == {
            "features": _items(3, "x")
        }
        no_list: dict[str, object] = {"slide_type": "closing", "features": "x"}
        assert restore_closing_actions(no_list) == {
            "slide_type": "closing",
            "features": "x",
        }


@pytest.mark.unit
class TestAutofixFillsActions:
    def test_missing_actions_come_from_the_outline(self) -> None:
        """Scenario: The owner autofix fills missing closing actions from the outline."""
        record = _closing_record({"actions": []}, {"actions": []})
        plan = plan_autofix([record], _context(_CLOSING_POINTS))
        pt = cast(dict[str, object], plan.records[0]["presentation_pt"])
        en = cast(dict[str, object], plan.records[0]["presentation_en"])
        actions = cast(list[dict[str, object]], pt["actions"])
        assert [a["title"] for a in actions] == [
            "Teste controlado",
            "Leia cada passo",
            "Aumente aos poucos",
        ]
        assert all(len(str(a["title"])) <= 30 for a in actions)
        assert all(len(str(a["body"])) <= 90 for a in actions)
        assert all(a["icon_name"] in _POLICY.lucide_icon_allowlist for a in actions)
        assert en["actions"] == actions
        paths = {target.path for target in plan.retranslate}
        assert "actions[0].title" in paths and "actions[2].body" in paths

    def test_swapped_features_move_back_to_actions(self) -> None:
        """Scenario: The owner autofix moves swapped closing features back to actions."""
        record = _closing_record(
            {"features": _items(3, "Passo")}, {"features": _items(3, "Step")}
        )
        plan = plan_autofix([record], _context(()))
        pt = cast(dict[str, object], plan.records[0]["presentation_pt"])
        en = cast(dict[str, object], plan.records[0]["presentation_en"])
        assert [a["title"] for a in cast(list[dict[str, object]], pt["actions"])] == [
            "Passo 0",
            "Passo 1",
            "Passo 2",
        ]
        assert [a["title"] for a in cast(list[dict[str, object]], en["actions"])] == [
            "Step 0",
            "Step 1",
            "Step 2",
        ]
        assert "features" not in pt and "features" not in en

    def test_too_few_key_points_invent_nothing(self) -> None:
        """Scenario: Too few key points leave the closing slide for a revision."""
        record = _closing_record({"actions": []}, {"actions": []})
        plan = plan_autofix([record], _context(_CLOSING_POINTS[:1]))
        pt = cast(dict[str, object], plan.records[0]["presentation_pt"])
        assert pt["actions"] == []

    def test_outline_from_state(self) -> None:
        state = {
            "outline": [
                {
                    "title": " Gancho ",
                    "key_points": ["a", " ", 3],
                    "slide_type": "intro",
                },
                {"slide_index": 6, "key_points": "x"},
                "junk",
            ]
        }
        outline = outline_from_state(state)
        assert outline[1] == SlideOutline(
            title="Gancho", key_points=("a",), slide_type="intro"
        )
        assert outline[6] == SlideOutline()
        assert outline_from_state(None) == {}
        assert outline_from_state({"outline": "x"}) == {}


def _without_items() -> list[dict[str, object]]:
    slides = prod_slides()
    for index, key in ((2, "summary_points"), (6, "actions")):
        for locale in ("pt", "en"):
            _payload(slides, index, locale)[key] = []
    return slides


def _outline() -> dict[int, SlideOutline]:
    return {
        2: SlideOutline(key_points=_SUMMARY_POINTS, slide_type="summary"),
        6: SlideOutline(key_points=_CLOSING_POINTS, slide_type="closing"),
    }


def _en_item_answers() -> dict[str, str]:
    answers = dict(PROD_ANSWERS)
    for index, key in ((2, "summary_points"), (6, "actions")):
        for n in range(3):
            answers[f"{index}:en:{key}[{n}].title"] = f"Point {n}"
            answers[f"{index}:en:{key}[{n}].body"] = f"The English body {n}."
    return answers


@pytest.mark.unit
@pytest.mark.asyncio
class TestGateRepairFillsStructure:
    async def test_summary_points_and_actions_come_from_the_outline(self) -> None:
        """Scenario: The content gate repair fills closing actions and summary points."""
        repairer = FakeRepairer(_en_item_answers())
        outcome = await run_gate_repair(
            GateRepairCommand(
                slides=_without_items(),
                repairer=repairer,
                policy_version=POLICY_V4,
                outline=_outline(),
            )
        )
        pt_actions = cast(
            list[dict[str, object]], _payload(outcome.slides, 6, "pt")["actions"]
        )
        assert pt_actions[0]["title"] == "Teste controlado"
        assert (
            len(cast(list[object], _payload(outcome.slides, 2, "pt")["summary_points"]))
            == 3
        )
        assert "6:en:actions[0].title" in repairer.calls[0]
        assert "2:en:summary_points[2].body" in repairer.calls[0]
        en_actions = cast(
            list[dict[str, object]], _payload(outcome.slides, 6, "en")["actions"]
        )
        assert en_actions[0]["title"] == "Point 0"
        codes = {v.code for v in outcome.report.violations if v.is_blocker}
        assert "closing_actions_missing" not in codes
        assert "summary_points_missing" not in codes
        assert {2, 6} <= outcome.changed_indices

    async def test_without_outline_nothing_is_invented(self) -> None:
        outcome = await run_gate_repair(
            GateRepairCommand(
                slides=_without_items(),
                repairer=FakeRepairer({}),
                policy_version=POLICY_V4,
            )
        )
        assert _payload(outcome.slides, 6, "pt")["actions"] == []
        codes = {v.code for v in outcome.report.violations}
        assert "closing_actions_missing" in codes


@pytest.mark.unit
@pytest.mark.asyncio
class TestEnglishStaysEnglish:
    async def test_portuguese_answer_for_en_is_dropped(self) -> None:
        """Scenario: A Portuguese answer for an EN field is dropped."""
        answers = {
            **PROD_ANSWERS,
            "1:en:tldr_strip": "Eu olho para o computador, não para a demo",
        }
        outcome = await run_gate_repair(
            GateRepairCommand(
                slides=prod_slides(),
                repairer=FakeRepairer(answers),
                policy_version=POLICY_V4,
            )
        )
        en = _payload(outcome.slides, 1, "en")
        assert en.get("tldr_strip") != answers["1:en:tldr_strip"]
        assert en.get("tldr_strip") != _payload(outcome.slides, 1, "pt")["tldr_strip"]
        assert en["heading"] == PROD_ANSWERS["1:en:heading"]

    async def test_untranslated_copy_is_taken_out_of_en(self) -> None:
        """Scenario: A PT copy nobody translated is taken out of EN again."""
        outcome = await run_gate_repair(
            GateRepairCommand(
                slides=prod_slides(),
                repairer=FakeRepairer(fail=True),
                policy_version=POLICY_V4,
            )
        )
        assert "tldr_strip" not in _payload(outcome.slides, 1, "en")
        assert outcome.changed_indices == frozenset()

    async def test_translated_copy_stays(self) -> None:
        outcome = await run_gate_repair(
            GateRepairCommand(
                slides=prod_slides(),
                repairer=FakeRepairer(),
                policy_version=POLICY_V4,
            )
        )
        assert (
            _payload(outcome.slides, 1, "en")["tldr_strip"]
            == (PROD_ANSWERS["1:en:tldr_strip"])
        )


@pytest.mark.unit
class TestRepairTargetHelpers:
    def test_fill_slide_structure_needs_a_pt_payload_and_an_index(self) -> None:
        context = StructureFillContext()
        no_pt = {"slide_index": 6, "presentation_en": {}}
        assert fill_slide_structure(no_pt, context) == no_pt
        no_index = {"presentation_pt": {"slide_type": "closing"}}
        assert fill_slide_structure(no_index, context) == no_index
        pt_only = _closing_record({"features": _items(3, "Passo")}, {})
        del pt_only["presentation_en"]
        filled = fill_slide_structure(pt_only, context)
        assert "presentation_en" not in filled
        assert cast(dict[str, object], filled["presentation_pt"])["actions"]

    def test_drop_untranslated_copies(self) -> None:
        """When EN had a shorter list, the untranslated PT copy goes back to it; when EN
        already held the same items before the repair, there is nothing to undo.
        """
        pt_items = _items(3, "Passo")
        no_en = {"presentation_pt": {"actions": pt_items}}
        assert drop_untranslated_copies(no_en, None) == no_en
        copied = _closing_record({"actions": pt_items}, {"actions": pt_items})
        original = _closing_record({"actions": pt_items}, {"actions": pt_items[:1]})
        restored = drop_untranslated_copies(copied, original)
        assert _payload([restored], 6, "en")["actions"] == pt_items[:1]
        kept = drop_untranslated_copies(copied, copied)
        assert _payload([kept], 6, "en")["actions"] == pt_items
