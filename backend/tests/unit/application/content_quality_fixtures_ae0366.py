"""Prod-shaped slide drafts for the content quality tests (8e350d6e, PT-BR, GLM).

Every draft carries the prod key set: slide_index, title, key_points,
slide_type, tldr_strip, draft_text, presentation_pt, presentation_en,
image_prompt. ``clean_drafts()`` is a valid 7-slide carousel; ``prod_drafts()``
reproduces the three owner-reported defects on slides 4-6.
"""

from __future__ import annotations

import copy

SLIDE4_INDEX = 4
SLIDE5_INDEX = 5
SLIDE6_INDEX = 6
LOWERCASE_HEADING_5 = "a versão para robótica leva o gemini ao mundo físico"
FIXED_HEADING_5 = "A versão para robótica leva o gemini ao mundo físico"
LOWERCASE_HEADING_6 = "o que muda para devs no brasil"
LOWERCASE_BODY_6 = "à frente, o time testa a api nova. depois publica."
FIXED_BODY_6 = "À frente, o time testa a api nova. Depois publica."


def _item(icon: str, title: str, body: str) -> dict[str, object]:
    return {"icon_name": icon, "title": title, "body": body}


def _draft(
    index: int, slide_type: str, pt: dict[str, object], en: dict[str, object]
) -> dict[str, object]:
    return {
        "slide_index": index,
        "title": str(pt.get("heading") or ""),
        "key_points": ["Ponto um", "Ponto dois"],
        "slide_type": slide_type,
        "tldr_strip": "Resumo curto do carrossel." if index == 1 else None,
        "draft_text": str(pt.get("body") or ""),
        "presentation_pt": {"slide_type": slide_type, **pt},
        "presentation_en": {"slide_type": slide_type, **en},
        "image_prompt": f"Editorial illustration {index}",
    }


def _features_pt() -> list[dict[str, object]]:
    return [
        _item("brain", "Raciocínio melhor", "Resolve tarefas longas com menos erros."),
        _item("target", "Foco em código", "Lidera benchmarks de segurança."),
        _item("shield-check", "Mais seguro", "Resiste a injeções indiretas."),
    ]


def _features_en() -> list[dict[str, object]]:
    return [
        _item("brain", "Better reasoning", "Solves long tasks with fewer errors."),
        _item("target", "Code focus", "Leads the security benchmarks."),
        _item("shield-check", "Safer", "Resists indirect injections."),
    ]


def clean_drafts() -> list[dict[str, object]]:
    """A valid 7-slide hero_lower_third_v3 carousel."""
    return [
        _draft(
            1,
            "intro",
            {
                "heading": "Gemini 4 Argon chegou",
                "body": "O novo modelo do Google muda o jogo para quem programa.",
            },
            {
                "heading": "Gemini 4 Argon is here",
                "body": "Google's new model changes the game for developers.",
            },
        ),
        _draft(
            2,
            "summary",
            {
                "heading": "O que você vai ver",
                "body": "",
                "summary_points": [
                    _item("brain", "Modelo", "O que é o Argon."),
                    _item("target", "Números", "Onde ele lidera."),
                    _item("shield-check", "Impacto", "O que muda para você."),
                ],
            },
            {
                "heading": "What you will see",
                "body": "",
                "summary_points": [
                    _item("brain", "Model", "What Argon is."),
                    _item("target", "Numbers", "Where it leads."),
                    _item("shield-check", "Impact", "What changes for you."),
                ],
            },
        ),
        *[
            _draft(
                index,
                "content",
                {
                    "heading": f"Ponto de conteúdo número {index}",
                    "body": f"O Argon divide a liderança no item {index} da análise.",
                    "content_kind": "features",
                    "features": _features_pt(),
                },
                {
                    "heading": f"Content point number {index}",
                    "body": f"Argon shares the lead on item {index} of the review.",
                    "content_kind": "features",
                    "features": _features_en(),
                },
            )
            for index in (3, 4, 5)
        ],
        _draft(
            6,
            "closing",
            {
                "heading": "O que muda para devs no Brasil",
                "body": "",
                "actions": [
                    _item("wrench", "Teste a API", "Rode seus prompts no Argon."),
                    _item("book-open", "Leia o relatório", "Veja os números."),
                    _item("flask-conical", "Compare", "Meça contra seu modelo."),
                ],
            },
            {
                "heading": "What changes for devs in Brazil",
                "body": "",
                "actions": [
                    _item("wrench", "Try the API", "Run your prompts on Argon."),
                    _item("book-open", "Read the report", "See the numbers."),
                    _item("flask-conical", "Compare", "Measure it against yours."),
                ],
            },
        ),
        _draft(
            7,
            "cta",
            {"heading": "Salve e compartilhe", "body": ""},
            {"heading": "Save and share", "body": ""},
        ),
    ]


def prod_drafts() -> list[dict[str, object]]:
    """The owner-reported defects: empty body (4), lowercase (5, 6)."""
    drafts = copy.deepcopy(clean_drafts())
    slide4 = drafts[SLIDE4_INDEX - 1]
    for key in ("presentation_pt", "presentation_en"):
        slide4[key]["body"] = ""
        slide4[key]["features"] = []
    slide4["draft_text"] = ""
    slide5 = drafts[SLIDE5_INDEX - 1]
    slide5["title"] = LOWERCASE_HEADING_5
    slide5["presentation_pt"]["heading"] = LOWERCASE_HEADING_5
    slide6 = drafts[SLIDE6_INDEX - 1]
    slide6["title"] = LOWERCASE_HEADING_6
    slide6["presentation_pt"]["heading"] = LOWERCASE_HEADING_6
    slide6["presentation_pt"]["body"] = LOWERCASE_BODY_6
    slide6["presentation_pt"]["actions"] = [
        _item("wrench", "teste a api", "rode seus prompts no argon."),
        _item("book-open", "leia o relatório", "veja os números."),
        _item("flask-conical", "compare", "meça contra seu modelo."),
    ]
    slide6["draft_text"] = ""
    return drafts
