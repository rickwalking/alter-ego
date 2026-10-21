"""The owner autofix plan, issue lines, checkpoint patch, translator.

Gherkin: tests/features/autopilot_owner_autofix.feature
"""

from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import dataclass, field
from typing import cast

import pytest
from langchain_core.language_models import BaseChatModel

from rag_backend.application.services.carousel import owner_autofix_translate
from rag_backend.application.services.carousel.owner_autofix_checkpoint import (
    checkpoint_patch,
)
from rag_backend.application.services.carousel.owner_autofix_issues import (
    Issue,
    NounFinding,
    issue_lines,
    noun_findings,
    noun_issues,
    translation_issues,
    violation_issues,
)
from rag_backend.application.services.carousel.owner_autofix_plan import (
    AutofixContext,
    RetranslateTarget,
    SlideOutline,
    apply_translations,
    plan_autofix,
)
from rag_backend.application.services.carousel.owner_autofix_translate import (
    LlmEnRetranslator,
    LlmRetranslatorConfig,
    retranslate_bounded,
)
from rag_backend.application.services.carousel.presentation_casing_markers import (
    CASING_REPAIRS_KEY,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3,
)

_V3 = PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3
_POLICY = load_presentation_policy(_V3)
_KEY_POINTS = (
    "Simulação Real2Sim: treina antes do mundo real",
    "Braços robóticos: seguem instruções em linguagem natural",
    "Segurança: para sozinho quando algo sai do esperado",
)


def _record(
    index: int, slide_type: str, pt: dict[str, object], en: dict[str, object]
) -> dict[str, object]:
    return {
        "slide_index": index,
        "slide_type": slide_type,
        "presentation_pt": {"slide_type": slide_type, **pt},
        "presentation_en": {"slide_type": slide_type, **en},
    }


def _context(**outline: SlideOutline) -> AutofixContext:
    entries = {int(key.removeprefix("s")): value for key, value in outline.items()}
    return AutofixContext(
        policy=_POLICY, vocabulary=("Argon", "Brasil"), outline=entries
    )


