"""AE-0367: the owner autofix's pure text repairs.

Gherkin: tests/features/autopilot_owner_autofix.feature
(Happy path: the owner taps Fix issues; EN re-translation fails)
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.owner_autofix_fill import (
    FEATURE_BUDGET,
    FillSource,
    build_items,
    key_point_pairs,
    split_key_point,
)
from rag_backend.application.services.carousel.owner_autofix_text import (
    balance_strong,
    is_untranslated,
    looks_portuguese,
    lowercase_nouns,
    restore_proper_nouns,
)
from rag_backend.application.services.carousel.owner_autofix_vocabulary import (
    VocabularySources,
    build_vocabulary,
)
from rag_backend.application.services.carousel.presentation_content_rules import (
    emphasis_markup_is_valid,
)

_ICONS = ("chart-column", "book-open", "newspaper", "brain")


@pytest.mark.unit
class TestBalanceStrong:
    """Scenario: mangled or unbalanced <strong> tags are rebuilt."""

    def test_rebuilds_the_sanitizer_residue(self) -> None:
        mangled = "Resiste a strongindirect prompt injections/strong hoje."
        fixed = balance_strong(mangled)
        assert fixed == "Resiste a <strong>indirect prompt injections</strong> hoje."
        assert emphasis_markup_is_valid(fixed)

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("<strong>aberto sem fim", "<strong>aberto sem fim</strong>"),
            ("sobra</strong> aqui", "sobra aqui"),
            (
                "<strong>a <strong>b</strong> c</strong>",
                "<strong>a b</strong> c",
            ),
            ("<em>x</em> e <b>y</b>", "x e y"),
            ("< STRONG >caixa</ strong >", "<strong>caixa</strong>"),
        ],
    )
    def test_balances_and_keeps_only_strong(self, raw: str, expected: str) -> None:
        fixed = balance_strong(raw)
        assert fixed == expected
        assert emphasis_markup_is_valid(fixed)

    def test_valid_text_is_unchanged_and_idempotent(self) -> None:
        text = "O <strong>Argon</strong> chegou. Sem tags aqui."
        assert balance_strong(text) == text
        assert balance_strong(balance_strong("a strongb/strong c")) == (
            "a <strong>b</strong> c"
        )

    def test_the_word_strong_alone_is_not_a_tag(self) -> None:
        text = "A strong model and a stronger one"
        assert balance_strong(text) == text


@pytest.mark.unit
class TestRestoreProperNouns:
    """Scenario: "argon" is lowercase where the outline says "Argon"."""

    def test_restores_fully_lowercase_nouns_only(self) -> None:
        nouns = ("Argon", "Brasil", "OpenAI")
        text = "o argon chega ao brasil; ARGON e openai também"
        assert restore_proper_nouns(text, nouns) == (
            "o Argon chega ao Brasil; ARGON e OpenAI também"
        )

    def test_whole_words_only(self) -> None:
        assert restore_proper_nouns("argonauta e brasileiro", ("Argon", "Brasil")) == (
            "argonauta e brasileiro"
        )

    def test_lowercase_nouns_lists_what_the_restore_fixes(self) -> None:
        nouns = ("Argon", "Brasil", "iPhone", "api")
        assert lowercase_nouns("o argon no Brasil, iphone", nouns) == (
            "argon",
            "iphone",
        )
        assert lowercase_nouns("", nouns) == ()


@pytest.mark.unit
class TestUntranslatedDetection:
    """Scenario: EN re-translation targets only untranslated EN texts."""

    @pytest.mark.parametrize(
        "text",
        [
            "O que muda para devs no Brasil",
            "Rode seus prompts no Argon e compare com o seu modelo.",
            "À frente, a equipe testa.",
        ],
    )
    def test_portuguese_is_detected(self, text: str) -> None:
        assert looks_portuguese(text)

    @pytest.mark.parametrize(
        "text",
        [
            "What changes for devs in Brazil",
            "Argon now drives real robot arms.",
            "São Paulo",
            "",
        ],
    )
    def test_english_is_not_portuguese(self, text: str) -> None:
        assert not looks_portuguese(text)

    def test_identical_copy_is_untranslated(self) -> None:
        assert is_untranslated("Gemini 4 Argon Robotics", "Gemini 4 Argon Robotics")
        assert is_untranslated("<strong>Ponto</strong> de vista", "Ponto de vista")

    def test_short_identical_names_and_empty_text_are_fine(self) -> None:
        assert not is_untranslated("Argon", "Argon")
        assert not is_untranslated("", "Texto em português de verdade")
        assert not is_untranslated("Argon leads the review.", "O Argon lidera.")


@pytest.mark.unit
class TestVocabulary:
    """Scenario: proper nouns come from the carousel's own vocabulary."""

    def test_mid_sentence_capitals_of_the_outline_are_nouns(self) -> None:
        vocabulary = build_vocabulary(
            VocabularySources(
                trusted=("A versão para robótica leva o Argon ao mundo físico",),
                copy=("a versão para robótica leva o argon ao mundo físico",),
            )
        )
        assert "Argon" in vocabulary
        assert "A" not in vocabulary
        assert "versão" not in vocabulary

    def test_title_case_research_titles_only_give_distinctive_tokens(self) -> None:
        vocabulary = build_vocabulary(
            VocabularySources(titles=("How Gemini Changes Robotics With GPT-5 Tools",))
        )
        assert "GPT-5" in vocabulary
        assert "Changes" not in vocabulary
        assert "Robotics" not in vocabulary

    def test_sentence_case_titles_count_like_the_outline(self) -> None:
        vocabulary = build_vocabulary(
            VocabularySources(titles=("O lançamento do Argon pela equipe",))
        )
        assert "Argon" in vocabulary

    def test_trusted_lowercase_use_vetoes_a_word(self) -> None:
        vocabulary = build_vocabulary(
            VocabularySources(
                trusted=("Usa o gás argon como exemplo.",),
                copy=("Leia Argon hoje.",),
            )
        )
        assert "Argon" not in vocabulary

    def test_common_words_short_tokens_and_long_caps_are_skipped(self) -> None:
        vocabulary = build_vocabulary(
            VocabularySources(
                trusted=("Dicas Para os devs. Veja IA e IMPORTANTE e API.",)
            )
        )
        assert "Para" not in vocabulary
        assert "IA" not in vocabulary
        assert "IMPORTANTE" not in vocabulary
        assert "API" in vocabulary

    def test_constants_and_configured_nouns_are_always_included(self) -> None:
        vocabulary = build_vocabulary(VocabularySources(configured=("Gemini",)))
        assert "Brasil" in vocabulary
        assert "Gemini" in vocabulary
        # Longest first, so "OpenAI" is restored before a shorter overlap.
        assert vocabulary.index("JavaScript") < vocabulary.index("Python")

    def test_the_most_frequent_spelling_wins(self) -> None:
        vocabulary = build_vocabulary(
            VocabularySources(trusted=("Use o GitHub. Veja o GitHub e o Github.",))
        )
        assert "GitHub" in vocabulary
        assert "Github" not in vocabulary


