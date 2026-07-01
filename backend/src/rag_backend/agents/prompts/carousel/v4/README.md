# Carousel v4 prompts (AE-0291)

Prompt templates for the `hero_lower_third_v1` presentation contract. v4 supersedes
[v3](../v3/README.md) for the editorial content path; v3 is kept for rollback.

## What changed from v3

- **Cross-slide distinctness.** `content.yaml` now instructs the model to cover a
  distinct angle from the OTHER slides in the carousel. The sibling outline
  (other slides' headings + key points) is injected at runtime by the instruction
  context loader under "Other slides in this carousel" (truncation-safe placement),
  not by this template.
- **Rework feedback is deduped + imperative.** The `{{ revision_notes }}` block was
  REMOVED from `content.yaml`. Reviewer notes now render exactly once, imperatively,
  in the instruction context loader (`## Reviewer revision notes (REGENERATION)`),
  alongside the previous rejected draft so the model can diff against it. This
  removes the prior double-render (soft heading here + section in the loader).
- **Live model config.** `content.yaml`'s `model:` block (`temperature`,
  `max_tokens: 32000`) is now actually applied via a per-call `.bind(...)` in
  `ContentDraftAgent.draft_slide`. `max_tokens` is kept large because GLM 5.2 is a
  reasoning model — do NOT lower it to the old v3 value (2048), which truncates
  reasoning + output.

## Files

- `outline.yaml` — seven-slide outline planning (unchanged from v3).
- `content.yaml` — per-slide draft generation with cross-slide distinctness.

## Policy fragment

Both templates expect `presentation_policy_context` to be generated at runtime by
`render_presentation_policy_context()` from the typed `CarouselPresentationPolicy`
loaded via `load_presentation_policy()`.

Do not duplicate slide counts, copy budgets, geometry ratios, or Lucide allowlist
values in these templates. The canonical source is
`backend/src/rag_backend/agents/skills/carousel-pipeline/contracts/hero_lower_third_v1.yaml`.

## Usage

```python
from rag_backend.agents.prompts.registry import render_prompt

prompt_text, model_cfg = render_prompt(
    "carousel",
    "content",
    variables={
        "slide_number": slide_number,
        "title": title,
        "key_points": key_points,
        "locale": locale,
        "phase": phase,
        "presentation_policy_context": policy_context,
        "persona_context": persona_context,
    },
    version="v4",
)
# model_cfg is applied via llm.bind(**model_cfg) — no longer discarded.
```
