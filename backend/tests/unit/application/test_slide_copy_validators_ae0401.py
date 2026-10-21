"""Copy-hygiene validators and their deterministic repair.

Gherkin: tests/features/slide_copy_validators_ae0401.feature
Each rule has a rule-fires test on a seeded violation; the clean
prod deck proves the rules stay tolerant of legitimate copy.
"""

from __future__ import annotations

import copy
import json

import pytest

from rag_backend.application.services.carousel.copy_hygiene_repair import (
    repair_colon_case_en,
    repair_copy_hygiene,
    repair_doubled_words,
    repair_emphasis,
    repair_encoding,
    repair_markup,
)
from rag_backend.application.services.carousel.copy_hygiene_text import (
    placeholder_detail,
    truncation_detail,
)
from rag_backend.application.services.carousel.owner_autofix_fill import (
    split_key_point,
)
from rag_backend.application.services.carousel.owner_autofix_plan import (
    AutofixContext,
    plan_autofix,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.application.services.carousel.presentation_review_repair import (
    repair_localized_slides_sync,
)
from rag_backend.application.services.carousel.presentation_validation import (
    ValidatePayloadCommand,
    validate_slide_payload,
)
from tests.unit.application.copy_hygiene_fixtures_ae0401 import (
    POV,
    SAVE_BODY_PT,
    blob_body,
    broken_deck,
    en,
    prod_deck,
    pt,
)

V3 = "hero_lower_third_v3"
V4 = "hero_lower_third_v4"
HOOK_TEXT = "Meu time de agentes não é chatbot. É autonomia aprovada."
_HYGIENE_CODES = frozenset({
    "structured_payload_in_copy",
    "markup_leak",
    "emphasis_unbalanced",
    "assistant_chatter",
    "placeholder_text",
    "encoding_garbled",
    "copy_truncated",
    "body_too_short",
    "wrong_language",
    "repeated_text",
    "structured_item_split",
})


def _codes(deck: list[dict[str, object]], version: str = POV) -> set[tuple[int, str]]:
    report = validate_localized_slides(deck, policy_version=version)
    return {(v.slide_index or 0, v.code) for v in report.violations if v.is_blocker}


def _payload_codes(
    payload: dict[str, object], locale: str, version: str = POV
) -> set[str]:
    violations = validate_slide_payload(
        ValidatePayloadCommand(
            payload, locale=locale, policy=load_presentation_policy(version)
        )
    )
    return {violation.code for violation in violations}


_BASE = {
    "pt": ("O agente não é o problema", "Eu vejo o mesmo erro em todo PR do meu time."),
    "en": (
        "The agent is not the problem",
        "I see the same mistake in every PR I review.",
    ),
}


def _content(field: str, text: str, locale: str = "pt") -> dict[str, object]:
    heading, body = _BASE[locale]
    payload: dict[str, object] = {
        "slide_type": "content",
        "heading": heading,
        "body": body,
    }
    payload[field] = text
    return payload


@pytest.mark.unit
class TestProdDeck:
    """Scenarios: the approved deck passes; the shipped deck is blocked."""

    @pytest.mark.parametrize("version", [POV, V4])
    def test_approved_deck_passes_every_rule(self, version: str) -> None:
        """Scenario: The approved 9-slide prod deck passes every rule."""
        report = validate_localized_slides(prod_deck(), policy_version=version)
        hygiene = [v for v in report.violations if v.code in _HYGIENE_CODES]
        assert hygiene == []
        if version == POV:
            assert report.violations == []

    def test_shipped_deck_is_blocked_on_slides_3_and_8(self) -> None:
        """Scenario: The deck prod shipped is blocked on slides 3 and 8."""
        codes = _codes(broken_deck())
        assert (3, "structured_payload_in_copy") in codes
        assert (8, "markup_leak") in codes
        assert {index for index, _ in codes} == {3, 8}

    def test_generation_repair_restores_the_deck(self) -> None:
        """Scenario: The deterministic repair restores the approved deck."""
        assert repair_localized_slides_sync(broken_deck(), policy_version=POV) == (
            prod_deck()
        )

    def test_gate_repair_restores_the_deck(self) -> None:
        """Scenario: The deterministic repair restores the approved deck (gate)."""
        context = AutofixContext(policy=load_presentation_policy(POV))
        plan = plan_autofix(broken_deck(), context)
        assert plan.records == prod_deck()
        assert plan.retranslate == ()


_FIRES: list[tuple[str, str, str, str]] = [
    (
        "structured_payload_in_copy",
        "pt",
        "body",
        '{"pt": {"heading": "Oi", "body": "Tudo."}}',
    ),
    ("structured_payload_in_copy", "pt", "body", blob_body()),
    (
        "structured_payload_in_copy",
        "en",
        "body",
        'The "body": "copy" key leaked into the slide text.',
    ),
    (
        "structured_payload_in_copy",
        "en",
        "body",
        '[{"title": "x"}] was left in the copy here.',
    ),
    ("markup_leak", "pt", "body", "## Checklist para salvar"),
    (
        "markup_leak",
        "en",
        "body",
        "Use the <em>new</em> agent mode for every review you run.",
    ),
    (
        "markup_leak",
        "pt",
        "body",
        "- Liste os arquivos que o agente pode tocar no ticket.",
    ),
    ("markup_leak", "pt", "body", "| Antes | Depois |\n| --- | --- |"),
    (
        "markup_leak",
        "pt",
        "body",
        "Rode o comando `npm test` antes de abrir o PR no time.",
    ),
    (
        "markup_leak",
        "en",
        "body",
        "First line\\nsecond line of the copy that the model escaped.",
    ),
    (
        "emphasis_unbalanced",
        "pt",
        "body",
        "Eu vejo **escopo aberto demais em quase todo PR do time.",
    ),
    (
        "emphasis_unbalanced",
        "en",
        "body",
        "I see **** in the copy and nobody notices it at review.",
    ),
    (
        "emphasis_unbalanced",
        "en",
        "body",
        "I see <strong></strong> in the copy and nobody notices it.",
    ),
    (
        "assistant_chatter",
        "en",
        "body",
        "Here is the revised slide copy you asked me to write today.",
    ),
    (
        "assistant_chatter",
        "pt",
        "body",
        "Claro! Aqui está o texto do slide revisado para o carrossel.",
    ),
    (
        "assistant_chatter",
        "en",
        "body",
        "Sure, the agent rewrites modules when nobody limits the scope.",
    ),
    (
        "assistant_chatter",
        "pt",
        "body",
        "Eu reviso PRs toda semana no meu time (Nota: 30 palavras).",
    ),
    (
        "placeholder_text",
        "pt",
        "body",
        "Eu uso [inserir ferramenta] em todo ticket do meu time agora.",
    ),
    ("placeholder_text", "en", "heading", "The {topic} that changes everything"),
    (
        "placeholder_text",
        "pt",
        "body",
        "TODO escrever o corpo deste slide antes de publicar hoje.",
    ),
    (
        "placeholder_text",
        "en",
        "body",
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit now.",
    ),
    ("placeholder_text", "pt", "heading", "…"),
    (
        "encoding_garbled",
        "pt",
        "body",
        "Eu reviso PRs toda semana e o erro Ã© sempre o mesmo aqui.",
    ),
    (
        "encoding_garbled",
        "en",
        "body",
        "I review PRs every week and the mistake is not new \ufffd at all.",
    ),
    (
        "encoding_garbled",
        "en",
        "body",
        "I review PRs every week and\x07 the mistake is always the same.",
    ),
    (
        "copy_truncated",
        "pt",
        "body",
        "Eu reviso PRs de agentes toda semana e o erro mais comum é",
    ),
    (
        "copy_truncated",
        "en",
        "body",
        "I review agent PRs every week and the mistake I see is...",
    ),
    (
        "copy_truncated",
        "pt",
        "body",
        "Eu reviso PRs de agentes toda semana e vejo sempre o mesmo,",
    ),
    (
        "copy_truncated",
        "en",
        "body",
        "I review agent PRs every week and it always ends the same and.",
    ),
    ("body_too_short", "pt", "body", "Escopo aberto custa caro."),
    (
        "wrong_language",
        "pt",
        "body",
        "The agent is not the problem and the vague request is.",
    ),
    (
        "wrong_language",
        "en",
        "body",
        "O agente não é o problema, o pedido vago é que é o erro.",
    ),
    (
        "repeated_text",
        "pt",
        "body",
        "O agente erra muito. O agente erra muito. E ninguém vê.",
    ),
    (
        "repeated_text",
        "en",
        "body",
        "The the agent rewrites whole modules to fix a small bug.",
    ),
]


@pytest.mark.unit
class TestRulesFire:
    """Scenario Outline: Each rule fires on its seeded violation."""

    @pytest.mark.parametrize(("code", "locale", "field", "text"), _FIRES)
    def test_rule_fires(self, code: str, locale: str, field: str, text: str) -> None:
        assert code in _payload_codes(_content(field, text, locale), locale)

    @pytest.mark.parametrize(("code", "locale", "field", "text"), _FIRES)
    def test_rule_is_a_blocker(
        self, code: str, locale: str, field: str, text: str
    ) -> None:
        violations = validate_slide_payload(
            ValidatePayloadCommand(
                _content(field, text, locale),
                locale=locale,
                policy=load_presentation_policy(POV),
                slide_index=4,
            )
        )
        found = [violation for violation in violations if violation.code == code]
        assert found and all(violation.is_blocker for violation in found)
        assert all(violation.slide_index == 4 for violation in found)

    def test_item_title_cut_on_a_connector(self) -> None:
        """Scenario: A summary point cut mid-phrase is blocked."""
        deck = prod_deck()
        points = pt(deck, 8)["summary_points"]
        assert isinstance(points, list)
        points[0] = {
            "icon_name": "target",
            "title": "Comece com dois ou",
            "body": "Três agentes, não dez.",
        }
        report = validate_localized_slides(deck, policy_version=POV)
        found = [v for v in report.violations if v.code == "structured_item_split"]
        assert [(v.slide_index, v.field) for v in found] == [
            (8, "summary_points[0].title")
        ]

    def test_hook_body_repeating_its_heading(self) -> None:
        """Scenario: A hook whose body repeats its heading is blocked."""
        deck = prod_deck()
        pt(deck, 1)["heading"] = HOOK_TEXT
        pt(deck, 1)["body"] = HOOK_TEXT
        assert (1, "heading_repeated_in_body") in _codes(deck)

    def test_feature_body_in_items_is_checked(self) -> None:
        payload = _content(
            "body", "Eu listo os arquivos que o agente pode tocar no ticket."
        )
        payload["features"] = [
            {"icon_name": "brain", "title": "Escopo", "body": "TODO."}
        ]
        assert "placeholder_text" in _payload_codes(payload, "pt")


_CLEAN: list[tuple[str, str]] = [
    ("pt", "Eu vejo **escopo** aberto demais em quase todo PR que eu reviso."),
    ("en", "I see <strong>scope</strong> left too open in almost every PR I review."),
    ("pt", "No Claude Code eu peço 3 testes antes da mudança, nunca depois."),
    ("en", "In 2026 I ask the agent for tests first: that is the whole trick."),
    ("pt", "O dia todo eu vejo o mesmo erro, e o time todo também vê."),
    ("en", "What it had had in mind was the same thing that that team wanted."),
    ("pt", "Eu reviso o que o agente fez e ele erra menos a cada semana."),
]


@pytest.mark.unit
class TestTolerance:
    """Scenario: Legit emphasis is never a leak (and other legit copy)."""

    @pytest.mark.parametrize(("locale", "text"), _CLEAN)
    def test_clean_copy_passes(self, locale: str, text: str) -> None:
        codes = _payload_codes(_content("body", text, locale), locale)
        assert not codes & _HYGIENE_CODES

    def test_older_contracts_keep_their_semantics(self) -> None:
        """Scenario: Older contracts keep their semantics."""
        payload = _content("body", blob_body())
        assert not _payload_codes(payload, "pt", V3) & _HYGIENE_CODES

    def test_intro_and_cta_are_exempt_from_truncation(self) -> None:
        payload = {
            "slide_type": "intro",
            "heading": "Escopo",
            "body": "E isso custa caro",
        }
        assert "copy_truncated" not in _payload_codes(payload, "pt")

    def test_content_with_features_is_not_too_short(self) -> None:
        payload = _content("body", "Três sinais de alerta.")
        payload["features"] = [
            {"icon_name": "brain", "title": f"Sinal {n}", "body": "Ele muda tudo."}
            for n in (1, 2, 3)
        ]
        assert "body_too_short" not in _payload_codes(payload, "pt")

    @pytest.mark.parametrize("text", ["", "Ok."])
    def test_detectors_on_edge_text(self, text: str) -> None:
        assert truncation_detail(text) == ""
        assert placeholder_detail(text) == ""


@pytest.mark.unit
class TestDeterministicRepair:
    """The safe repairs, one by one."""

    def test_markup_keeps_strong_and_bold(self) -> None:
        text = "Eu vejo **escopo** e <strong>scope</strong>."
        assert repair_markup(text) == text

    def test_markup_drops_other_tags_headings_and_escapes(self) -> None:
        text = "## Título\nUse <em>isto</em>, <b>aquilo</b> e `npm test`.\\n Fim."
        assert repair_markup(text) == (
            "Título\nUse isto, <strong>aquilo</strong> e npm test. Fim."
        )

    def test_emphasis_repair(self) -> None:
        assert repair_emphasis("Eu vejo **escopo aberto.") == "Eu vejo escopo aberto."
        assert repair_emphasis("Eu vejo **** aqui.") == "Eu vejo aqui."
        assert repair_emphasis("Ok **sim**.") == "Ok **sim**."

    def test_encoding_repair(self) -> None:
        assert (
            repair_encoding("O erro Ã© sempre o mesmo.") == "O erro é sempre o mesmo."
        )
        assert repair_encoding("Sem\x07 controle.") == "Sem controle."
        assert repair_encoding("Ã™ \ufffd") == "Ã™ \ufffd"

    def test_doubled_words(self) -> None:
        assert repair_doubled_words("O o agente erra.") == "O agente erra."
        assert repair_doubled_words("It had had a plan.") == "It had had a plan."

    def test_colon_case_en(self) -> None:
        """Scenario: The EN casing repair never capitalizes after a colon."""
        assert repair_colon_case_en("I see the mistake: It responds.") == (
            "I see the mistake: it responds."
        )
        assert repair_colon_case_en("How to decide: Pass or return") == (
            "How to decide: pass or return"
        )
        assert repair_colon_case_en("Note: I was wrong.") == "Note: I was wrong."
        assert repair_colon_case_en("The tool: Claude Code.", ("Claude",)) == (
            "The tool: Claude Code."
        )
        assert repair_colon_case_en("Rule: API first.") == "Rule: API first."
        assert repair_colon_case_en("Use: GitHub now.") == "Use: GitHub now."

    def test_colon_case_runs_on_en_only(self) -> None:
        policy = load_presentation_policy(POV)
        payload = _content(
            "body", "Eu vejo o erro: Ele responde rápido demais e ninguém vê."
        )
        assert repair_copy_hygiene(payload, "pt", policy) == payload
        english = _content(
            "body", "I see the mistake: It responds too fast for anyone.", "en"
        )
        fixed = repair_copy_hygiene(english, "en", policy)
        assert fixed["body"] == "I see the mistake: it responds too fast for anyone."

    def test_blob_summary_points_are_kept_whole(self) -> None:
        """Scenario: A fenced blob's summary points are kept whole."""
        deck = prod_deck()
        points = [
            {"title": "Comece com dois ou três agentes", "body": "Não dez."},
            {"title": "Fora do escopo", "body": "Liste o que ele não deve tocar."},
            {"title": "Teste do pedido", "body": "Peça o teste antes do código."},
        ]
        blob = {
            "pt": {
                "heading": "Checklist para salvar",
                "body": SAVE_BODY_PT,
                "summary_points": points,
            }
        }
        pt(deck, 8)["body"] = (
            "```Json\n" + json.dumps(blob, ensure_ascii=False) + "\n```"
        )
        repaired = repair_copy_hygiene(pt(deck, 8), "pt", load_presentation_policy(POV))
        items = repaired["summary_points"]
        assert isinstance(items, list)
        assert [item["title"] for item in items] == [p["title"] for p in points]
        assert items[0]["icon_name"] == "target"
        assert repaired["body"] == SAVE_BODY_PT

    def test_blob_with_partial_items_keeps_the_current_items(self) -> None:
        payload = copy.deepcopy(pt(prod_deck(), 8))
        before = copy.deepcopy(payload["summary_points"])
        payload["body"] = json.dumps({
            "heading": "Checklist para salvar",
            "body": SAVE_BODY_PT,
            "summary_points": [{"title": "Só título"}],
        })
        repaired = repair_copy_hygiene(payload, "pt", load_presentation_policy(POV))
        assert repaired["summary_points"] == before

    def test_fence_around_plain_copy_is_dropped(self) -> None:
        payload = _content(
            "body", "```\nEu vejo o mesmo erro em todo PR do meu time.\n```"
        )
        repaired = repair_copy_hygiene(payload, "pt", load_presentation_policy(POV))
        assert repaired["body"] == "Eu vejo o mesmo erro em todo PR do meu time."

    def test_v3_payload_is_untouched(self) -> None:
        payload = _content("body", blob_body())
        assert (
            repair_copy_hygiene(payload, "pt", load_presentation_policy(V3)) == payload
        )

    def test_en_blob_reads_the_english_copy(self) -> None:
        payload = copy.deepcopy(en(broken_deck(), 3))
        payload["body"] = blob_body()
        repaired = repair_copy_hygiene(payload, "en", load_presentation_policy(POV))
        assert repaired["body"] == en(prod_deck(), 3)["body"]

    def test_key_point_split_never_ends_on_a_connector(self) -> None:
        """Scenario: A key point is never split on a connector word."""
        assert split_key_point("Comece com dois ou três agentes, não dez.", 36) == (
            "Comece com dois ou três agentes",
            "não dez.",
        )
        title, _ = split_key_point(
            "Comece com dois ou três agentes de cada vez sem pressa alguma", 20
        ) or ("", "")
        assert title == "Comece com dois"
