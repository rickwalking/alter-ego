"""AE-0347: carousel blog body composition inputs (see carousel_blog_body_ae0347.feature)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.carousel.blog_composition import (
    research_summary_from_findings,
)
from rag_backend.application.services.carousel.editorial_distribution_constants import (
    LONG_FORM_NOTES_KEY,
)
from rag_backend.application.services.carousel.editorial_distribution_generation import (
    _build_translation_payload,
    _parse_translation_response,
)
from rag_backend.application.services.carousel.editorial_distribution_pack import (
    DistributionBuildContext,
    build_editorial_distribution_updates,
)
from rag_backend.domain.constants.ai_agents import PROMPT_EDITORIAL_SLIDE_TRANSLATIONS
from rag_backend.domain.constants.carousel import CAROUSEL_PROMPT_VERSION_V5
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.carousel import CarouselStatus

_PACK = "rag_backend.application.services.carousel.editorial_distribution_pack"
_PERSIST = "rag_backend.application.services.carousel.editorial_distribution_persist"


@pytest.mark.unit
class TestContentPromptContract:
    """Scenario: Content prompt requires long-form notes."""

    def test_v5_prompt_requests_long_form_notes(self) -> None:
        text, _cfg = render_prompt(
            "carousel",
            "content",
            variables={
                "slide_number": 1,
                "title": "T",
                "key_points": "a",
                "locale": "pt",
                "phase": "content",
                "presentation_policy_context": "",
                "persona_context": "",
            },
            version=CAROUSEL_PROMPT_VERSION_V5,
        )
        assert LONG_FORM_NOTES_KEY in text
        assert (
            "{draft_text, confidence_score, sources_used, icon_name?, long_form_notes}"
            in text
        )

    def test_v4_prompt_did_not_request_long_form_notes(self) -> None:
        """Regression anchor: the bug was the field missing from the v3/v4 contract."""
        text, _cfg = render_prompt(
            "carousel",
            "content",
            variables={
                "slide_number": 1,
                "title": "T",
                "key_points": "a",
                "locale": "pt",
                "phase": "content",
                "presentation_policy_context": "",
                "persona_context": "",
            },
            version="v4",
        )
        assert LONG_FORM_NOTES_KEY not in text

    def test_translation_prompt_requests_long_form_notes(self) -> None:
        assert LONG_FORM_NOTES_KEY in PROMPT_EDITORIAL_SLIDE_TRANSLATIONS


@pytest.mark.unit
@pytest.mark.asyncio
class TestContentAgentV5:
    """Scenario: Long-form notes survive parsing and reach the slide draft."""

    async def test_agent_renders_v5_and_keeps_notes(self) -> None:
        llm = AsyncMock()
        llm.bind = MagicMock(return_value=llm)
        payload = {
            "draft_text": "Slide copy",
            "confidence_score": 0.9,
            "sources_used": [],
            LONG_FORM_NOTES_KEY: "Para one.\n\nPara two.",
        }
        llm.ainvoke.return_value = MagicMock(content=json.dumps(payload))
        agent = ContentDraftAgent(llm=llm)
        with patch(
            "rag_backend.agents.content_draft_agent.render_prompt",
            wraps=render_prompt,
        ) as spy:
            result = await agent.draft_slide(1, "Title", ["Point"])
        assert result[LONG_FORM_NOTES_KEY] == "Para one.\n\nPara two."
        assert result["prompt_version"] == CAROUSEL_PROMPT_VERSION_V5
        assert spy.call_args.kwargs["version"] == CAROUSEL_PROMPT_VERSION_V5


@pytest.mark.unit
class TestTranslationNotes:
    """Scenario: English translation carries long-form notes."""

    def test_payload_includes_notes_when_present(self) -> None:
        payload = _build_translation_payload([
            {
                "slide_index": 1,
                "title": "H",
                "draft_text": "B",
                LONG_FORM_NOTES_KEY: "Notas Longas.",
            },
            {"slide_index": 2, "title": "H2", "draft_text": "B2"},
        ])
        assert payload[0][LONG_FORM_NOTES_KEY] == "Notas Longas."
        assert LONG_FORM_NOTES_KEY not in payload[1]

    def test_payload_index_falls_back_to_position(self) -> None:
        payload = _build_translation_payload([
            {"title": "A", "draft_text": "a"},
            {"title": "B", "draft_text": "b"},
        ])
        assert [item["slide_index"] for item in payload] == [1, 2]

    def test_parse_keeps_translated_notes(self) -> None:
        parsed = _parse_translation_response({
            "slides_en": [
                {
                    "slide_index": 1,
                    "heading": "H",
                    "body": "B",
                    LONG_FORM_NOTES_KEY: "Notes.",
                },
                {
                    "slide_index": 2,
                    "heading": "H2",
                    "body": "B2",
                    LONG_FORM_NOTES_KEY: "  ",
                },
            ]
        })
        assert parsed[1][LONG_FORM_NOTES_KEY] == "Notes."
        assert LONG_FORM_NOTES_KEY not in parsed[2]


@pytest.mark.unit
class TestResearchSummary:
    """Scenarios: Research findings feed the blog intro / absent or malformed."""

    def test_joins_deduplicated_summaries(self) -> None:
        findings = [
            {"source": "a", "summary": "First. "},
            {"source": "b", "summary": "First."},
            {"source": "c", "summary": ""},
            {"source": "d", "summary": 42},
            "junk",
            {"source": "e", "summary": "Second."},
        ]
        assert research_summary_from_findings(findings) == "First.\n\nSecond."

    @pytest.mark.parametrize("raw", [None, "", {}, 3, []])
    def test_empty_when_missing_or_malformed(self, raw: object) -> None:
        assert research_summary_from_findings(raw) == ""


def _project(title: str | None = None, title_en: str | None = None) -> CarouselProject:
    project_id = uuid4()
    return CarouselProject(
        id=project_id,
        topic="Raw English topic",
        audience="Devs",
        niche="Tech",
        status=CarouselStatus.DRAFTING,
        output_dir=f"/tmp/{project_id}",
        title=title,
        title_en=title_en,
    )


async def _run_pack(
    project: CarouselProject,
    *,
    translations: dict[int, dict[str, object]],
    research_summary: str = "",
    leading_slide: dict[str, object] | None = None,
) -> dict[str, object]:
    slide_drafts: list[dict[str, object]] = [
        *([leading_slide] if leading_slide else []),
        {
            "slide_index": 1,
            "title": "Gancho em PT",
            "draft_text": "Body one.",
            LONG_FORM_NOTES_KEY: "Notas longas.",
        },
    ]
    outline = [
        {
            "slide_index": 1,
            "title": "Gancho em PT",
            "key_points": [],
            "slide_type": "intro",
        }
    ]
    repo = MagicMock()
    repo.get_project_by_id = AsyncMock(return_value=project)
    repo.get_slides_by_project = AsyncMock(return_value=[])
    repo.create_slide = AsyncMock()
    repo.update_project = AsyncMock(side_effect=lambda p: p)
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="Caption #tag"))
    with (
        patch(f"{_PACK}.PostgresCarouselRepository", return_value=repo),
        patch(f"{_PERSIST}.PostgresCarouselRepository", return_value=repo),
        patch(
            f"{_PACK}._generate_en_translations",
            new=AsyncMock(return_value=translations),
        ),
    ):
        return await build_editorial_distribution_updates(
            DistributionBuildContext(
                db=MagicMock(),
                llm=llm,
                project_id=str(project.id),
                outline=outline,
                slide_drafts=slide_drafts,
                research_summary=research_summary,
            ),
        )


@pytest.mark.unit
@pytest.mark.asyncio
class TestBlogTitles:
    """Scenarios: Blog titles derive from the intro slide / never overwritten."""

    async def test_titles_derive_from_intro_slide(self) -> None:
        project = _project()
        updates = await _run_pack(
            project,
            translations={
                1: {
                    "heading": "Hook in EN",
                    "body": "B",
                    LONG_FORM_NOTES_KEY: "EN notes.",
                }
            },
            research_summary="Intro research.",
        )
        assert project.title == "Gancho em PT"
        assert project.title_en == "Hook in EN"
        assert str(updates["blog_markdown"]).startswith(
            "# Gancho em PT\n\nIntro research."
        )
        assert project.blog_translations is not None
        assert project.blog_translations["en"].startswith("# Hook in EN")
        assert "EN notes." in project.blog_translations["en"]

    async def test_existing_titles_are_kept(self) -> None:
        project = _project(title="Meu título", title_en="My title")
        await _run_pack(project, translations={1: {"heading": "Other", "body": "B"}})
        assert project.title == "Meu título"
        assert project.title_en == "My title"

    async def test_intro_is_selected_by_slide_index_not_position(self) -> None:
        project = _project()
        await _run_pack(
            project,
            translations={1: {"heading": "Intro EN", "body": "B"}},
            leading_slide={"slide_index": 2, "title": "Segundo", "draft_text": "b"},
        )
        assert project.title == "Gancho em PT"
        assert project.title_en == "Intro EN"

    async def test_no_en_heading_leaves_title_en_unset(self) -> None:
        project = _project()
        await _run_pack(project, translations={})
        assert project.title == "Gancho em PT"
        assert project.title_en is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestRunnerFeedsResearchFindings:
    """Scenario: Research findings feed the blog intro (state key wiring)."""

    async def test_runner_maps_research_findings_into_research_summary(self) -> None:
        from rag_backend.application.services.carousel.phase_artifact_runner import (
            PhaseArtifactRunner,
            PhaseArtifactRunnerConfig,
        )
        from rag_backend.domain.constants.workflow_state_fields import (
            STATE_FIELD_RESEARCH_FINDINGS,
        )

        runner = PhaseArtifactRunner(
            PhaseArtifactRunnerConfig(
                outline_agent=MagicMock(),
                content_agent=MagicMock(),
                llm=MagicMock(),
                image_registry=MagicMock(),
                db=MagicMock(),
                workflow_input=MagicMock(),
                slide_draft_retry=MagicMock(),
            )
        )
        state = {
            "project_id": "p1",
            STATE_FIELD_RESEARCH_FINDINGS: [
                {"source": "a", "summary": "Alpha."},
                {"source": "b", "summary": "Alpha."},
                {"source": "c", "summary": "Beta."},
            ],
        }
        captured: list[DistributionBuildContext] = []

        async def _fake_build(
            ctx: DistributionBuildContext, **_kw: object
        ) -> dict[str, object]:
            captured.append(ctx)
            return {}

        with (
            patch(
                "rag_backend.application.services.carousel.phase_artifact_runner.build_editorial_distribution_updates",
                new=_fake_build,
            ),
            patch("rag_backend.infrastructure.container.get_container") as container,
        ):
            container.return_value.linkedin_post_generator.return_value = None
            await runner._build_distribution_if_needed(
                state,  # type: ignore[arg-type]
                [{"slide_index": 1}],
                ([{"slide_index": 1, "draft_text": "x"}], {"slide_drafts": True}),
            )
        assert captured and captured[0].research_summary == "Alpha.\n\nBeta."


@pytest.mark.unit
@pytest.mark.asyncio
class TestContentAgentNotesHardening:
    """Scenarios: notes sanitized at the source; missing notes are observable."""

    async def test_notes_are_case_preserving_sanitized(self) -> None:
        llm = AsyncMock()
        llm.bind = MagicMock(return_value=llm)
        payload = {
            "draft_text": "Slide",
            "confidence_score": 0.5,
            "sources_used": [],
            LONG_FORM_NOTES_KEY: "Keep Case <b>(x)</b>.",
        }
        llm.ainvoke.return_value = MagicMock(content=json.dumps(payload))
        result = await ContentDraftAgent(llm=llm).draft_slide(1, "T", ["p"])
        assert result[LONG_FORM_NOTES_KEY] == "Keep Case bx/b."

    async def test_missing_notes_logs_warning(self) -> None:
        llm = AsyncMock()
        llm.bind = MagicMock(return_value=llm)
        payload = {"draft_text": "Slide", "confidence_score": 0.5, "sources_used": []}
        llm.ainvoke.return_value = MagicMock(content=json.dumps(payload))
        with patch("rag_backend.agents.content_draft_agent.logger") as log:
            # Distinct prompt: the AI response cache is process-global.
            result = await ContentDraftAgent(llm=llm).draft_slide(2, "No notes", ["q"])
        assert LONG_FORM_NOTES_KEY not in result
        log.warning.assert_called_once()
