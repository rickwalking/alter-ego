# carousel_copy_budget prompts

## v1

Generated slide copy fits the slide length budgets of its presentation
contract (Pedro's decision, 2026-11-01). The numbers never live in these
files: they are rendered from the contract through the validator's resolvers
(`application/services/carousel/copy_budget_limits.py`).

| File | Rendered by | Purpose |
|---|---|---|
| `slide_limits.yaml` | `instruction_context_loader._slide_block` | "Copy limits of this slide": every field of the slide type with its max characters / lines / words, appended to the per-slide block of the drafting instruction (every content prompt family). |
| `fit_fields.yaml` | `copy_budget_fit_llm.LlmCopyBudgetFitter` | The shorten step before the presentation validation: only the over-budget fields go to the fast model, each with its limit, current text, problems, slide heading and (EN) PT source. Answers are checked by code (fits or is shorter, adds no violation, no forbidden phrase); at most 2 attempts. |

## v2

`slide_limits.yaml` only (AE-0599): item limits apply only to the items the
slide's role asks for, and the emphasis markup cost per locale is stated. See
`v2/README.md`. `fit_fields.yaml` stays at v1.

Change a template by adding a new version folder; never edit one in place.

## v3

`fit_fields.yaml` only (AE-0607): same template, `max_tokens` 32000 instead of
4096. In prod every fit call spent the whole 4096 on reasoning and answered
nothing. See `v3/README.md`. `slide_limits.yaml` stays at v2.
