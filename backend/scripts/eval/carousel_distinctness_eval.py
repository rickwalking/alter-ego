"""Offline cross-slide distinctness eval for carousel content (AE-0291).

NOT a CI gate. Run manually against a real GLM 5.2 carousel run to check that the
content phase produces distinct slide bodies. It reads a JSON file of slide drafts
(``[{"slide_index": 1, "draft_text": "..."}, ...]``) — e.g. the ``slide_drafts``
persisted for a project — and reports pairwise body similarity plus the slides the
distinctness metric would flag for re-draft.

Usage (from the backend/ directory):
    uv run python scripts/eval/carousel_distinctness_eval.py drafts.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Reuse the exact metric the generator uses so the eval and the runtime agree.
from rag_backend.application.services.carousel.content_distinctness import (
    DISTINCTNESS_SIMILARITY_THRESHOLD,
    body_similarity,
    find_duplicate_slide_indices,
)

_USAGE = "usage: carousel_distinctness_eval.py <drafts.json>"
_EXPECTED_ARGC = 2


def _load_bodies(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("drafts JSON must be a list of slide objects")
    return [str(item.get("draft_text", "")) for item in data if isinstance(item, dict)]


def _report(bodies: list[str]) -> None:
    print(f"Slides: {len(bodies)}  threshold: {DISTINCTNESS_SIMILARITY_THRESHOLD}")
    for left in range(len(bodies)):
        for right in range(left + 1, len(bodies)):
            score = body_similarity(bodies[left], bodies[right])
            flag = (
                " <-- NEAR-DUPLICATE"
                if score >= DISTINCTNESS_SIMILARITY_THRESHOLD
                else ""
            )
            print(f"  slide {left + 1} vs {right + 1}: {score:.2f}{flag}")
    flagged = find_duplicate_slide_indices(bodies)
    labels = ", ".join(str(index + 1) for index in flagged) or "none"
    print(f"Would re-draft slides: {labels}")


def main() -> None:
    if len(sys.argv) != _EXPECTED_ARGC:
        raise SystemExit(_USAGE)
    _report(_load_bodies(Path(sys.argv[1])))


if __name__ == "__main__":
    main()
