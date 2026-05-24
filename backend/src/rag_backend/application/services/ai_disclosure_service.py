"""AI content disclosure labeling service (QUAL-002)."""

from __future__ import annotations

from rag_backend.domain.constants.ai_disclosure import (
    AI_ACTION_GENERATE_IMAGE,
    AI_ACTION_IMPROVE,
    AI_ACTION_SUGGEST,
    AI_DISCLOSURE_ASSISTED,
    AI_DISCLOSURE_GENERATED,
    AI_DISCLOSURE_HYBRID,
    AI_DISCLOSURE_NONE,
)

_ACTION_WEIGHTS: dict[str, int] = {
    AI_ACTION_SUGGEST: 1,
    AI_ACTION_IMPROVE: 2,
    AI_ACTION_GENERATE_IMAGE: 1,
}

DISCLOSURE_WEIGHT_GENERATED = 5
DISCLOSURE_WEIGHT_HYBRID = 2


class AiDisclosureService:
    """Tracks and computes AI disclosure labels for editorial content."""

    def record_action(self, metadata: dict[str, object], action: str) -> dict[str, object]:
        """Record an AI action and update disclosure metadata."""
        updated = dict(metadata)
        actions = list(updated.get("ai_actions", []))
        if not isinstance(actions, list):
            actions = []
        actions.append({"action": action})
        updated["ai_actions"] = actions
        updated["ai_action_count"] = len(actions)
        updated["ai_disclosure_label"] = self.compute_label(updated)
        return updated

    def compute_label(self, metadata: dict[str, object]) -> str:
        """Derive disclosure label from AI usage metadata."""
        actions = metadata.get("ai_actions", [])
        if not isinstance(actions, list) or not actions:
            return str(metadata.get("ai_disclosure_label", AI_DISCLOSURE_NONE))

        total_weight = 0
        for entry in actions:
            if isinstance(entry, dict):
                action = str(entry.get("action", ""))
                total_weight += _ACTION_WEIGHTS.get(action, 0)

        if total_weight == 0:
            return AI_DISCLOSURE_NONE
        if total_weight >= DISCLOSURE_WEIGHT_GENERATED:
            return AI_DISCLOSURE_GENERATED
        if total_weight >= DISCLOSURE_WEIGHT_HYBRID:
            return AI_DISCLOSURE_HYBRID
        return AI_DISCLOSURE_ASSISTED

    def requires_disclosure(self, label: str) -> bool:
        """Return True if label indicates AI involvement."""
        return label != AI_DISCLOSURE_NONE

    def validate_for_publish(self, label: str | None) -> bool:
        """Disclosure labels must be set for AI-assisted content before publish."""
        if label is None or label == AI_DISCLOSURE_NONE:
            return True
        return label in (AI_DISCLOSURE_ASSISTED, AI_DISCLOSURE_GENERATED, AI_DISCLOSURE_HYBRID)


__all__ = ["AiDisclosureService"]
