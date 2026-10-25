"""The content gate repairs only the failing fields, at most 2 rounds.

Gherkin: tests/features/content_gate_repair_ae0430.feature (section A + the
residual shape mismatch of section C). The model is a fake; the validator and
the policy are the real ones.
"""

from __future__ import annotations

from typing import cast

import pytest

from rag_backend.application.services.carousel.content_gate_repair import (
    GateRepairCommand,
    run_gate_repair,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_TRANSLATION_SHAPE_MISMATCH,
)
from rag_backend.domain.constants.content_gate_repair import (
    GATE_REPAIR_MAX_ROUNDS,
    GATE_REPAIR_PROBLEM_MISSING_EN,
)
from tests.unit.application.content_gate_repair_fixtures_ae0430 import (
    POLICY_V4,
    PROD_ANSWERS,
    FakeRepairer,
    OverLimitRepairer,
    load_fixture,
    prod_slides,
)

PROD_FAILING_IDS = sorted(PROD_ANSWERS)


def _command(
    repairer: FakeRepairer, slides: list[dict[str, object]] | None = None
) -> GateRepairCommand:
    return GateRepairCommand(
        slides=prod_slides() if slides is None else slides,
        repairer=repairer,
        policy_version=POLICY_V4,
    )


def _slide(slides: list[dict[str, object]], index: int) -> dict[str, object]:
    return next(slide for slide in slides if slide.get("slide_index") == index)


def _payload(
    slides: list[dict[str, object]], index: int, locale: str
) -> dict[str, object]:
    return cast(dict[str, object], _slide(slides, index)[f"presentation_{locale}"])


def _items(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], payload[key])


@pytest.mark.unit
class TestProdFixture:
    def test_fixture_reproduces_the_prod_report(self) -> None:
        """Background: the exported slides validate to the prod blockers.

        the same exported state carries the label/emphasis leaks the
        QA hand-noted (``**PT**`` on slide 1, ``**PT** ** **`` and
        ``PT:\\nHeading:`` on slide 4, EN ``**…**`` on slide 3). The stricter
        gate adds those 4 violations to the 12 stored ones.
        """
        report = validate_localized_slides(prod_slides(), policy_version=POLICY_V4)
        stored = cast(dict[str, object], load_fixture()["content_gate_validation"])
        stored_violations = cast(list[object], stored["violations"])
        assert report.blocking is True
        stored_codes = [cast(dict[str, object], v)["code"] for v in stored_violations]
        codes = [violation.code for violation in report.violations]
        assert sorted(stored_codes) == sorted([
            code for code in codes if code in set(stored_codes)
        ])
        new = {
            (violation.locale, violation.field, violation.code)
            for violation in report.violations
            if violation.code not in set(stored_codes)
        }
        assert new == {
            ("pt", "body", "drafting_scaffold_present"),
            ("en", "body", "drafting_scaffold_present"),
            ("en", "body", "emphasis_markup_locale_mismatch"),
            ("pt", "summary_points[0].body", "copy_truncated"),
            ("pt", "summary_points[2].body", "copy_truncated"),
            ("en", "summary_points[0].body", "copy_truncated"),
            ("en", "summary_points[2].body", "copy_truncated"),
        }


