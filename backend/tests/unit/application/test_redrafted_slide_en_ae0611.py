"""The EN copy of a slide follows the fail-closed retry's re-draft.

Gherkin: tests/features/redrafted_slide_en_copy_ae0611.feature
Synthetic slides. Real localized builder, real fail-closed chain and real gate
validation; the retry and the translator are doubles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import pytest
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.content_fail_closed import (
    FailClosedReviewCommand,
    build_fail_closed_review_updates,
)
from rag_backend.application.services.carousel.redrafted_translation import (
    LOG_REDRAFT_TRANSLATION_MISSING,
)
from tests.unit.application.content_quality_fixtures_ae0366 import clean_drafts
from tests.unit.application.owner_autofix_fixtures_ae0367 import V3

_PROJECT = "ae0611-shape"
_SLIDE = 3
_OTHER_SLIDE = 4
_PT = "presentation_pt"
_EN = "presentation_en"
_UNPARSABLE = "## PT\n**Heading:**\n**Body:**\n## EN\n**Heading:**\n**Body:**\n"
_OLD_HEADING = "Old english heading"
_OLD_BODY = "Old english body about the slide that is gone."
_NEW_HEADING_PT = "Regra nova para o time"
_NEW_BODY_PT = "Eu escrevo a regra nova antes de abrir o pedido."
_NEW_HEADING_EN = "A new rule for the team"
_NEW_BODY_EN = "I write the new rule before I open the request."
_SCAFFOLD = (
    f"## PT\n**Heading:** {_NEW_HEADING_PT}\n**Body:** {_NEW_BODY_PT}\n"
    "## EN\n**Heading:** Scaffold heading\n**Body:** Scaffold body in english.\n"
)


def _plain(slide_index: int, **extras: object) -> dict[str, object]:
    return {
        "slide_index": slide_index,
        "slide_type": "content",
        "title": _NEW_HEADING_PT,
        "draft_text": _NEW_BODY_PT,
        **extras,
    }


def _translation(draft: dict[str, object]) -> dict[str, object]:
    """The stored EN of a slide: its shape, with copy the re-draft must replace."""
    index = draft["slide_index"]
    en = cast(dict[str, object], draft[_EN])
    return {**en, "heading": f"{_OLD_HEADING} {index}", "body": f"{_OLD_BODY} {index}"}


def _deck(
    *failing: int,
) -> tuple[list[dict[str, object]], dict[int, dict[str, object]]]:
    """A plain deck (PT copy plus a translation); ``failing`` slides block."""
    drafts: list[dict[str, object]] = []
    translations: dict[int, dict[str, object]] = {}
    for draft in clean_drafts():
        translations[int(draft["slide_index"])] = _translation(draft)
        plain = {key: value for key, value in draft.items() if key != _EN}
        if draft["slide_index"] in failing:
            plain.pop(_PT)
            plain.update(title="", draft_text=_UNPARSABLE)
        drafts.append(plain)
    return drafts, translations


@dataclass
class _Translator:
    """Records every call; answers the slides it gets unless told otherwise."""

    answer: dict[int, dict[str, object]] | None = None
    error: Exception | None = None
    calls: list[list[dict[str, object]]] = field(default_factory=list)

    async def __call__(
        self, drafts: list[dict[str, object]]
    ) -> dict[int, dict[str, object]]:
        self.calls.append(drafts)
        if self.error is not None:
            raise self.error
        if self.answer is not None:
            return self.answer
        return {
            int(d["slide_index"]): {"heading": _NEW_HEADING_EN, "body": _NEW_BODY_EN}
            for d in drafts
        }


def _retry(**fresh_by_slide: dict[str, object]):
    async def retry(slide_index: int) -> dict[str, object] | None:
        return fresh_by_slide.get(f"s{slide_index}")

    return retry


async def _run(
    drafts: list[dict[str, object]],
    translations: dict[int, dict[str, object]] | None,
    context: tuple[object, _Translator],
) -> dict[str, object]:
    retry, translate = context
    return await build_fail_closed_review_updates(
        FailClosedReviewCommand(
            project_id=_PROJECT,
            slide_drafts=drafts,
            translations_en=translations,
            policy_version=V3,
            retry_draft=retry,
            translate_slides=translate,
        )
    )


def _slide(updates: dict[str, object], slide_index: int) -> dict[str, object]:
    slides = updates["localized_slides"]
    assert isinstance(slides, list)
    return next(slide for slide in slides if slide["slide_index"] == slide_index)


def _en(updates: dict[str, object], slide_index: int) -> dict[str, object]:
    return _slide(updates, slide_index)[_EN]


def _blocking_slides(updates: dict[str, object]) -> set[int]:
    report = updates["content_gate_validation"]
    assert isinstance(report, dict)
    return {item["slide_index"] for item in report.get("violations", [])}


@pytest.mark.unit
class TestRedraftedSlideEn:
    async def test_en_follows_the_new_pt(self) -> None:
        """Scenario: A re-drafted slide gets its EN copy from the new PT."""
        drafts, translations = _deck(_SLIDE)
        translate = _Translator()

        updates = await _run(
            drafts, translations, (_retry(s3=_plain(_SLIDE)), translate)
        )

        assert _slide(updates, _SLIDE)[_PT]["heading"] == _NEW_HEADING_PT
        assert _en(updates, _SLIDE)["heading"] == _NEW_HEADING_EN
        assert _en(updates, _SLIDE)["body"] == _NEW_BODY_EN
        stored = updates["translations_en"]
        assert stored[str(_SLIDE)]["heading"] == _NEW_HEADING_EN

    async def test_only_the_redrafted_slides_in_one_call(self) -> None:
        """Scenario: Only the re-drafted slides are translated, in one call."""
        drafts, translations = _deck(_SLIDE, _OTHER_SLIDE)
        translate = _Translator()

        updates = await _run(
            drafts,
            translations,
            (
                _retry(s3=_plain(_SLIDE), s4=_plain(_OTHER_SLIDE)),
                translate,
            ),
        )

        assert len(translate.calls) == 1
        assert [d["slide_index"] for d in translate.calls[0]] == [_SLIDE, _OTHER_SLIDE]
        assert _en(updates, 5)["heading"] == f"{_OLD_HEADING} 5"
        assert updates["translations_en"]["5"] == translations[5]

    async def test_the_translator_sees_the_recovered_pt(self) -> None:
        """Scenario: The translator sees the PT copy the reviewer will see."""
        drafts, translations = _deck(_SLIDE)
        translate = _Translator()
        fresh = _plain(_SLIDE, title="", draft_text=_SCAFFOLD)

        await _run(drafts, translations, (_retry(s3=fresh), translate))

        (source,) = translate.calls[0]
        assert source[_PT]["heading"] == _NEW_HEADING_PT
        assert source[_PT]["body"] == _NEW_BODY_PT
        assert "## PT" not in str(source[_PT])

    async def test_a_redraft_with_its_own_en_needs_no_call(self) -> None:
        """Scenario: A re-draft that carries its own EN needs no translation."""
        drafts, translations = _deck(_SLIDE)
        translate = _Translator()
        pt = {"slide_type": "content", "heading": _NEW_HEADING_PT, "body": _NEW_BODY_PT}
        en = {"slide_type": "content", "heading": _NEW_HEADING_EN, "body": _NEW_BODY_EN}
        fresh = _plain(_SLIDE, presentation_pt=pt, presentation_en=en)

        updates = await _run(drafts, translations, (_retry(s3=fresh), translate))

        assert translate.calls == []
        assert _en(updates, _SLIDE)["heading"] == _NEW_HEADING_EN

    async def test_a_failed_translation_drops_the_old_en(self) -> None:
        """Scenario: A failed translation never keeps the old EN copy."""
        drafts, translations = _deck(_SLIDE)
        translate = _Translator(error=ValueError("en_translation_parse_failed"))

        with capture_logs() as logs:
            updates = await _run(
                drafts, translations, (_retry(s3=_plain(_SLIDE)), translate)
            )

        assert _OLD_HEADING not in str(_en(updates, _SLIDE))
        assert _OLD_BODY not in str(_en(updates, _SLIDE))
        missing = [e for e in logs if e["event"] == LOG_REDRAFT_TRANSLATION_MISSING]
        assert [entry["slides"] for entry in missing] == [[_SLIDE]]
        assert missing[0]["error"] == "en_translation_parse_failed"
        assert str(_SLIDE) not in updates["translations_en"]
        assert _SLIDE in _blocking_slides(updates)

    async def test_a_skipped_slide_drops_the_old_en(self) -> None:
        """Scenario: A translation that skips the slide never keeps the old EN copy."""
        drafts, translations = _deck(_SLIDE, _OTHER_SLIDE)
        translate = _Translator(
            answer={_OTHER_SLIDE: {"heading": _NEW_HEADING_EN, "body": _NEW_BODY_EN}}
        )

        with capture_logs() as logs:
            updates = await _run(
                drafts,
                translations,
                (
                    _retry(s3=_plain(_SLIDE), s4=_plain(_OTHER_SLIDE)),
                    translate,
                ),
            )

        assert _OLD_HEADING not in str(_en(updates, _SLIDE))
        assert _en(updates, _OTHER_SLIDE)["heading"] == _NEW_HEADING_EN
        missing = [e for e in logs if e["event"] == LOG_REDRAFT_TRANSLATION_MISSING]
        assert [entry["slides"] for entry in missing] == [[_SLIDE]]

    async def test_no_redraft_no_call(self) -> None:
        """Scenario: Nothing is translated when no slide was re-drafted."""
        drafts, translations = _deck(_SLIDE)
        translate = _Translator()

        updates = await _run(drafts, translations, (_retry(), translate))

        assert translate.calls == []
        assert updates["translations_en"][str(_SLIDE)] == translations[_SLIDE]

    async def test_no_stored_translations_no_call(self) -> None:
        """Scenario: Nothing is translated for a deck without stored translations."""
        drafts, _ = _deck(_SLIDE)
        translate = _Translator()

        await _run(drafts, None, (_retry(s3=_plain(_SLIDE)), translate))

        assert translate.calls == []
