# Carousel v7 prompts (AE-0372, AE-0376)

v7 is the Radar IA (`news_analysis`) generation of the Instagram growth plan
(`docs/architecture/instagram-growth-pov-mode.md`, plan section 16.4). v1-v6 stay
frozen for rollback and for the projects already stamped with them.

## Files

- `caption_prompt.yaml` (AE-0372): replaces the v2 caption (hook + value + question +
  double CTA + 12-18 PT/EN hashtags) with: the slide-1 hook on line 1, 2-4 short
  "what it changes for you" lines, one question that invites disagreement, ONE CTA
  chosen by `cta_goal` (follow / send / comment), plain-text search keywords and 3-5
  mostly-PT hashtags. Rendered by `build_caption_prompt` for every Radar IA project.

The caption is new in v7 rather than in the existing `v3/` folder (where the plan put
it) because `v3/` already holds the outline/content prompts and existing prompt
versions are never edited.
