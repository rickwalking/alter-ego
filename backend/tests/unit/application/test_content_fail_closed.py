"""Unit tests for the AE-0309 fail-closed content review chain.

Gherkin: tests/features/carousel_content_fail_closed.feature
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from structlog.testing import capture_logs

from rag_backend.agents.carousel_workflow_engine import _REVIEW_INTERRUPT_KEYS
from rag_backend.agents.carousel_workflow_nodes import content_phase
from rag_backend.application.services.carousel import content_fail_closed
from rag_backend.application.services.carousel.content_fail_closed import (
    LOG_EVENT_SLIDE_PARSE_FAILED,
    REPAIR_OUTCOME_DETERMINISTIC,
    REPAIR_OUTCOME_RETRY,
    REPAIR_OUTCOME_UNREPAIRED,
    FailClosedReviewCommand,
    build_fail_closed_review_updates,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    build_localized_slides_with_failures,
)
from rag_backend.application.services.carousel.presentation_review import (
    has_blocking_presentation_validation,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    PresentationReviewBuildResult,
    build_presentation_review_updates_async,
)
from rag_backend.application.services.carousel.slide_parse_failures import (
    PARSE_FAILURE_MISSING_CANONICAL_KEYS,
    PARSE_FAILURE_RAW_DRAFT_FALLBACK,
)
from rag_backend.application.services.carousel.workflow_state import (
    get_initial_carousel_state,
)
from rag_backend.domain.constants.carousel import LANGUAGE_PT
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_SLIDE_PARSE_FAILED,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_CONTENT_GATE_VALIDATION,
)

_PROJECT_ID = "38affb3e-c219-4c56-9838-9cae7094f767"
_GATE_KEY = STATE_FIELD_CONTENT_GATE_VALIDATION
_SCAFFOLD_LABELS = ("## PT", "## EN", "## Image Prompt", "**Heading:**", "**Body:**")

# Reproduction of the prod incident payload (project 38affb3e, slide 4,
# 2026-07-07): the PT extraction failed and the ENTIRE raw drafting scaffold
# (~1147 chars, "## PT / **Heading:** / **Body:** / **Features:** / ## EN /
# ## Image Prompt") was stored as presentation_pt.body.
INCIDENT_SCAFFOLD_DRAFT = """## PT
**Heading:** O disparo silencioso que corrompeu o slide quatro
**Body:** A verdade incomoda: equipes tratam a regeneracao de conteudo como uma operacao segura, mas cada nova rodada reescreve artefatos que ja tinham sido aprovados pelo revisor humano. Quando o parser falha, o texto bruto inteiro vaza para o corpo visivel do slide e ninguem percebe ate a fase de design apontar as violacoes. O custo real aparece horas depois, em cirurgia manual de checkpoint em producao, num fluxo que deveria ter travado no proprio passo de conteudo.
**Features:**
- Regeneracao segura: valide cada payload no momento exato da escrita
- Reparo deterministico: extraia o texto util antes de acionar o modelo
- Gate bloqueante: mostre a violacao ao revisor no passo de conteudo
## EN
**Heading:** The silent regeneration that corrupted slide four
**Body:** The uncomfortable truth: teams treat content regeneration as a safe operation, but every new pass rewrites artifacts a human reviewer already approved. When the parser fails, the entire raw draft leaks into the slide's visible body and nobody notices until the design phase flags the violations hours later.
## Image Prompt
Neon comic panel of a robot editor shredding a corrupted slide, dark plasma background, high contrast lighting.
"""

# A draft whose scaffold carries no extractable copy: extraction, label
# stripping, and shape normalization all fail, so only the LLM retry (or the
# blocking report) can resolve it.
UNRECOVERABLE_SCAFFOLD_DRAFT = (
    "## PT\n**Heading:**\n**Body:**\n## EN\n**Heading:**\n**Body:**\n"
)

_CONTENT_BODY_BUDGET = 220


def _content_draft(draft_text: str, *, slide_index: int = 4) -> dict[str, object]:
    return {
        "slide_index": slide_index,
        "slide_type": "content",
        "title": "Fluxo editorial sob controle",
        "draft_text": draft_text,
    }


def _clean_drafts() -> list[dict[str, object]]:
    """Seven canonical drafts that parse cleanly (no repair or retry needed)."""
    drafts: list[dict[str, object]] = [
        {
            "slide_index": 1,
            "slide_type": "intro",
            "title": "Gancho inicial",
            "draft_text": "Uma promessa curta e concreta para abrir o carrossel.",
        }
    ]
    for index in range(2, 7):
        drafts.append({
            "slide_index": index,
            "slide_type": "content",
            "title": f"Insight numero {index}",
            "draft_text": f"Detalhe pratico e verificavel do insight {index}.",
            "content_kind": "features",
            "features": [
                {
                    "icon_name": "target",
                    "title": f"Pratica {index}",
                    "body": "Aplique no proximo ciclo.",
                }
            ],
        })
    drafts.append({
        "slide_index": 7,
        "slide_type": "cta",
        "title": "Chamada final",
        "draft_text": "Siga o perfil para acompanhar a serie completa.",
    })
    return drafts


class _RetryDouble:
    """Injectable fail-then-succeed draft double for the single LLM retry."""

    def __init__(self, replacement: dict[str, object] | None) -> None:
        self.calls: list[int] = []
        self._replacement = replacement

    async def __call__(self, slide_index: int) -> dict[str, object] | None:
        self.calls.append(slide_index)
        if self._replacement is None:
            return None
        return {**self._replacement, "slide_index": slide_index}


def _command(
    drafts: list[dict[str, object]],
    retry: _RetryDouble | None = None,
) -> FailClosedReviewCommand:
    return FailClosedReviewCommand(
        project_id=_PROJECT_ID,
        slide_drafts=drafts,
        retry_draft=retry,
    )


def _pt_payload(updates: dict[str, object], slide_index: int) -> dict[str, object]:
    localized = updates["localized_slides"]
    assert isinstance(localized, list)
    for slide in localized:
        if slide.get("slide_index") == slide_index:
            payload = slide.get("presentation_pt")
            assert isinstance(payload, dict)
            return payload
    raise AssertionError(f"slide {slide_index} not found in localized slides")


def _report(updates: dict[str, object]) -> dict[str, object]:
    report = updates["presentation_validation"]
    assert isinstance(report, dict)
    return report


@pytest.mark.unit
class TestIncidentScaffoldRepair:
    """Scenario: Deterministic repair rescues a scaffold-contaminated slide."""

    def test_incident_fixture_shape_matches_prod_payload(self) -> None:
        """The fixture reproduces the incident scaffold (~1147 chars, all labels)."""
        assert len(INCIDENT_SCAFFOLD_DRAFT) >= 1000
        for label in _SCAFFOLD_LABELS:
            assert label in INCIDENT_SCAFFOLD_DRAFT

    async def test_write_path_repairs_the_incident_payload(self) -> None:
        """Rule-fires: the write path repairs the scaffold instead of storing it."""
        updates = await build_fail_closed_review_updates(
            _command([_content_draft(INCIDENT_SCAFFOLD_DRAFT)])
        )

        payload = _pt_payload(updates, 4)
        body = str(payload["body"])
        assert body, "the repaired body must carry visible copy"
        for label in _SCAFFOLD_LABELS:
            assert label not in body
        assert len(body) <= _CONTENT_BODY_BUDGET
        assert _report(updates)["blocking"] is False
        assert updates[_GATE_KEY] == {}

    async def test_repaired_payload_carries_canonical_keys(self) -> None:
        """The payload has the canonical key set after the deterministic repair."""
        updates = await build_fail_closed_review_updates(
            _command([_content_draft(INCIDENT_SCAFFOLD_DRAFT)])
        )

        payload = _pt_payload(updates, 4)
        for key in ("slide_type", "heading", "body", "content_kind", "features"):
            assert key in payload

    async def test_parse_failure_logs_deterministic_repair_outcome(self) -> None:
        """Scenario: parse failures emit carousel_slide_parse_failed events."""
        with capture_logs() as logs:
            await build_fail_closed_review_updates(
                _command([_content_draft(INCIDENT_SCAFFOLD_DRAFT)])
            )

        events = [log for log in logs if log["event"] == LOG_EVENT_SLIDE_PARSE_FAILED]
        assert events, "expected a carousel_slide_parse_failed log event"
        pt_event = next(log for log in events if log["locale"] == LANGUAGE_PT)
        assert pt_event["project_id"] == _PROJECT_ID
        assert pt_event["slide_index"] == 4
        assert pt_event["repair_outcome"] == REPAIR_OUTCOME_DETERMINISTIC


@pytest.mark.unit
class TestRetryRescue:
    """Scenario: The single LLM retry rescues an unrepaired slide."""

    async def test_retry_success_stores_the_retried_draft(self) -> None:
        retry = _RetryDouble({
            "slide_type": "content",
            "title": "Fluxo editorial sob controle",
            "draft_text": "Copy limpa e directa gerada na segunda tentativa.",
        })

        updates = await build_fail_closed_review_updates(
            _command([_content_draft(UNRECOVERABLE_SCAFFOLD_DRAFT)], retry)
        )

        assert retry.calls == [4], "the LLM retry must run exactly once"
        payload = _pt_payload(updates, 4)
        assert payload["body"] == "Copy limpa e directa gerada na segunda tentativa."
        for key in ("slide_type", "heading", "body", "content_kind", "features"):
            assert key in payload
        assert _report(updates)["blocking"] is False
        assert updates[_GATE_KEY] == {}

    async def test_retry_success_replaces_the_slide_draft(self) -> None:
        retry = _RetryDouble({
            "slide_type": "content",
            "title": "Fluxo editorial sob controle",
            "draft_text": "Copy limpa e directa gerada na segunda tentativa.",
        })

        updates = await build_fail_closed_review_updates(
            _command([_content_draft(UNRECOVERABLE_SCAFFOLD_DRAFT)], retry)
        )

        drafts = updates["slide_drafts"]
        assert isinstance(drafts, list)
        assert drafts[0]["draft_text"] == (
            "Copy limpa e directa gerada na segunda tentativa."
        )

    async def test_retry_rescue_logs_llm_retry_outcome(self) -> None:
        retry = _RetryDouble({
            "slide_type": "content",
            "title": "Fluxo editorial sob controle",
            "draft_text": "Copy limpa e directa gerada na segunda tentativa.",
        })

        with capture_logs() as logs:
            await build_fail_closed_review_updates(
                _command([_content_draft(UNRECOVERABLE_SCAFFOLD_DRAFT)], retry)
            )

        outcomes = {
            log["repair_outcome"]
            for log in logs
            if log["event"] == LOG_EVENT_SLIDE_PARSE_FAILED
        }
        assert REPAIR_OUTCOME_RETRY in outcomes


@pytest.mark.unit
class TestUnrepairableBlocksAtContentReview:
    """Scenario: Unrepairable slide surfaces at the content review step."""

    async def test_blocking_report_attached_after_failed_retry(self) -> None:
        retry = _RetryDouble({
            "slide_type": "content",
            "title": "Fluxo editorial sob controle",
            "draft_text": UNRECOVERABLE_SCAFFOLD_DRAFT,
        })

        updates = await build_fail_closed_review_updates(
            _command([_content_draft(UNRECOVERABLE_SCAFFOLD_DRAFT)], retry)
        )

        assert retry.calls == [4], "only one retry may be consumed"
        gate = updates[_GATE_KEY]
        assert isinstance(gate, dict)
        assert gate["blocking"] is True
        codes = {
            (violation["code"], violation["slide_index"])
            for violation in gate["violations"]
        }
        assert (VIOLATION_SLIDE_PARSE_FAILED, 4) in codes

    async def test_scaffold_never_persists_even_when_unrepairable(self) -> None:
        """Fail closed: the raw draft never becomes visible body copy."""
        updates = await build_fail_closed_review_updates(
            _command([_content_draft(UNRECOVERABLE_SCAFFOLD_DRAFT)])
        )

        payload = _pt_payload(updates, 4)
        assert payload["body"] == ""
        gate = updates[_GATE_KEY]
        assert isinstance(gate, dict)
        assert gate["blocking"] is True

    async def test_unrecovered_parse_failure_blocks_approval(self) -> None:
        """The stored markers keep approval blocked on later read paths."""
        updates = await build_fail_closed_review_updates(
            _command([_content_draft(UNRECOVERABLE_SCAFFOLD_DRAFT)])
        )

        assert has_blocking_presentation_validation(updates) is True

    async def test_en_translation_survives_a_pt_only_parse_failure(self) -> None:
        """Edge case: an EN translation is kept when only PT extraction fails."""
        command = FailClosedReviewCommand(
            project_id=_PROJECT_ID,
            slide_drafts=[_content_draft(UNRECOVERABLE_SCAFFOLD_DRAFT)],
            translations_en={
                4: {"heading": "Editorial flow", "body": "Short clean body."}
            },
        )

        updates = await build_fail_closed_review_updates(command)

        localized = updates["localized_slides"]
        assert isinstance(localized, list)
        en_payload = localized[0]["presentation_en"]
        assert isinstance(en_payload, dict)
        assert en_payload["body"] == "Short clean body."
        gate = updates[_GATE_KEY]
        assert isinstance(gate, dict)
        locales = {
            violation["locale"]
            for violation in gate["violations"]
            if violation["code"] == VIOLATION_SLIDE_PARSE_FAILED
        }
        assert locales == {LANGUAGE_PT}

    async def test_unrepairable_logs_unrepaired_outcome(self) -> None:
        with capture_logs() as logs:
            await build_fail_closed_review_updates(
                _command([_content_draft(UNRECOVERABLE_SCAFFOLD_DRAFT)])
            )

        outcomes = {
            log["repair_outcome"]
            for log in logs
            if log["event"] == LOG_EVENT_SLIDE_PARSE_FAILED
        }
        assert outcomes == {REPAIR_OUTCOME_UNREPAIRED}

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_content_interrupt_payload_carries_gate_report(
        self, mock_interrupt: MagicMock
    ) -> None:
        """The interrupt payload mirrors the blocking gate report (AE-0309)."""
        mock_interrupt.return_value = {"action": "approve"}
        gate_report = {"blocking": True, "violations": []}
        state = get_initial_carousel_state(_PROJECT_ID, {"topic": "AI"})
        state.update({
            "slide_drafts": [{"slide_index": 4}],
            STATE_FIELD_CONTENT_GATE_VALIDATION: gate_report,
        })

        content_phase(state)

        payload = mock_interrupt.call_args[0][0]
        assert payload[STATE_FIELD_CONTENT_GATE_VALIDATION] == gate_report
        assert payload["slide_drafts"] == [{"slide_index": 4}]

    def test_engine_merges_gate_report_from_pending_interrupts(self) -> None:
        """The engine surfaces the gate payload key when state lacks it."""
        assert STATE_FIELD_CONTENT_GATE_VALIDATION in _REVIEW_INTERRUPT_KEYS


@pytest.mark.unit
class TestCleanDraftsUnaffected:
    """Scenario: Clean drafts are unaffected."""

    async def test_clean_drafts_match_todays_artifact_and_skip_retry(self) -> None:
        retry = _RetryDouble(None)
        drafts = _clean_drafts()

        updates = await build_fail_closed_review_updates(_command(drafts, retry))
        baseline = await build_presentation_review_updates_async(_clean_drafts())

        assert retry.calls == [], "clean drafts must not consume the retry"
        assert updates[_GATE_KEY] == {}
        assert updates["localized_slides"] == baseline["localized_slides"]
        report = _report(updates)
        assert report["blocking"] is False
        assert report["violations"] == []

    async def test_clean_drafts_emit_no_parse_failed_events(self) -> None:
        with capture_logs() as logs:
            await build_fail_closed_review_updates(_command(_clean_drafts()))

        events = [log for log in logs if log["event"] == LOG_EVENT_SLIDE_PARSE_FAILED]
        assert events == []


@pytest.mark.unit
class TestBlockingFlagIsTheOnlyTrigger:
    """Scenario: A non-blocking report never consumes the retry or the interrupt.

    AE-0312 forward-compatibility (cold-critic r6): a report that carries
    violations with blocking=False (future warning-severity rules) must not
    consume the LLM retry and must not attach the blocking gate report.
    """

    async def test_non_blocking_violations_skip_retry_and_gate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        warning_updates: dict[str, object] = {
            "localized_slides": [{"slide_index": 4, "slide_type": "content"}],
            "presentation_validation": {
                "validation_status": "invalid",
                "validated_at": "2026-07-10T00:00:00+00:00",
                "blocking": False,
                "violations": [
                    {
                        "code": "heading_not_sentence_case_pt",
                        "message": "warning-severity rule",
                        "slide_index": 4,
                    }
                ],
            },
            "presentation_policy_version": "hero_lower_third_v1",
        }

        async def _fake_result(
            slide_drafts: list[dict[str, object]],
            *,
            translations_en: object = None,
            policy_version: object = None,
        ) -> PresentationReviewBuildResult:
            return PresentationReviewBuildResult(updates=dict(warning_updates))

        monkeypatch.setattr(
            content_fail_closed,
            "build_presentation_review_result_async",
            _fake_result,
        )
        retry = _RetryDouble(None)

        updates = await build_fail_closed_review_updates(
            _command([_content_draft("Texto limpo.")], retry)
        )

        assert retry.calls == [], "blocking=False must never consume the retry"
        assert updates[_GATE_KEY] == {}
        assert _report(updates)["violations"], "violations stay visible in the report"


@pytest.mark.unit
class TestCanonicalKeys:
    """Scenario: A locale payload missing canonical keys counts as a parse failure."""

    def test_builder_flags_missing_canonical_keys(self) -> None:
        drafts = [
            {
                "slide_index": 4,
                "slide_type": "content",
                "presentation_pt": {
                    "slide_type": "content",
                    "heading": "Insight",
                    "body": "Corpo curto.",
                },
                "presentation_en": {
                    "slide_type": "content",
                    "heading": "Insight",
                    "body": "Short body.",
                },
            }
        ]

        _, failures = build_localized_slides_with_failures(drafts)

        reasons = {(failure.locale, failure.reason) for failure in failures}
        assert (LANGUAGE_PT, PARSE_FAILURE_MISSING_CANONICAL_KEYS) in reasons

    async def test_missing_keys_are_normalized_on_the_write_path(self) -> None:
        updates = await build_fail_closed_review_updates(
            _command([
                {
                    "slide_index": 4,
                    "slide_type": "content",
                    "presentation_pt": {
                        "slide_type": "content",
                        "heading": "Insight",
                        "body": "Corpo curto.",
                    },
                    "presentation_en": {
                        "slide_type": "content",
                        "heading": "Insight number four",
                        "body": "Short body.",
                    },
                }
            ])
        )

        payload = _pt_payload(updates, 4)
        assert payload["content_kind"] == "features"
        assert payload["features"] == []
        assert _report(updates)["blocking"] is False


@pytest.mark.unit
class TestBuilderNeverFallsBackToRawDraft:
    """AE-0309: _build_locale_payload never stores the raw draft as body."""

    def test_scaffold_draft_yields_typed_failure_and_empty_body(self) -> None:
        slides, failures = build_localized_slides_with_failures([
            _content_draft(INCIDENT_SCAFFOLD_DRAFT)
        ])

        payload = slides[0]["presentation_pt"]
        assert isinstance(payload, dict)
        assert payload["body"] == ""
        reasons = {(failure.locale, failure.reason) for failure in failures}
        assert (LANGUAGE_PT, PARSE_FAILURE_RAW_DRAFT_FALLBACK) in reasons

    def test_clean_plain_draft_text_still_becomes_body(self) -> None:
        """Legacy drafts with plain copy in draft_text keep working."""
        slides, failures = build_localized_slides_with_failures([
            {
                "slide_index": 1,
                "slide_type": "intro",
                "title": "Gancho",
                "draft_text": "Subtitulo simples.",
            }
        ])

        payload = slides[0]["presentation_pt"]
        assert isinstance(payload, dict)
        assert payload["body"] == "Subtitulo simples."
        assert failures == []
