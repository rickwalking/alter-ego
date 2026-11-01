"""Localized slides, copy pools and a fake fit model for the shorten-step tests.

The copy is real Portuguese and English prose that passes the copy rules
(sentence case, final punctuation, the right language, no repeated sentence),
so the only blocking problem of an over-budget field is its length. The fake
model never calls a provider: it answers from an explicit map or picks short,
distinct sentences from an answer pool that never overlaps the slide copy.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from rag_backend.application.services.carousel.copy_budget_fit_llm import (
    FitRequest,
    FitTarget,
)

POLICY_V4 = "hero_lower_third_v4"
POLICY_POV = "pov_hook_v1"

PT_SENTENCES: tuple[str, ...] = (
    "Eu vejo o time perder horas com revisões sem um objetivo claro.",
    "No meu trabalho, a revisão melhora quando cada pedido tem um dono.",
    "O problema não é a ferramenta, é a falta de um critério simples.",
    "Quando o critério fica escrito, a conversa sobre o código fica curta.",
    "Isso muda a forma como o time decide o que entra na versão.",
    "A pressa de entregar esconde o custo de cada retrabalho.",
    "Eu prefiro uma regra curta que todo mundo lembra de seguir.",
    "Sem essa regra, cada revisão vira uma discussão sobre gosto.",
)
EN_SENTENCES: tuple[str, ...] = (
    "I see the team lose hours on reviews without a clear goal.",
    "In my work, a review gets better when every request has an owner.",
    "The problem is not the tool, it is the lack of a simple rule.",
    "When the rule is written down, the talk about the code gets short.",
    "This changes how the team decides what goes into the release.",
    "The rush to ship hides the cost of every bit of rework.",
    "I prefer a short rule that everyone remembers to follow.",
    "Without that rule, every review turns into a debate about taste.",
)
PT_ANSWERS: tuple[str, ...] = (
    "Eu defino um dono para cada pedido de revisão antes de começar.",
    "Uma regra escrita deixa a revisão curta e o time mais calmo.",
    "Eu cobro o critério antes do código e economizo horas.",
    "Cada pedido com dono chega revisado no mesmo dia.",
    "Um objetivo claro corta pela metade o tempo de revisão.",
    "Eu anoto a decisão e o time para de repetir a conversa.",
)
EN_ANSWERS: tuple[str, ...] = (
    "I give every review request one owner before it starts.",
    "A written rule keeps the review short and the team calm.",
    "I ask for the rule before the code and save hours.",
    "Every request with an owner gets reviewed the same day.",
    "A clear goal cuts the review time in half.",
    "I write the decision down and the team stops repeating it.",
)
PT_HEADING_ANSWERS: tuple[str, ...] = (
    "Revisão sem critério custa caro",
    "Um dono por pedido muda tudo",
)
EN_HEADING_ANSWERS: tuple[str, ...] = (
    "Reviews without a rule cost time",
    "One owner per request changes it",
)


def prose(sentences: tuple[str, ...], min_characters: int) -> str:
    """Distinct sentences joined until the text is at least ``min_characters``."""
    kept: list[str] = []
    for sentence in sentences:
        kept.append(sentence)
        if len(" ".join(kept)) >= min_characters:
            break
    return " ".join(kept)


def locale_payload(slide_type: str, heading: str, body: str) -> dict[str, object]:
    """One locale payload with the slide type the validator reads."""
    return {"slide_type": slide_type, "heading": heading, "body": body}


def localized_slide(
    index: int,
    pt: dict[str, object],
    en: dict[str, object],
) -> dict[str, object]:
    """One localized slide record as the review build produces it."""
    return {
        "slide_index": index,
        "slide_type": pt["slide_type"],
        "presentation_pt": pt,
        "presentation_en": en,
    }


def content_slide(index: int, *, pt_body: str, en_body: str) -> dict[str, object]:
    """A content slide with short headings and the given bodies."""
    return localized_slide(
        index,
        locale_payload("content", "Revisões precisam de um dono", pt_body),
        locale_payload("content", "Reviews need an owner", en_body),
    )


def summary_items(
    sentences: tuple[str, ...], titles: tuple[str, ...], min_body: int
) -> list[dict[str, object]]:
    """Summary points with distinct titles and bodies of at least ``min_body``."""
    items: list[dict[str, object]] = []
    for position, title in enumerate(titles):
        rotated = sentences[position * 2 :] + sentences[: position * 2]
        items.append({
            "icon_name": "target",
            "title": title,
            "body": prose(rotated, min_body),
        })
    return items


def _default_pool(item: FitTarget) -> tuple[str, ...]:
    english = item.target.locale == "en"
    if item.target.field == "heading":
        return EN_HEADING_ANSWERS if english else PT_HEADING_ANSWERS
    return EN_ANSWERS if english else PT_ANSWERS


@dataclass
class FakeFitter:
    """Records every request; answers from ``answers`` or a fitting pool sentence."""

    answers: dict[str, str] = field(default_factory=dict)
    answer_fn: Callable[[FitTarget], str] | None = None
    calls: list[list[str]] = field(default_factory=list)
    requests: list[FitRequest] = field(default_factory=list)
    error: Exception | None = None

    async def fit(self, request: FitRequest) -> dict[str, str]:
        """Answer every requested id (or raise the configured error)."""
        self.requests.append(request)
        self.calls.append([item.target.target_id for item in request.targets])
        if self.error is not None:
            raise self.error
        used: dict[tuple[str, ...], int] = {}
        texts: dict[str, str] = {}
        for item in request.targets:
            target_id = item.target.target_id
            if target_id in self.answers:
                texts[target_id] = self.answers[target_id]
                continue
            if self.answer_fn is not None:
                texts[target_id] = self.answer_fn(item)
                continue
            pool = _default_pool(item)
            position = used.get(pool, 0)
            used[pool] = position + 1
            texts[target_id] = pool[position % len(pool)]
        return texts


__all__ = [
    "EN_ANSWERS",
    "EN_SENTENCES",
    "POLICY_POV",
    "POLICY_V4",
    "PT_ANSWERS",
    "PT_SENTENCES",
    "FakeFitter",
    "content_slide",
    "locale_payload",
    "localized_slide",
    "prose",
    "summary_items",
]
