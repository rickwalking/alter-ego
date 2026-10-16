"""The 9-slide POV carousel of prod run b241ded5 (carousel 98a2e2f0, 2026-10-16).

``prod_deck()`` is the deck as it should have been: the 9 slides the owner
approved after the hand patch (hook, rehook, pov, 3 points, twist, save, CTA).
``broken_deck()`` puts back what prod shipped: slide 3 written as a
```` ```json ```` fenced bilingual object (auto-capitalised to "```Json") and
slide 8's PT body starting with ``## Checklist para salvar``. The EN copy uses
``<strong>`` and the PT copy ``**bold**``: the pipeline's two legit emphasis
formats, which no rule flags.

The prod copy itself is not readable from CI; the clean copy is the shape of
the approved deck (budgets, roles, ``**bold**`` emphasis, proper nouns,
numbers), written in the carousel's voice.
"""

from __future__ import annotations

import copy
import json

POV = "pov_hook_v1"
SLIDE_BLOB = 3
SLIDE_HEADING_LEAK = 8

POV_HEADING_PT = "Por que eu digo isso"
POV_BODY_PT = (
    "Eu reviso PRs de agentes toda semana no meu trabalho. O erro que mais vejo "
    "é **escopo** aberto demais, não código ruim."
)
POV_HEADING_EN = "Why I say this"
POV_BODY_EN = (
    "I review agent PRs every week at work. The mistake I see most is "
    "<strong>scope</strong> left too open, not bad code."
)
SAVE_BODY_PT = "Use esta lista antes de abrir o próximo PR com um agente."
HEADING_LEAK_BODY_PT = f"## Checklist para salvar\n{SAVE_BODY_PT}"


def _item(icon: str, title: str, body: str) -> dict[str, object]:
    return {"icon_name": icon, "title": title, "body": body}


def _slide(
    index: int, slide_type: str, pt: dict[str, object], en: dict[str, object]
) -> dict[str, object]:
    return {
        "slide_index": index,
        "slide_type": slide_type,
        "presentation_pt": {"slide_type": slide_type, **pt},
        "presentation_en": {"slide_type": slide_type, **en},
    }


def _copy(heading: str, body: str) -> dict[str, object]:
    return {"heading": heading, "body": body}


_CONTENT: tuple[tuple[int, tuple[str, str], tuple[str, str]], ...] = (
    (
        2,
        (
            "O agente entrega tudo, menos o que você pediu",
            "Ele resolve o ticket e ainda mexe em arquivos que ninguém mandou tocar.",
        ),
        (
            "The agent delivers everything but what you asked",
            "It closes the ticket and still edits files nobody asked it to touch.",
        ),
    ),
    (3, (POV_HEADING_PT, POV_BODY_PT), (POV_HEADING_EN, POV_BODY_EN)),
    (
        4,
        (
            "Prompt sem limite vira refatoração",
            "Quando eu não digo onde parar, o agente reescreve módulos inteiros "
            "para corrigir um bug de duas linhas.",
        ),
        (
            "A prompt with no limit becomes a refactor",
            "When I do not say where to stop, the agent rewrites whole modules to "
            "fix a two line bug.",
        ),
    ),
    (
        5,
        (
            "Defina o que fica de fora",
            "Eu listo os arquivos que o agente pode tocar e os proibidos. Em 3 de "
            "cada 4 tickets o diff cai pela metade.",
        ),
        (
            "Define what stays out",
            "I list the files the agent may touch and the forbidden ones. In 3 out "
            "of 4 tickets the diff drops by half.",
        ),
    ),
    (
        6,
        (
            "Testes primeiro, código depois",
            "No Claude Code eu peço os testes antes da mudança. Se o teste não "
            "cobre o pedido, o agente saiu do escopo.",
        ),
        (
            "Tests first, code later",
            "In Claude Code I ask for the tests before the change. If the test does "
            "not cover the request, the agent left the scope.",
        ),
    ),
    (
        7,
        (
            "O agente não é o problema",
            "O problema é o pedido vago. Um engenheiro júnior faria a mesma coisa "
            "com o mesmo ticket.",
        ),
        (
            "The agent is not the problem",
            "The problem is the vague request. A junior engineer would do the same "
            "thing with the same ticket.",
        ),
    ),
)


def _save_slide() -> dict[str, object]:
    points_pt = [
        _item("target", "Arquivos permitidos", "Diga onde o agente pode mexer."),
        _item("shield-check", "Fora do escopo", "Liste o que ele não deve tocar."),
        _item("flask-conical", "Teste do pedido", "Peça o teste antes do código."),
    ]
    points_en = [
        _item("target", "Allowed files", "Say where the agent may work."),
        _item("shield-check", "Out of scope", "List what it must not touch."),
        _item("flask-conical", "Request test", "Ask for the test before the code."),
    ]
    return _slide(
        8,
        "summary",
        {**_copy("Checklist para salvar", SAVE_BODY_PT), "summary_points": points_pt},
        {
            **_copy("A checklist to save", "Use this list before your next agent PR."),
            "summary_points": points_en,
        },
    )


def prod_deck() -> list[dict[str, object]]:
    """The approved 9-slide POV deck: every slide passes every rule."""
    hook = _slide(
        1,
        "intro",
        _copy(
            "Seu agente de IA não sabe o que é escopo", "E isso custa caro no sprint"
        ),
        _copy(
            "Your AI agent does not know what scope is", "And it costs you the sprint"
        ),
    )
    content = [
        _slide(index, "content", _copy(*pt), _copy(*en)) for index, pt, en in _CONTENT
    ]
    cta = _slide(
        9,
        "cta",
        _copy(
            "Me segue para mais bastidores", "Eu mostro como uso agentes no trabalho"
        ),
        _copy("Follow me for more", "I show how I use agents at work"),
    )
    return [hook, *content, _save_slide(), cta]


def blob_body() -> str:
    """Slide 3 as prod stored it: the fenced object, auto-capitalised."""
    blob = {
        "pt": {"heading": POV_HEADING_PT, "body": POV_BODY_PT},
        "en": {"heading": POV_HEADING_EN, "body": POV_BODY_EN},
    }
    return "```Json\n" + json.dumps(blob, ensure_ascii=False, indent=2) + "\n```"


def pt(deck: list[dict[str, object]], index: int) -> dict[str, object]:
    """The PT payload of slide ``index`` (1-based)."""
    payload = deck[index - 1]["presentation_pt"]
    assert isinstance(payload, dict)
    return payload


def en(deck: list[dict[str, object]], index: int) -> dict[str, object]:
    """The EN payload of slide ``index`` (1-based)."""
    payload = deck[index - 1]["presentation_en"]
    assert isinstance(payload, dict)
    return payload


def broken_deck() -> list[dict[str, object]]:
    """The deck prod shipped: slide 3 fenced blob, slide 8 ## heading."""
    deck = copy.deepcopy(prod_deck())
    pt(deck, SLIDE_BLOB)["body"] = blob_body()
    pt(deck, SLIDE_HEADING_LEAK)["body"] = HEADING_LEAK_BODY_PT
    return deck
