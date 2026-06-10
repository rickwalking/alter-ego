# Carousel v3 prompts

Prompt templates for the `hero_lower_third_v1` presentation contract.

## Files

- `outline.yaml` — seven-slide outline planning with policy fragment injection.
- `content.yaml` — per-slide draft generation with Lucide `icon_name` guidance.

## Policy fragment

Both templates expect `presentation_policy_context` to be generated at runtime by
`render_presentation_policy_context()` from the typed
`CarouselPresentationPolicy` loaded via `load_presentation_policy()`.

Do not duplicate slide counts, copy budgets, geometry ratios, or Lucide allowlist
values in these templates. The canonical source is
`skills/runtime/carousel-pipeline/contracts/hero_lower_third_v1.yaml`.

## Usage

```python
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
    render_presentation_policy_context,
)

policy = load_presentation_policy("hero_lower_third_v1")
policy_context = render_presentation_policy_context(policy)
prompt_text, model_cfg = render_prompt(
    "carousel",
    "outline",
    variables={
        "topic": topic,
        "audience": audience,
        "brief": brief,
        "sources": sources,
        "locale": locale,
        "phase": phase,
        "slide_count": policy.slide_count,
        "presentation_policy_context": policy_context,
        "persona_context": persona_context,
        "revision_notes": revision_notes,
    },
    version="v3",
)
```
