"""Unit tests for the deterministic length/heading copy repair (AE-0286).

Scenarios: see tests/features/glm_content_budget_trim.feature
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.presentation_copy_repair import (
    _strip_heading_from_body,
    _trim_body_to_budget,
    repair_body_length_and_heading,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_validation import (
    ValidatePayloadCommand,
    validate_slide_payload,
)
from rag_backend.domain.constants.carousel import LANGUAGE_PT
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_BODY_TOO_LONG,
    VIOLATION_HEADING_REPEATED_IN_BODY,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
)

_THREE_SENTENCES = (
    "O git worktree cria multiplos diretorios ligados ao mesmo repositorio. "
    "Alterne entre branches em pastas separadas sem stash ou clone. "
    "Isso acelera o fluxo diario de qualquer time que precise de contexto paralelo "
    "constante, seguro e totalmente isolado entre as varias tarefas em andamento."
)


@pytest.fixture
def policy():
    return load_presentation_policy(PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1)


class TestTrimBodyToBudget:
    def test_keeps_whole_sentences_under_budget(self) -> None:
        trimmed = _trim_body_to_budget(_THREE_SENTENCES, 220)
        assert len(trimmed) <= 220
        # A whole-sentence trim ends on terminal punctuation (no mid-word cut).
        assert trimmed.endswith((".", "!", "?"))
        assert "  " not in trimmed

    def test_never_exceeds_budget_even_for_one_giant_sentence(self) -> None:
        giant = "palavra " * 80  # one 600+ char run with no sentence break
        trimmed = _trim_body_to_budget(giant.strip(), 90)
        assert len(trimmed) <= 90
        assert trimmed.endswith("…")
        # word-boundary cut: no partial trailing word before the ellipsis
        assert not trimmed[:-1].endswith("palavr")

    def test_short_body_is_returned_unchanged(self) -> None:
        assert _trim_body_to_budget("Curto e direto.", 220) == "Curto e direto."

    def test_balances_dangling_markup_after_a_cut(self) -> None:
        body = (
            "Use <strong>git worktree</strong> para isolar contextos. "
            "Cada pasta liga ao mesmo repo e evita <strong>stash repetido e "
            "troca de branch que quebra o foco do desenvolvedor distraido</strong>."
        )
        trimmed = _trim_body_to_budget(body, 70)
        assert len(trimmed) <= 70
        # no dangling open tag
        assert trimmed.count("<strong>") == trimmed.count("</strong>")


class TestStripHeadingFromBody:
    def test_removes_repeated_heading_and_tidies(self) -> None:
        out = _strip_heading_from_body(
            "Worktree vs clone: o worktree nao duplica o historico do repo.",
            "Worktree vs clone",
        )
        assert "worktree vs clone" not in out.casefold()
        assert out.startswith("o worktree")

    def test_handles_markdown_in_heading(self) -> None:
        out = _strip_heading_from_body(
            "git worktree na pratica cria varios diretorios.",
            "**git worktree na pratica**",
        )
        assert "git worktree na pratica" not in out.casefold()


class TestDeterministicRepairClearsValidator:
    """The strongest test: repaired payload passes the real validator."""

    def test_over_budget_and_heading_repeat_are_both_cleared(self, policy) -> None:
        # Scenario: GLM over-writes content; the trim must clear validation.
        heading = "O que e git worktree na pratica"
        payload = {
            "slide_type": "content",
            "heading": heading,
            "body": f"{heading}. {_THREE_SENTENCES}",
        }
        before = validate_slide_payload(
            ValidatePayloadCommand(
                payload, locale=LANGUAGE_PT, policy=policy, slide_index=3
            )
        )
        before_codes = {v.code for v in before}
        assert VIOLATION_BODY_TOO_LONG in before_codes
        assert VIOLATION_HEADING_REPEATED_IN_BODY in before_codes

        repaired = repair_body_length_and_heading(payload, tuple(before), policy)
        after = validate_slide_payload(
            ValidatePayloadCommand(
                repaired, locale=LANGUAGE_PT, policy=policy, slide_index=3
            )
        )
        after_codes = {v.code for v in after}
        assert VIOLATION_BODY_TOO_LONG not in after_codes
        assert VIOLATION_HEADING_REPEATED_IN_BODY not in after_codes
        # And the repaired body is still meaningful (non-empty, real words).
        assert isinstance(repaired["body"], str)
        assert len(repaired["body"].split()) >= 4

    def test_returns_payload_unchanged_without_length_violations(self, policy) -> None:
        # No body/heading violation in the set -> body untouched.
        payload = {"slide_type": "content", "heading": "H", "body": "Curto."}
        repaired = repair_body_length_and_heading(payload, (), policy)
        assert repaired["body"] == "Curto."
