"""Drafts, translations and a fit model double built from the prod shapes.

Every field gets synthetic prose of its recorded length and markup: whole
sentences from a per-locale pool (never one sentence twice on a slide), the
second and third words wrapped in the recorded emphasis. Blob slides carry both
locale payloads on the draft, the way the drafting model returned them; plain
slides carry PT copy plus an EN translation. The fit double answers every
requested field inside its limit and keeps the markers of the text it was
given, as the fit prompt asks ("keep the emphasis ... in the same format").
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rag_backend.application.services.carousel.copy_budget_fit_llm import (
    FitRequest,
    FitTarget,
)
from tests.unit.application.gate_shape_specs_ae0599 import (
    NONE,
    Field,
    Locale,
    S,
    Slide,
)

POLICY = "pov_hook_v1"
_CLOSE = {"**": "**", "<strong>": "</strong>"}
_CREATOR_KEYS = ("creator_name", "creator_handle", "creator_website")

PT_POOL: tuple[str, ...] = (
    "Eu vejo isso toda semana.",
    "O time perde horas com revisões sem um objetivo claro.",
    "No meu trabalho, a revisão melhora quando cada pedido tem um dono.",
    "O problema não é a ferramenta.",
    "Falta um critério simples que todo mundo entenda.",
    "Quando o critério fica escrito, a conversa sobre o código fica curta.",
    "Isso muda a forma como o time decide o que entra na versão.",
    "A pressa de entregar esconde o custo de cada retrabalho.",
    "Eu prefiro uma regra curta que todo mundo lembra de seguir.",
    "Sem essa regra, cada revisão vira uma discussão sobre gosto.",
    "O cliente sente a demora antes de qualquer métrica.",
    "Eu já errei aqui mais de uma vez.",
    "A primeira versão quase nunca é a que fica.",
    "Medir o tempo de espera mostra onde o processo trava.",
    "Uma pergunta boa economiza uma reunião inteira.",
    "O gargalo raramente está onde o time acha que está.",
    "Eu começo pelo pedido mais antigo da fila.",
    "Cada atraso pequeno vira uma semana no fim do mês.",
    "A documentação curta ganha da documentação perfeita.",
    "Ninguém lê um guia de quarenta páginas.",
    "O segredo é tornar o caminho certo o mais fácil.",
    "Quando a regra é clara, ninguém precisa pedir licença.",
    "Eu anoto cada decisão no próprio pedido.",
    "Assim a próxima pessoa entende o motivo sem perguntar.",
    "Isso pesa.",
    "Vale testar.",
    "Eu mudei de ideia.",
)
EN_POOL: tuple[str, ...] = (
    "I see this every week.",
    "The team loses hours on reviews without a clear goal.",
    "In my work, a review gets better when every request has an owner.",
    "The problem is not the tool.",
    "What is missing is a simple rule that everyone understands.",
    "When the rule is written down, the talk about the code gets short.",
    "This changes how the team decides what goes into the release.",
    "The rush to ship hides the cost of every bit of rework.",
    "I prefer a short rule that everyone remembers to follow.",
    "Without that rule, every review turns into a debate about taste.",
    "The client feels the delay before any metric shows it.",
    "I got this wrong more than once.",
    "The first version is almost never the one that stays.",
    "Measuring the waiting time shows where the process gets stuck.",
    "A good question saves a whole meeting.",
    "The bottleneck is rarely where the team thinks it is.",
    "I start with the oldest request in the queue.",
    "Every small delay becomes a week by the end of the month.",
    "Short documentation beats perfect documentation.",
    "Nobody reads a guide that runs forty pages.",
    "The trick is to make the right path the easiest one.",
    "When the rule is clear, nobody needs to ask for permission.",
    "I write every decision down on the request itself.",
    "That way the next person knows why without asking.",
    "It adds up.",
    "Worth a try.",
    "I changed my mind.",
)
PT_HEADING_WORDS: tuple[str, ...] = (
    "Critérios",
    "explícitos",
    "encurtam",
    "semanas",
    "inteiras",
    "trabalho",
    "desperdiçado",
    "projetos",
    "complicados",
    "demais",
    "equipes",
    "distribuídas",
    "lideranças",
    "ocupadas",
    "hoje",
    "times",
    "rápido",
)
EN_HEADING_WORDS: tuple[str, ...] = (
    "Explicit",
    "criteria",
    "shorten",
    "entire",
    "weeks",
    "wasted",
    "effort",
    "throughout",
    "complicated",
    "projects",
    "everywhere",
    "distributed",
    "leadership",
    "nowadays",
    "teams",
    "today",
    "fast",
    "now",
)
_POOLS = {"pt": (PT_POOL, PT_HEADING_WORDS), "en": (EN_POOL, EN_HEADING_WORDS)}


def _marked(text: str, mark: str) -> str:
    if mark == NONE or not text:
        return text
    words = text.split(" ")
    if len(words) < 3:
        return f"{mark}{text}{_CLOSE[mark]}"
    emphasized = f"{mark}{words[1]} {words[2]}{_CLOSE[mark]}"
    return " ".join([words[0], emphasized, *words[3:]])


def _closest(parts: list[str], spec: Field) -> list[str]:
    """Parts in order, each kept only when the marked text still fits the length."""
    kept: list[str] = []
    for part in parts:
        if len(_marked(" ".join([*kept, part]), spec.mark)) <= spec.length:
            kept.append(part)
    return kept or parts[:1]


def _heading(words: list[str], spec: Field) -> str:
    return _marked(" ".join(_closest(words, spec)), spec.mark)


@dataclass
class _Writer:
    """Synthetic prose for one slide and locale; never reuses a sentence."""

    locale: str
    used: set[str] = field(default_factory=set)

    def prose(self, spec: Field) -> str:
        """Unused whole sentences, as close to the recorded length as they fit."""
        if spec.length == 0:
            return ""
        pool = [s for s in _POOLS[self.locale][0] if s not in self.used]
        kept = _closest(pool, spec)
        self.used.update(kept)
        return _marked(" ".join(kept), spec.mark)

    def heading(self, spec: Field) -> str:
        """A sentence-case heading phrase up to the recorded length."""
        return _heading(list(_POOLS[self.locale][1]), spec)

    def title(self, spec: Field, position: int) -> str:
        """An item title; each position starts from a different word."""
        words = list(_POOLS[self.locale][1][position * 3 :])
        words[0] = words[0].capitalize()
        return _heading(words, spec)


def _quote_card(locale: str) -> dict[str, object]:
    quote = "A regra simples venceu." if locale == "pt" else "The simple rule won."
    return {
        "quote": quote,
        "attribution": "Ana Souza, CTO",
        "name": "Ana Souza",
        "handle": "anasouza",
        "quote_id": "q1",
    }


def _item_key(slide: Slide) -> str:
    return "summary_points" if slide.slide_type == "summary" else "features"


def locale_payload(slide: Slide, spec: Locale, locale: str) -> dict[str, object]:
    """One locale payload of the slide, filled with synthetic prose."""
    writer = _Writer(locale)
    payload: dict[str, object] = {
        "slide_type": slide.slide_type,
        "heading": writer.heading(spec.heading),
        "body": writer.prose(spec.body),
    }
    if spec.items or slide.slide_type == "content":
        payload[_item_key(slide)] = [
            {
                "icon_name": "target",
                "title": writer.title(item.title, position),
                "body": writer.prose(item.body),
            }
            for position, item in enumerate(spec.items)
        ]
    if slide.slide_type == "content":
        payload["content_kind"] = "features"
    if slide.slide_type == "cta":
        payload.update(dict.fromkeys(_CREATOR_KEYS, ""))
    return payload


def _draft(slide: Slide) -> dict[str, object]:
    pt = locale_payload(slide, slide.pt, "pt")
    draft: dict[str, object] = {
        "slide_index": slide.index,
        "slide_type": slide.slide_type,
        "role": slide.role,
        "title": pt["heading"],
        "draft_text": pt["body"],
        "policy_version": POLICY,
    }
    if slide.blob:
        draft["presentation_pt"] = pt
        draft["presentation_en"] = locale_payload(slide, slide.en, "en")
        return draft
    for key in ("features", "summary_points"):
        if pt.get(key):
            draft[key] = pt[key]
    if slide.quote_card:
        draft["insight"] = _quote_card("pt")
    return draft


def _translation(slide: Slide) -> dict[str, object]:
    en = locale_payload(slide, slide.en, "en")
    entry: dict[str, object] = {"heading": en["heading"], "body": en["body"]}
    for key in ("features", "summary_points"):
        if en.get(key):
            entry[key] = en[key]
    if slide.quote_card or slide.en_only_quote_card:
        entry["insight"] = _quote_card("en")
    return entry


def drafts_and_translations(
    shape: tuple[Slide, ...],
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    """The sanitized drafts and the EN translations the content ensure holds."""
    drafts = [_draft(slide) for slide in shape]
    translations = {str(slide.index): _translation(slide) for slide in shape}
    return drafts, translations


PT_ANSWERS: tuple[str, ...] = (
    "Eu dou um dono a cada pedido antes de abrir a revisão.",
    "Uma regra escrita deixa a conversa curta e o time calmo.",
    "Eu cobro o critério antes do código e ganho horas na semana.",
    "Cada pedido com dono chega revisado no mesmo dia útil.",
    "Um objetivo claro corta pela metade o tempo da revisão.",
    "Eu registro a decisão e a dúvida some da próxima vez.",
    "O time decide mais rápido quando o motivo está à vista.",
    "Eu troco a reunião longa por uma pergunta bem feita.",
)
EN_ANSWERS: tuple[str, ...] = (
    "I give every request an owner before the review starts.",
    "A written rule keeps the talk short and the team calm.",
    "I ask for the rule before the code and save hours each week.",
    "Every request with an owner gets reviewed on the same day.",
    "A clear goal cuts the review time in half for everyone.",
    "I record the decision and the doubt is gone next time.",
    "The team decides faster when the reason is in plain sight.",
    "I swap the long meeting for one well framed question.",
)
_SHORT = {"pt": "Eu explico o motivo a seguir.", "en": "I explain the reason next."}
_HEADS = {
    "pt": ("Revisão com dono", "Fila sem espera", "Regra visível", "Decisão anotada"),
    "en": ("Owned reviews", "Queues that flow", "Visible rules", "Logged decisions"),
}
_MARKS = ("<strong>", "**")


def _mark_of(text: str) -> str:
    return next((mark for mark in _MARKS if mark in text), NONE)


@dataclass
class ShapeFitter:
    """Answers every field inside its limit, keeping the given text's markers.

    Like a model asked for distinct copy, it never gives two fields of the same
    slide and locale the same sentence.
    """

    fail: bool = False
    calls: list[FitRequest] = field(default_factory=list)
    used: dict[tuple[int, str], set[str]] = field(default_factory=dict)

    def _candidates(self, item: FitTarget) -> tuple[str, ...]:
        target = item.target
        if "title" in target.field or target.field == "heading":
            return _HEADS[target.locale]
        pool = PT_ANSWERS if target.locale == "pt" else EN_ANSWERS
        return (*pool, _SHORT[target.locale])

    def _answer(self, item: FitTarget) -> str:
        target, limit = item.target, item.limit
        mark = _mark_of(target.text)
        used = self.used.setdefault((target.slide_index, target.locale), set())
        for text in self._candidates(item):
            marked = _marked(text, mark)
            if text not in used and len(marked) <= limit.max_characters:
                used.add(text)
                return marked
        return _SHORT[target.locale]

    async def fit(self, request: FitRequest) -> dict[str, str]:
        """One answer per requested id, or a provider failure."""
        self.calls.append(request)
        if self.fail:
            raise TimeoutError
        return {item.target.target_id: self._answer(item) for item in request.targets}


__all__ = [
    "POLICY",
    "S",
    "ShapeFitter",
    "drafts_and_translations",
    "locale_payload",
]
