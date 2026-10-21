"""Shared fakes and the prod fixture for the content-gate repair tests.

``tests/fixtures/ae0430_carousel_5344_content_gate.json`` is the read-only
export of prod carousel 5344b6c6 (2026-10-19): its 7 localized slides and the
12 blocking violations the owner could not clear with two revisions.

PROD_ANSWERS holds within-limit rewrites of the 12 prod fields, as a limit-respecting
model would answer. The same exported state also carries the label and emphasis leaks
the QA noted ("**PT**", "**PT** ** **", a "PT:" line before "Heading:", EN "**…**"); the
gate flags them, so the fake model answers those 4 fields with clean copy too.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import cast

from rag_backend.application.services.carousel.content_gate_repair import (
    FieldRepairRequest,
)

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "ae0430_carousel_5344_content_gate.json"
)
POLICY_V4 = "hero_lower_third_v4"

PROD_ANSWERS: dict[str, str] = {
    "1:en:heading": "Grok Bot booked a table. Nobody talked about the computer.",
    "1:en:body": (
        "I look at the computer, not the demo. The leap is the runtime that keeps "
        "working outside the chat."
    ),
    "1:en:tldr_strip": "Grok Bot, phone booking, agent with its own computer",
    "1:pt:body": (
        "Todo mundo viu o Grok Bot reservar mesa. Ninguém falou do computador. "
        "A ligação chama atenção."
    ),
    "3:pt:features[0].body": (
        "Navegador, terminal e arquivos ficam no ambiente dele, não no seu setup."
    ),
    "3:en:body": (
        "Grok Bot runs on its own <strong>cloud computer</strong>, with a browser, "
        "terminal and files. It is not your laptop carrying the task, it is its "
        "machine. In practice, you close the lid and keep going from your phone."
    ),
    "3:en:features[0].body": (
        "Browser, terminal and files live in its environment, not in your setup."
    ),
    "3:en:features[1].body": (
        "Close the laptop and follow the task in the app. The server keeps the state."
    ),
    "4:pt:body": (
        "Na prática, o ganho não é a resposta, é a **execução**. Você descreve o "
        "pedido e o agente conduz a ligação até a reserva estar feita. O pedido "
        "não volta pela metade."
    ),
    "4:en:body": (
        "A boring task becomes real delegation. What comes back is not a draft to "
        "review, but <strong>a completed action</strong>. The target is the "
        "decision, not the paragraph."
    ),
    "6:pt:actions[0].body": "Um comando claro e fácil de desfazer. O alvo é o erro barato.",
    "6:pt:actions[1].body": "Leia cada passo no app antes de liberar mais acesso.",
    "6:pt:actions[2].body": "Passou no teste? Solte uma tarefa um pouco mais longa.",
    "6:en:actions[0].body": "One clear command that is easy to undo. Aim for a cheap mistake.",
    "6:en:actions[1].body": "Read every step in the app before you grant more access.",
    "6:en:actions[2].body": "Did it pass? Hand over a slightly longer task next.",
}


def load_fixture() -> dict[str, object]:
    """The exported prod state (a fresh copy each call)."""
    return cast(dict[str, object], json.loads(FIXTURE.read_text(encoding="utf-8")))


def prod_slides() -> list[dict[str, object]]:
    """The 7 prod localized slides."""
    slides = load_fixture()["localized_slides"]
    return copy.deepcopy(cast(list[dict[str, object]], slides))


class FakeRepairer:
    """Answers from a fixed table; records the ids asked per round."""

    def __init__(
        self,
        answers: dict[str, str] | None = None,
        *,
        fail: bool = False,
    ) -> None:
        self.answers = PROD_ANSWERS if answers is None else answers
        self.fail = fail
        self.calls: list[list[str]] = []
        self.requests: list[FieldRepairRequest] = []

    async def repair(self, request: FieldRepairRequest) -> dict[str, str]:
        self.calls.append([target.target_id for target in request.targets])
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("model down")
        return dict(self.answers)


class OverLimitRepairer(FakeRepairer):
    """Always answers with a text longer than any item budget."""

    async def repair(self, request: FieldRepairRequest) -> dict[str, str]:
        await super().repair(request)
        return {
            target.target_id: f"{target.text} E ainda mais um trecho longo aqui."
            for target in request.targets
        }
