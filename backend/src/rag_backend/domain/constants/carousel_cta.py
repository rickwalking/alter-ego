"""CTA slide copy variants by goal (AE-0372, growth plan 16.3 F / 16.4 #5).

One specific action per carousel instead of the generic "Siga para mais
conteúdo como esse". ``{handle}`` is the creator handle, ``@`` included.
"""

from __future__ import annotations

CTA_GOAL_FOLLOW = "follow"
CTA_GOAL_SEND = "send"
CTA_GOAL_COMMENT = "comment"
DEFAULT_CTA_GOAL = CTA_GOAL_FOLLOW
CTA_GOALS: frozenset[str] = frozenset({
    CTA_GOAL_FOLLOW,
    CTA_GOAL_SEND,
    CTA_GOAL_COMMENT,
})

# The creator handle when the project has none (was inline in strategies/cta.py).
DEFAULT_CTA_HANDLE = "pedromarins.ai"

CTA_COPY_PT: dict[str, str] = {
    CTA_GOAL_FOLLOW: ("Siga {handle}: eu traduzo IA em decisões reais."),
    CTA_GOAL_SEND: "Manda pra quem precisa ouvir isso.",
    CTA_GOAL_COMMENT: "Discorda? Me diz nos comentários.",
}
CTA_COPY_EN: dict[str, str] = {
    CTA_GOAL_FOLLOW: ("Follow {handle}: I turn AI into real decisions."),
    CTA_GOAL_SEND: "Send this to someone who needs to hear it.",
    CTA_GOAL_COMMENT: "Disagree? Tell me in the comments.",
}

__all__ = [
    "CTA_COPY_EN",
    "CTA_COPY_PT",
    "CTA_GOALS",
    "CTA_GOAL_COMMENT",
    "CTA_GOAL_FOLLOW",
    "CTA_GOAL_SEND",
    "DEFAULT_CTA_GOAL",
    "DEFAULT_CTA_HANDLE",
]