@pytest.mark.unit
class TestPlanRepairs:
    """Scenario: Happy path — every deterministic repair in one plan."""

    def test_sentence_case_nouns_and_tags_in_both_locales(self) -> None:
        record = _record(
            5,
            "content",
            {
                "heading": "a versão leva o argon ao mundo físico",
                "body": "à frente, o time testa. depois strongpublica/strong.",
            },
            {"heading": "the robotics version", "body": "argon now drives arms."},
        )
        plan = plan_autofix([record], _context())
        pt = plan.records[0]["presentation_pt"]
        en = plan.records[0]["presentation_en"]
        assert isinstance(pt, dict) and isinstance(en, dict)
        assert pt["heading"] == "A versão leva o Argon ao mundo físico"
        assert pt["body"] == "À frente, o time testa. Depois <strong>publica</strong>."
        assert en["heading"] == "The robotics version"
        assert en["body"] == "Argon now drives arms."
        assert plan.changed and plan.fixable
        assert plan.retranslate == ()

    def test_title_only_content_slide_gets_features_and_en_targets(self) -> None:
        record = _record(
            4,
            "content",
            {"heading": "Robôs reais", "body": ""},
            {"heading": "Real robots", "body": ""},
        )
        plan = plan_autofix([record], _context(s4=SlideOutline(key_points=_KEY_POINTS)))
        pt = plan.records[0]["presentation_pt"]
        assert isinstance(pt, dict)
        features = pt["features"]
        assert isinstance(features, list) and len(features) == 3
        assert features[0] == {
            "icon_name": _POLICY.lucide_icon_allowlist[0],
            "title": "Simulação Real2Sim",
            "body": "Treina antes do mundo real",
        }
        paths = {target.path for target in plan.retranslate}
        assert paths == {
            f"features[{n}].{key}" for n in range(3) for key in ("title", "body")
        }
        assert all(target.slide_index == 4 for target in plan.retranslate)
        report = validate_localized_slides(plan.records, policy_version=_V3)
        assert not any(
            v.code == "body_empty" and v.locale == "pt" for v in report.violations
        )

    def test_too_few_key_points_leave_the_slide_for_a_rework(self) -> None:
        record = _record(
            4,
            "content",
            {"heading": "Robôs reais", "body": ""},
            {"heading": "Real robots", "body": ""},
        )
        plan = plan_autofix(
            [record], _context(s4=SlideOutline(key_points=_KEY_POINTS[:2]))
        )
        assert not plan.changed
        assert "features" not in cast(
            dict[str, object], plan.records[0]["presentation_pt"]
        )

    def test_summary_points_come_from_the_content_outline(self) -> None:
        record = _record(
            2,
            "summary",
            {"heading": "O que você vai ver", "body": "", "summary_points": []},
            {"heading": "What you will see", "body": "", "summary_points": []},
        )
        outline = {
            f"s{index}": SlideOutline(
                title=f"Ponto {index}",
                key_points=(f"detalhe do ponto {index}",),
                slide_type="content",
            )
            for index in (3, 4, 5)
        }
        plan = plan_autofix(
            [record], _context(s2=SlideOutline(slide_type="summary"), **outline)
        )
        pt = plan.records[0]["presentation_pt"]
        assert isinstance(pt, dict)
        points = pt["summary_points"]
        assert isinstance(points, list)
        assert [point["title"] for point in points] == ["Ponto 3", "Ponto 4", "Ponto 5"]
        assert points[0]["body"] == "Detalhe do ponto 3"

    def test_summary_prefers_its_own_key_points(self) -> None:
        record = _record(
            2,
            "summary",
            {"heading": "Resumo", "body": ""},
            {"heading": "Summary", "body": ""},
        )
        plan = plan_autofix(
            [record],
            _context(s2=SlideOutline(key_points=_KEY_POINTS, slide_type="summary")),
        )
        pt = cast(dict[str, object], plan.records[0]["presentation_pt"])
        points = cast(list[dict[str, str]], pt["summary_points"])
        assert points[2]["title"] == "Segurança"

    def test_untranslated_en_becomes_a_target(self) -> None:
        record = _record(
            6,
            "closing",
            {
                "heading": "O que muda para devs no Brasil",
                "body": "Teste hoje mesmo o modelo.",
            },
            {
                "heading": "O que muda para devs no Brasil",
                "body": "Teste hoje mesmo o modelo.",
            },
        )
        plan = plan_autofix([record], _context())
        assert {target.path for target in plan.retranslate} == {"heading", "body"}
        assert plan.retranslate[0].source == "O que muda para devs no Brasil"
        assert plan.retranslate[0].target_id == "6:heading"
        assert plan.fixable and not plan.changed

    def test_portuguese_en_without_a_pt_counterpart_is_a_target(self) -> None:
        record = _record(
            3,
            "content",
            {"heading": "Título", "body": "Corpo."},
            {
                "heading": "Title",
                "body": "Body.",
                "tldr_strip": "Para quem usa o modelo com você todos os dias",
            },
        )
        plan = plan_autofix([record], _context())
        assert [target.path for target in plan.retranslate] == ["tldr_strip"]

    def test_a_clean_or_unparsable_record_is_not_fixable(self) -> None:
        clean = _record(
            3,
            "content",
            {"heading": "O Argon lidera", "body": "Ele vence."},
            {"heading": "Argon leads", "body": "It wins."},
        )
        plan = plan_autofix(
            [
                clean,
                {"slide_index": 9},
                {"slide_index": 8, "presentation_pt": {"heading": "Só PT"}},
            ],
            _context(),
        )
        assert not plan.fixable

    def test_apply_translations_writes_known_ids_and_polishes(self) -> None:
        record = _record(
            6,
            "closing",
            {"heading": "Igual", "body": "Texto igual em português."},
            {"heading": "Igual", "body": "Texto igual em português."},
        )
        texts = {"6:body": "same text in english about argon.", "9:body": "ignored"}
        updated = apply_translations([record], texts, _context())
        en = cast(dict[str, object], updated[0]["presentation_en"])
        assert en["body"] == "Same text in english about Argon."
        assert en["heading"] == "Igual"
        assert apply_translations([record], {}, _context()) == [record]
        assert apply_translations([{"slide_index": 6}], texts, _context()) == [
            {"slide_index": 6}
        ]