@pytest.mark.unit
class TestFillFromKeyPoints:
    """Scenario: a title-only content slide gets features from its key points."""

    def test_splits_on_a_separator(self) -> None:
        assert split_key_point(
            "Simulação Real2Sim: treina antes do mundo real", 32
        ) == (
            "Simulação Real2Sim",
            "treina antes do mundo real",
        )

    def test_splits_on_words_within_the_title_budget(self) -> None:
        pair = split_key_point(
            "Robôs aprendem tarefas novas sem retreinar o modelo", 32
        )
        assert pair == ("Robôs aprendem tarefas novas", "sem retreinar o modelo")

    @pytest.mark.parametrize("point", ["", "   ", "Ok"])
    def test_too_short_points_do_not_split(self, point: str) -> None:
        assert split_key_point(point, 32) is None

    def test_builds_three_to_four_items_with_icons_per_position(self) -> None:
        points = (
            "Simulação Real2Sim: treina antes do mundo real",
            "braços robóticos: seguem instruções em linguagem natural",
            "segurança: para sozinho quando algo sai do esperado",
            "custo menor: roda em hardware comum de laboratório",
            "quinto ponto: nunca aparece porque o limite é quatro",
        )
        items = build_items(
            FillSource(
                pairs=key_point_pairs(points, FEATURE_BUDGET.title),
                icons=_ICONS,
                budget=FEATURE_BUDGET,
            )
        )
        assert items is not None
        assert len(items) == 4
        assert [item["icon_name"] for item in items] == list(_ICONS)
        assert items[1]["title"] == "Braços robóticos"
        assert items[1]["body"] == "Seguem instruções em linguagem natural"

    def test_long_text_is_cut_at_a_word_boundary(self) -> None:
        body = "palavra " * 30
        items = build_items(
            FillSource(
                pairs=(("Um", body), ("Dois", body), ("Três", body)),
                icons=("brain",),
                budget=FEATURE_BUDGET,
            )
        )
        assert items is not None
        assert all(len(str(item["body"])) <= FEATURE_BUDGET.body for item in items)
        assert str(items[0]["body"]).endswith("palavra")
        assert {item["icon_name"] for item in items} == {"brain"}

    def test_fewer_than_three_pairs_or_no_icons_build_nothing(self) -> None:
        pairs = (("Um", "corpo"), ("Dois", "corpo"))
        assert (
            build_items(FillSource(pairs=pairs, icons=_ICONS, budget=FEATURE_BUDGET))
            is None
        )
        three = (*pairs, ("Três", "corpo"))
        assert (
            build_items(FillSource(pairs=three, icons=(), budget=FEATURE_BUDGET))
            is None
        )


@pytest.mark.unit
def test_a_first_word_longer_than_the_title_budget_does_not_split() -> None:
    assert split_key_point("Anticonstitucionalissimamente longo demais", 10) is None


@pytest.mark.unit
def test_titles_without_long_words_are_read_as_sentences() -> None:
    assert "Argon" not in build_vocabulary(VocabularySources(titles=("A IA",)))
    assert "BYD" in build_vocabulary(VocabularySources(titles=("Vi a BYD",)))


@pytest.mark.unit
def test_urls_domains_and_handles_are_never_rewritten() -> None:
    nouns = ("GitHub", "Argon")
    text = "veja github.com/argon, @argon e argon-cli; o argon. github hoje"
    assert restore_proper_nouns(text, nouns) == (
        "veja github.com/argon, @argon e argon-cli; o Argon. GitHub hoje"
    )
