# Carousel v10 prompts

Only `slide_translations.yaml` moves to v10; every other carousel prompt keeps
its version. v9 `slide_translations.yaml` is kept for rollback.

## What changed from v9

- **Copy limits per field.** Every slide sent to the translator now carries
  `limits`: the max characters (and lines / words when the contract has them)
  of its heading, body and item titles and bodies, rendered from the
  presentation contract through the validator's resolvers
  (`copy_budget_limits.limits_payload`). v9 only asked to stay "about as long as
  the Portuguese source"; a POV carousel's EN copy came back 25-40% over budget
  (prod QA run, 2026-11-01). The prompt now says every English field must fit
  its limit with a shorter sentence of the same meaning, never a cut.

Everything else (structured fields, `<strong>` emphasis, no label scaffolding,
the quality rubric) is unchanged.