@pytest.mark.unit
class TestIssueLines:
    """Scenario: The review message lists the issues (at most 5 lines)."""

    def test_formats_validator_translation_and_noun_issues(self) -> None:
        records = [
            _record(
                4,
                "content",
                {"heading": "Robôs", "body": ""},
                {"heading": "Robots", "body": ""},
            ),
            _record(
                5,
                "content",
                {"heading": "a versão", "body": "Ok."},
                {"heading": "The version", "body": "Ok."},
            ),
        ]
        report = validate_localized_slides(records, policy_version=_V3)
        target = RetranslateTarget(slide_index=6, path="heading", source="x")
        lines = issue_lines([
            *violation_issues(report),
            *translation_issues([target]),
            *noun_issues([NounFinding(slide=5, noun="argon")]),
        ])
        assert "Slide 4: no body or features" in lines
        assert "Slide 5: heading starts lowercase" in lines
        assert len(lines) <= 5

    def test_caps_at_five_lines_with_a_more_line(self) -> None:
        issues = [
            Issue(slide=index, english=False, text="body starts lowercase")
            for index in range(1, 8)
        ]
        lines = issue_lines(issues)
        assert len(lines) == 5
        assert lines[-1] == "+3 more issues"
        assert lines[0] == "Slide 1: body starts lowercase"

    def test_en_items_and_carousel_level_lines(self) -> None:
        issues = [
            Issue(slide=6, english=True, text="not translated"),
            Issue(slide=6, english=True, text="not translated"),
            Issue(slide=0, english=False, text="slide count invalid"),
        ]
        assert issue_lines(issues) == (
            "Carousel: slide count invalid",
            "Slide 6 EN: not translated",
        )

    def test_item_casing_and_unknown_codes_read_as_text(self) -> None:
        records = [
            _record(
                6,
                "closing",
                {
                    "heading": "Fim",
                    "body": "Ok.",
                    "actions": [
                        {"icon_name": "wrench", "title": "teste", "body": "Agora."}
                    ]
                    * 3,
                },
                {"heading": "End", "body": "Ok."},
            )
        ]
        lines = issue_lines(
            violation_issues(validate_localized_slides(records, policy_version=_V3))
        )
        assert "Slide 6: action text starts lowercase" in lines
        assert "Slide 6: translation shape mismatch" in lines

    def test_noun_findings_scan_both_locales(self) -> None:
        records = [
            _record(
                5,
                "content",
                {"heading": "O argon", "body": ""},
                {"heading": "The argon", "body": ""},
            )
        ]
        findings = noun_findings(records, ("Argon",))
        assert findings == [
            NounFinding(slide=5, noun="argon", english=False),
            NounFinding(slide=5, noun="argon", english=True),
        ]
        assert issue_lines(noun_issues(findings)) == (
            "Slide 5: proper noun lowercase (argon)",
            "Slide 5 EN: proper noun lowercase (argon)",
        )


@pytest.mark.unit
class TestCheckpointPatch:
    """Scenario: the workflow presentation copy carries the fix."""

    def test_replaces_payloads_drops_markers_and_keeps_actions(self) -> None:
        state_slide = {
            "slide_index": 6,
            "slide_type": "closing",
            "presentation_pt": {"heading": "o que muda", "actions": []},
            "presentation_en": {"heading": "what changes", "actions": []},
            CASING_REPAIRS_KEY: [
                {
                    "locale": "pt",
                    "field": "heading",
                    "code": "heading_not_sentence_case_pt",
                }
            ],
        }
        other = {"slide_index": 7, "presentation_pt": {"heading": "Salve"}}
        record = _record(
            6,
            "closing",
            {"heading": "O que muda", "features": [{"title": "A", "body": "B"}]},
            {"heading": "What changes"},
        )
        patch = checkpoint_patch(
            {"localized_slides": [state_slide, other, "junk"]}, [record], _V3
        )
        assert patch is not None
        slides = cast(list[dict[str, object]], patch["localized_slides"])
        pt = cast(dict[str, object], slides[0]["presentation_pt"])
        assert pt["heading"] == "O que muda"
        assert pt["actions"] == [{"title": "A", "body": "B"}]
        assert "features" not in pt
        assert CASING_REPAIRS_KEY not in slides[0]
        assert slides[1] == other
        assert "violations" in cast(dict[str, object], patch["presentation_validation"])

    def test_no_presentation_copy_means_no_patch(self) -> None:
        assert checkpoint_patch({}, [], _V3) is None
        assert checkpoint_patch({"localized_slides": "x"}, [], _V3) is None


@dataclass
class _Translator:
    answers: list[object] = field(default_factory=list)
    calls: int = 0

    async def translate(self, targets: tuple[RetranslateTarget, ...]) -> dict[str, str]:
        self.calls += 1
        answer = self.answers.pop(0) if self.answers else {}
        if isinstance(answer, Exception):
            raise answer
        return cast(dict[str, str], answer)


_TARGETS = (RetranslateTarget(slide_index=6, path="heading", source="O que muda"),)


