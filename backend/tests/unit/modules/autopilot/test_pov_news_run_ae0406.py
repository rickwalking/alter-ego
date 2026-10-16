"""A ``pov_news`` run: thesis step, spec, project fields and gate (AE-0406).

Gherkin: tests/features/autopilot_pov_news_ae0406.feature
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from rag_backend.domain.models import CarouselProject
from rag_backend.domain.news_quote_cards import quote_card
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.api.mapping import command_from, response_from
from rag_backend.modules.autopilot.api.schemas import TopicBatch
from rag_backend.modules.autopilot.application.run_spec import (
    project_spec,
    spec_refusal,
    with_inputs,
)
from rag_backend.modules.autopilot.application.topic_intake import TopicIntakeResult
from rag_backend.modules.autopilot.constants import GATE_CONTENT, GATE_DESIGN
from rag_backend.modules.autopilot.domain.gate import (
    GateSnapshot,
    QualityViolation,
    SnapshotParts,
)
from rag_backend.modules.autopilot.domain.intake import TopicRejection
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
)
from rag_backend.modules.autopilot.domain.snapshot import assemble_snapshot
from rag_backend.modules.autopilot.domain.thesis import (
    is_pov,
    needs_thesis,
    thesis_prompt_text,
)
from rag_backend.modules.autopilot.domain.x_observation import (
    ObservedPostInput,
    classify_post,
)
from rag_backend.modules.autopilot.infrastructure.pov_project import pov_fields_for
from rag_backend.modules.autopilot.infrastructure.quote_gate import quote_violations
from rag_backend.modules.autopilot.infrastructure.topic_rows import (
    topic_from_row,
    topic_row,
)
from tests.unit.autopilot.news_quote_support import POST_URL, THESIS, quote
from tests.unit.autopilot.support import snowflake_id
from tests.unit.modules.autopilot.project_inputs_fake import (
    FAKE_HOOK_ASSET_ID,
    FakeProjectInputs,
)

_Q1 = quote()
_OWNER = "owner-1"


def _topic(content_mode: str | None = "pov_news") -> TopicCandidate:
    return TopicCandidate(
        candidate_id=uuid4(),
        title="Agentes em paralelo",
        angle="a",
        why_viral="w",
        audience="devs",
        niche="agentes",
        brief="b",
        sources=(POST_URL, "https://www.anthropic.com/news/x"),
        score=78,
        signal_hash="h",
        status="accepted",
        content_mode=content_mode,
        thesis_draft=THESIS,
        pov_format="comparacao",
        slide_count=10,
        quotes=(_Q1,) if content_mode == "pov_news" else (),
    )


def _run(thesis: str | None = THESIS) -> AutopilotRun:
    return AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=None,
        state=AutopilotRunState.QUEUED,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
        pov_thesis=thesis,
    )


class TestThesisStep:
    # Scenario: A pov_news run waits for the thesis like POV
    def test_pov_news_needs_a_confirmed_thesis(self) -> None:
        assert is_pov(_topic()) is True
        assert needs_thesis(_run(thesis=None), _topic()) is True
        assert needs_thesis(_run(), _topic()) is False
        assert needs_thesis(_run(thesis=None), _topic("news_analysis")) is False

    def test_the_prompt_names_the_mode(self) -> None:
        assert thesis_prompt_text(_topic()).startswith(
            "🧭 Ponto de Vista: Notícia proposto"
        )
        assert thesis_prompt_text(_topic("pov")).startswith(
            "🧭 Ponto de Vista proposto"
        )


class TestSpec:
    # Scenario: The carousel is a POV deck with the news voice
    def test_spec_carries_the_pov_inputs_and_quotes(self) -> None:
        spec = project_spec(_run(), _topic(), _OWNER)
        assert spec.content_mode == "pov_news"
        assert spec.pov_thesis == THESIS
        assert spec.pov_format == "opiniao"  # stored topic format is ignored
        assert spec.slide_count == 10
        assert spec.quotes == (_Q1,)
        assert spec.image_style == "neo_anime"

    @pytest.mark.asyncio
    async def test_photo_and_refusal_follow_pov(self) -> None:
        spec = project_spec(_run(), _topic(), _OWNER)
        ready = await with_inputs(spec, FakeProjectInputs())
        assert ready.hook_asset_id == FAKE_HOOK_ASSET_ID
        assert spec_refusal(ready) is None
        missing = await with_inputs(spec, FakeProjectInputs(hook=None))
        assert spec_refusal(missing) == "hook_photo_missing"

    def test_project_fields_carry_quotes_and_sources(self) -> None:
        spec = replace(
            project_spec(_run(), _topic(), _OWNER), hook_asset_id=FAKE_HOOK_ASSET_ID
        )
        fields = pov_fields_for(spec)
        assert fields["pov_quotes"] == (_Q1,)
        assert fields["pov_sources"] == _topic().sources
        assert fields["pov_format"] == "opiniao"
        pov = pov_fields_for(replace(spec, content_mode="pov"))
        assert pov["pov_quotes"] == () and pov["pov_sources"] == ()


class TestRows:
    def test_topic_row_round_trips_quotes(self) -> None:
        topic = _topic()
        row = topic_row(topic)
        assert row.quotes == [_Q1.to_row()]
        assert topic_from_row(row).quotes == (_Q1,)
        assert topic_row(_topic("pov")).quotes is None

    def test_project_row_round_trips_quotes_and_sources(self) -> None:
        entity = CarouselProject(topic="t", audience="a", niche="n")
        entity.content_mode = "pov_news"
        entity.pov_quotes = (_Q1,)
        entity.pov_sources = (POST_URL,)
        model = CarouselProjectModel.from_entity(entity)
        assert model.pov_quotes == [_Q1.to_row()]
        fields = model.content_mode_fields()
        assert fields["pov_quotes"] == (_Q1,)
        assert fields["pov_sources"] == (POST_URL,)
        empty = CarouselProjectModel.from_entity(
            CarouselProject(topic="t", audience="a", niche="n")
        )
        assert empty.pov_quotes is None and empty.pov_sources is None
        assert empty.content_mode_fields()["pov_sources"] == ()


@dataclass
class _Acl:
    project: CarouselProject | None

    async def load_project(self, project_id: str) -> CarouselProject | None:
        del project_id
        return self.project


def _news_project() -> CarouselProject:
    project = CarouselProject(topic="t", audience="a", niche="n")
    project.content_mode = "pov_news"
    project.pov_quotes = (_Q1,)
    return project


def _state(pt_text: str) -> dict[str, object]:
    return {
        "current_phase": GATE_CONTENT,
        "localized_slides": [
            {
                "slide_index": 4,
                "presentation_pt": {"insight": quote_card(_Q1, pt_text)},
                "presentation_en": {"insight": quote_card(_Q1, _Q1.text_en)},
            },
            "junk",
        ],
    }


class TestGate:
    # Scenario: The autopilot content gate blocks an altered quote card
    @pytest.mark.asyncio
    async def test_altered_card_is_a_quality_violation(self) -> None:
        acl = _Acl(_news_project())
        found = await quote_violations(acl, "p", _state("Texto alterado."))
        assert [(v.rule, v.slide_index, v.locale) for v in found] == [
            ("quote_not_verbatim", 4, "pt")
        ]
        assert await quote_violations(acl, "p", _state(_Q1.text_pt)) == ()

    @pytest.mark.asyncio
    async def test_other_modes_and_missing_projects_are_not_checked(self) -> None:
        pov = _news_project()
        pov.content_mode = "pov"
        assert await quote_violations(_Acl(pov), "p", _state("x")) == ()
        assert await quote_violations(_Acl(None), "p", _state("x")) == ()
        news = _Acl(_news_project())
        assert await quote_violations(news, "p", {"localized_slides": "x"}) == ()

    @pytest.mark.asyncio
    async def test_too_many_cards_is_a_deck_violation(self) -> None:
        slide = _state(_Q1.text_pt)["localized_slides"]
        assert isinstance(slide, list)
        state = {"localized_slides": [slide[0], slide[0], slide[0]]}
        found = await quote_violations(_Acl(_news_project()), "p", state)
        assert [v.rule for v in found] == ["too_many_quote_cards"]
        assert "at most 2" in found[0].message

    def test_quote_violations_block_only_the_content_gate(self) -> None:
        violation = QualityViolation(rule="quote_not_verbatim", slide_index=4)

        def snapshot(phase: str) -> GateSnapshot:
            return assemble_snapshot(
                SnapshotParts(
                    state={"current_phase": phase},
                    images=(),
                    slides_total=9,
                    lock_version=1,
                    stale=False,
                    quote_violations=(violation,),
                )
            )

        assert snapshot(GATE_CONTENT).quality_violations == (violation,)
        assert snapshot(GATE_DESIGN).quality_violations == ()


class TestApi:
    def _body(self, quote_extra: dict[str, object] | None = None) -> dict[str, object]:
        row: dict[str, object] = {**_Q1.to_row(), **(quote_extra or {})}
        return {
            "topics": [
                {
                    "mode": "pov_news",
                    "title": "t",
                    "angle": "a",
                    "why_viral": "w",
                    "audience": "devs",
                    "niche": "ia",
                    "brief": "b t",
                    "sources": [POST_URL],
                    "score": 70,
                    "thesis_draft": THESIS,
                    "quotes": [row],
                }
            ]
        }

    # PR #124 review: a missing quote field rejects one topic, not the batch.
    def test_a_missing_quote_field_is_not_a_schema_error(self) -> None:
        body = self._body()
        topics = body["topics"]
        assert isinstance(topics, list)
        quotes = topics[0]["quotes"]
        assert isinstance(quotes, list)
        del quotes[0]["text_en"]
        (proposal,) = command_from(TopicBatch.model_validate(body)).proposals
        assert proposal.quotes[0].text_en == ""
        assert proposal.quotes[0].text_pt == _Q1.text_pt

    def test_batch_maps_quotes_and_index(self) -> None:
        command = command_from(TopicBatch.model_validate(self._body()))
        (proposal,) = command.proposals
        assert proposal.content_mode == "pov_news"
        assert proposal.index == 0
        assert proposal.quotes == (_Q1,)

    # Scenario: An unknown key inside a quote is still a 422
    def test_unknown_quote_key_is_rejected_by_the_schema(self) -> None:
        with pytest.raises(ValidationError):
            TopicBatch.model_validate(self._body({"avatar_asset_id": "a1"}))

    def test_unknown_mode_is_rejected_by_the_schema(self) -> None:
        body = self._body()
        topics = body["topics"]
        assert isinstance(topics, list)
        topics[0]["mode"] = "pov_screenshot"
        with pytest.raises(ValidationError):
            TopicBatch.model_validate(body)

    def test_response_carries_index_and_field(self) -> None:
        result = TopicIntakeResult(
            accepted=(),
            queued=(),
            rejected=(
                TopicRejection(
                    title="t",
                    reason="quote_too_long",
                    index=2,
                    field="quotes[0].text_pt",
                ),
                TopicRejection(title="u", reason="daily_cap_reached", index=1),
            ),
        )
        body = response_from(result).model_dump(exclude_none=True)
        assert body["rejected"] == [
            {
                "index": 2,
                "title": "t",
                "reason": "quote_too_long",
                "field": "quotes[0].text_pt",
            },
            {"index": 1, "title": "u", "reason": "daily_cap_reached"},
        ]


class TestXSignalsText:
    def test_line_breaks_are_stored_as_spaces(self) -> None:
        moment = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)
        post = ObservedPostInput(
            url=f"https://x.com/kanishksj01/status/{snowflake_id(moment)}",
            handle="kanishksj01",
            text="First line.\r\nSecond\tline \x00ok",
            likes=None,
            reposts=None,
            replies=None,
            views=None,
            observed_at=moment,
        )
        accepted = classify_post(post, moment)
        assert getattr(accepted, "text", None) == "First line. Second line ok"