@pytest.mark.unit
@pytest.mark.asyncio
class TestTargetedRepair:
    async def test_prod_fixture_asks_only_failing_fields_and_ends_green(self) -> None:
        """Scenario: The regression fixture from prod ends green.

        Slide 4 is in the changed set because its PT and EN bodies carried the "**PT**
        ** **" and "PT:" label leaks the stricter gate flags.
        """
        repairer = FakeRepairer()

        outcome = await run_gate_repair(_command(repairer))

        assert repairer.calls == [PROD_FAILING_IDS]
        assert outcome.report.blocking is False
        assert outcome.report.violations == []
        assert outcome.changed_indices == frozenset({1, 2, 3, 4, 6})

    async def test_over_limit_field_repaired_in_one_round(self) -> None:
        """Scenario: An over-limit field is repaired in one round."""
        repairer = FakeRepairer()

        outcome = await run_gate_repair(_command(repairer))

        request = repairer.requests[0]
        target = next(
            t for t in request.targets if t.target_id == "3:en:features[0].body"
        )
        assert len(target.text) == 121
        assert target.max_characters == 100
        assert target.slide_heading == "Ele não usa o seu notebook"
        assert target.source_text.startswith("Navegador, terminal e arquivos")
        assert any(problem.startswith("body_too_long") for problem in target.problems)
        features = _items(_payload(outcome.slides, 3, "en"), "features")
        assert features[0]["body"] == PROD_ANSWERS["3:en:features[0].body"]
        assert len(repairer.calls) == 1

    async def test_two_rounds_then_stop_with_violations_shown(self) -> None:
        """Scenario: Two rounds then stop with the violations shown.

        The over-long answer is never truncated; it is kept whole for the owner.
        """
        repairer = OverLimitRepairer()

        outcome = await run_gate_repair(_command(repairer))

        assert len(repairer.calls) == GATE_REPAIR_MAX_ROUNDS
        assert outcome.report.blocking is True
        codes = {violation.code for violation in outcome.report.violations}
        assert "body_too_long" in codes
        body = _items(_payload(outcome.slides, 6, "pt"), "actions")[0]["body"]
        assert str(body).endswith("E ainda mais um trecho longo aqui.")

    async def test_repair_never_touches_fields_that_pass(self) -> None:
        """Scenario: The repair never touches fields that pass."""
        slides = prod_slides()
        heading = _payload(slides, 6, "pt")["heading"]
        answers = {**PROD_ANSWERS, "6:pt:heading": "Um título que ninguém pediu."}
        repairer = FakeRepairer(answers)

        outcome = await run_gate_repair(_command(repairer, slides))

        assert "6:pt:heading" not in repairer.calls[0]
        assert _payload(outcome.slides, 6, "pt")["heading"] == heading
        assert _payload(outcome.slides, 5, "pt") == _payload(prod_slides(), 5, "pt")

    async def test_failing_model_leaves_copy_and_report(self) -> None:
        """Scenario: A failing model leaves the copy and the report as they were."""
        slides = [s for s in prod_slides() if s["slide_index"] != 1]
        repairer = FakeRepairer(fail=True)

        outcome = await run_gate_repair(_command(repairer, slides))

        assert len(repairer.calls) == 1
        assert outcome.slides == slides
        assert outcome.changed_indices == frozenset()
        assert outcome.report.blocking is True

    async def test_empty_or_unchanged_answers_are_ignored(self) -> None:
        """Scenario: An answer that is empty or the same text changes nothing."""
        slides = [s for s in prod_slides() if s["slide_index"] != 1]
        current = str(_items(_payload(slides, 3, "pt"), "features")[0]["body"])
        repairer = FakeRepairer({
            "3:pt:features[0].body": current,
            "6:pt:actions[0].body": " ",
        })

        outcome = await run_gate_repair(_command(repairer, slides))

        assert outcome.changed_indices == frozenset()
        assert len(repairer.calls) == GATE_REPAIR_MAX_ROUNDS

    async def test_valid_slides_never_call_the_model(self) -> None:
        """Scenario: A gate that passes runs no repair round."""
        repairer = FakeRepairer()
        first = await run_gate_repair(_command(repairer))
        again = FakeRepairer()

        outcome = await run_gate_repair(_command(again, first.slides))

        assert again.calls == []
        assert outcome.changed_indices == frozenset()


@pytest.mark.unit
@pytest.mark.asyncio
class TestResidualShapeMismatch:
    async def test_missing_en_tldr_is_filled_from_pt_and_translated(self) -> None:
        """Scenario: A residual shape mismatch is filled from PT and translated."""
        repairer = FakeRepairer()

        outcome = await run_gate_repair(_command(repairer))

        target = next(
            t for t in repairer.requests[0].targets if t.target_id == "1:en:tldr_strip"
        )
        assert target.problems[0] == GATE_REPAIR_PROBLEM_MISSING_EN
        assert target.source_text == _payload(prod_slides(), 1, "pt")["tldr_strip"]
        en = _payload(outcome.slides, 1, "en")
        assert en["tldr_strip"] == PROD_ANSWERS["1:en:tldr_strip"]
        codes = {violation.code for violation in outcome.report.violations}
        assert VIOLATION_TRANSLATION_SHAPE_MISMATCH not in codes

    async def test_missing_en_items_are_filled_with_pt_shape(self) -> None:
        """Scenario: EN lacking the PT item list gets the PT items to translate.

        The copies must be translated to stay (see the scenario "A PT copy nobody
        translated is taken out of EN again").
        """
        slides = prod_slides()
        en = _payload(slides, 6, "en")
        en.pop("actions")
        answers = {
            f"6:en:actions[{n}].{key}": f"Action {n} {key} in English"
            for n in range(3)
            for key in ("title", "body")
        }
        repairer = FakeRepairer(answers)

        outcome = await run_gate_repair(_command(repairer, slides))

        asked = repairer.calls[0]
        assert "6:en:actions[0].title" in asked
        assert "6:en:actions[2].body" in asked
        actions = _items(_payload(outcome.slides, 6, "en"), "actions")
        pt_actions = _items(_payload(outcome.slides, 6, "pt"), "actions")
        assert [a["icon_name"] for a in actions] == [a["icon_name"] for a in pt_actions]
        assert actions[0]["title"] == "Action 0 title in English"