@pytest.mark.unit
@pytest.mark.asyncio
class TestBoundedRetranslate:
    """Scenario: EN re-translation fails — at most 2 calls, EN kept."""

    async def test_every_attempt_failing_reports_failure(self) -> None:
        translator = _Translator(answers=[RuntimeError("boom"), ValueError("bad json")])
        result = await retranslate_bounded(translator, _TARGETS)
        assert result.failed and result.texts == {} and result.attempts == 2
        assert translator.calls == 2

    async def test_retry_succeeds_and_filters_answers(self) -> None:
        translator = _Translator(
            answers=[
                RuntimeError("boom"),
                {"6:heading": "What changes", "9:x": "Other", "6:body": ""},
            ]
        )
        result = await retranslate_bounded(translator, _TARGETS)
        assert not result.failed and result.attempts == 2
        assert result.texts == {"6:heading": "What changes"}

    async def test_portuguese_answers_are_dropped(self) -> None:
        translator = _Translator(
            answers=[{"6:heading": "O que muda para devs no Brasil"}]
        )
        result = await retranslate_bounded(translator, _TARGETS)
        assert result.texts == {} and not result.failed

    async def test_no_targets_means_no_call(self) -> None:
        translator = _Translator()
        result = await retranslate_bounded(translator, ())
        assert translator.calls == 0 and result.attempts == 0

    async def test_a_hanging_model_times_out(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            owner_autofix_translate, "AUTOFIX_TRANSLATE_TIMEOUT_SECONDS", 0.01
        )

        class _Slow:
            async def translate(
                self, targets: tuple[RetranslateTarget, ...]
            ) -> dict[str, str]:
                await asyncio.sleep(1)
                return {}

        result = await retranslate_bounded(_Slow(), _TARGETS)
        assert result.failed


@dataclass
class _Reply:
    content: str


@dataclass
class _ChatModel:
    reply: str
    prompts: list[str] = field(default_factory=list)

    async def ainvoke(self, messages: list[object], config: object = None) -> _Reply:
        self.prompts.append(str(getattr(messages[0], "content", "")))
        return _Reply(content=self.reply)


@pytest.mark.unit
@pytest.mark.asyncio
class TestLlmRetranslator:
    """The versioned prompt carries the ids and PT texts; the answer is parsed."""

    async def test_renders_the_prompt_and_parses_translations(self) -> None:
        answer = {
            "translations": [
                {"id": "6:heading", "text": " What changes "},
                {"id": 3},
                "x",
            ]
        }
        model = _ChatModel(reply=json.dumps(answer))
        translator = LlmEnRetranslator(
            LlmRetranslatorConfig(llm=cast(BaseChatModel, model))
        )
        assert await translator.translate(_TARGETS) == {"6:heading": "What changes"}
        assert '"id": "6:heading"' in model.prompts[0]
        assert "O que muda" in model.prompts[0]
        assert "<strong>" in model.prompts[0]

    @pytest.mark.parametrize("reply", ['["not", "a", "map"]', '{"translations": "x"}'])
    async def test_malformed_answers_raise(self, reply: str) -> None:
        translator = LlmEnRetranslator(
            LlmRetranslatorConfig(llm=cast(BaseChatModel, _ChatModel(reply=reply)))
        )
        with pytest.raises(TypeError):
            await translator.translate(_TARGETS)


def test_targets_are_value_objects() -> None:
    target = copy.copy(_TARGETS[0])
    assert target == _TARGETS[0]


@pytest.mark.unit
def test_body_casing_reads_as_body_and_pt_only_records_patch() -> None:
    issue = violation_issues(
        validate_localized_slides(
            [
                _record(
                    3,
                    "content",
                    {"heading": "Ok", "body": "ok. depois."},
                    {"heading": "Ok", "body": "Ok."},
                )
            ],
            policy_version=_V3,
        )
    )
    assert "Slide 3: body starts lowercase" in issue_lines(issue)
    patch = checkpoint_patch(
        {
            "localized_slides": [
                {"slide_index": 3, "presentation_en": {"heading": "Old"}}
            ]
        },
        [{"slide_index": 3, "presentation_pt": {"heading": "Novo"}}],
        _V3,
    )
    assert patch is not None
    slide = cast(list[dict[str, object]], patch["localized_slides"])[0]
    assert slide["presentation_en"] == {"heading": "Old"}
    assert slide["presentation_pt"] == {"heading": "Novo"}
