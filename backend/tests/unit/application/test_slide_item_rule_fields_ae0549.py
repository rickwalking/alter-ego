"""Checklist rule violations point at the item (field paths) and item bodies truncate.

Feature: backend/tests/features/slide_item_rule_fields_ae0549.feature
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.presentation_content_rules import (
    ContentRuleCommand,
    content_rule_violations,
)
from rag_backend.application.services.carousel.presentation_copy_rules import (
    copy_hygiene_violations,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.domain.constants.carousel import LANGUAGE_PT
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_CLOSING_ACTIONS_MISSING,
    VIOLATION_COPY_TRUNCATED,
    VIOLATION_SUMMARY_POINTS_MISSING,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4,
)

_COMPLETE = {"title": "Ponto", "body": "Um corpo completo."}
_BODY = "Um corpo de slide com frases completas e um dado concreto."


def _command(payload: dict[str, object]) -> ContentRuleCommand:
    return ContentRuleCommand(
        payload=payload,
        locale=LANGUAGE_PT,
        policy=load_presentation_policy(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4
        ),
        slide_index=2,
    )


def _fields(payload: dict[str, object], code: str) -> list[str]:
    return [
        str(violation.field)
        for violation in content_rule_violations(_command(payload))
        if violation.code == code
    ]


def _summary(points: list[dict[str, str]]) -> dict[str, object]:
    return {
        "slide_type": "summary",
        "heading": "Resumo",
        "body": _BODY,
        "summary_points": points,
    }


def _truncated(payload: dict[str, object]) -> list[str]:
    return [
        str(violation.field)
        for violation in copy_hygiene_violations(_command(payload))
        if violation.code == VIOLATION_COPY_TRUNCATED
    ]


@pytest.mark.unit
class TestListViolationField:
    def test_first_incomplete_point_is_named(self) -> None:
        """Scenario: A missing summary point is reported on the first incomplete item"""
        points = [_COMPLETE, {"title": "Sem corpo", "body": " "}, _COMPLETE]
        assert _fields(_summary(points), VIOLATION_SUMMARY_POINTS_MISSING) == [
            "summary_points[1].body"
        ]

    def test_too_few_complete_points_name_the_list(self) -> None:
        """Scenario: Too few complete summary points are reported on the list"""
        assert _fields(
            _summary([_COMPLETE, _COMPLETE]), VIOLATION_SUMMARY_POINTS_MISSING
        ) == ["summary_points"]
        assert _fields(_summary([]), VIOLATION_SUMMARY_POINTS_MISSING) == [
            "summary_points"
        ]

    def test_closing_names_the_first_incomplete_action(self) -> None:
        """Scenario: A closing slide with too few actions points at the first incomplete action"""
        payload = {
            "slide_type": "closing",
            "heading": "Próximos passos",
            "body": _BODY,
            "actions": [{"title": "", "body": "Faça isto."}, _COMPLETE],
        }
        assert _fields(payload, VIOLATION_CLOSING_ACTIONS_MISSING) == [
            "actions[0].title"
        ]
        features_only = {**payload, "actions": [], "features": [_COMPLETE]}
        assert _fields(features_only, VIOLATION_CLOSING_ACTIONS_MISSING) == ["features"]


@pytest.mark.unit
class TestItemBodyTruncation:
    @pytest.mark.parametrize(
        "body",
        [
            "Musk disse que o Grok Bot reserva mesa por telefone. Não é",
            "O agente conduz a ligação e",
            "Começa simples e vai crescendo...",
            "Três passos:",
            "Eu vejo diferente: funcionário tem. Ele resolve sozinho o pedido",
            "O agente conduz a",
            "O ganho real não é",
            "The agent does not",
            "It is not chat, it is",
            "This",
            "Calls restaurants and books a table by phone. It works for the",
        ],
    )
    def test_cut_off_item_body_is_truncated(self, body: str) -> None:
        """Scenario: A checklist item body cut off mid-sentence is truncated copy"""
        points = [_COMPLETE, {"title": "Corte", "body": body}, _COMPLETE]
        assert _truncated(_summary(points)) == ["summary_points[1].body"]

    @pytest.mark.parametrize(
        "body",
        [
            "Revisão automática de PRs",
            "Dados no seu ambiente",
            "Feito.",
            "Suporte a Node.js",
            "Grok 3.5 reserva mesa",
            "GPT-4.1 no fluxo",
            "Custo cai 2.5x",
            "Use e.g. Claude",
            "Funciona? Sim",
            "Plano A",
            "Vale o teste. Sem pressa",
            "Ship it. Then measure",
        ],
    )
    def test_short_fragment_is_not_truncated(self, body: str) -> None:
        """Scenario: A short checklist fragment without a full stop is not truncated"""
        points = [_COMPLETE, {"title": "Fragmento", "body": body}, _COMPLETE]
        assert _truncated(_summary(points)) == []

    def test_item_message_fits_the_item(self) -> None:
        """Scenario: A checklist item body cut off mid-sentence is truncated copy"""
        points = [
            _COMPLETE,
            {"title": "Corte", "body": "The agent does not"},
            _COMPLETE,
        ]
        (violation,) = [
            v
            for v in copy_hygiene_violations(_command(_summary(points)))
            if v.code == VIOLATION_COPY_TRUNCATED
        ]
        assert violation.message.startswith("Item text stops mid-sentence")
