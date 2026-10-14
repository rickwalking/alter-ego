# Carousel v6 prompts (AE-0366)

v6 supersedes [v5](../v5/README.md) for the editorial content path and is the
version `ContentDraftAgent` renders (`carousel/content`, `version=v6`). v5 is kept
for rollback.

## What changed from v5

- **Explicit casing rules.** Prod carousel `8e350d6e` (GLM) shipped headings and
  bodies in all-lowercase with lowercased proper nouns ("o que muda para devs no
  brasil"). v5 never stated a Portuguese casing rule, and the drafter's inputs
  were lowercased before rendering. v6 requires normal sentence case in PT and
  EN for every heading, body and structured item, and requires proper nouns,
  brands and acronyms to keep their capitals.
- **A body on every non-CTA slide.** A content slide rendered only its title
  because the model put all its copy in structured items. v6 requires a 1-3
  sentence body on every slide except the CTA (closing: a short sentence before
  its actions; summary: its points).
- **Quality rubric + self-check** (see below), shared with the EN translation
  prompt, which moves out of an inline constant into `slide_translations.yaml`.
- The translator input is no longer lowercased or stripped of `<strong>` tags
  (`sanitize_model_copy`), which produced the all-lowercase EN slides.
- The return contract (`draft_text`, `long_form_notes`, ...) is unchanged.

The deterministic guards (blocking `*_not_sentence_case_*` and `body_empty`
rules in `hero_lower_third_v3.yaml`) do not depend on the model following this
prompt; v6 only lowers how often they fire.

## Files

- `content.yaml`: per-slide draft generation.
- `slide_translations.yaml`: PT to EN slide translation. Supersedes the inline
  `PROMPT_EDITORIAL_SLIDE_TRANSLATIONS` constant (kept for rollback); rendered by
  `_generate_en_translations` at `version=v6`.

## Quality rubric

Both templates take a `{{ quality_rubric }}` variable: the numbered checklist +
self-check step rendered by `render_quality_rubric()` from the `quality_rubric`
section of `contracts/hero_lower_third_v3.yaml`. That section is the single
source of truth: each rubric item lists the validator rule codes that enforce
it (BLOCKING), and the policy loader fails when a listed code has no severity.
Edit the rubric there, not here.
