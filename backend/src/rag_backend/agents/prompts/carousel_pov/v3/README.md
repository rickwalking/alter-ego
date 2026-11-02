# Carousel "Ponto de Vista" prompts, v3

Only `content.yaml` has a v3; it renders from `POV_PROMPT_CONTENT_VERSION`.
The hook renders from `v2` (`POV_PROMPT_HOOK_VERSION`); outline and caption
still render from `v1` (`POV_PROMPT_VERSION`). v1 `content.yaml` is kept for
rollback.

Changes from `v1/content.yaml` (Pedro's decision, 2026-11-01: generated copy
must fit the slide budgets by itself):

- No hardcoded character numbers per role. v1 wrote its own limits ("até 80",
  "até 90", "até 160", "até 200", "até 60") and the hook sub-line number
  contradicted the contract (`pov_hook_v1` allows 40). The only limits the
  model sees now are the contract's, rendered per slide by
  `carousel_copy_budget/v1/slide_limits.yaml` into the instruction context
  ("Copy limits of this slide") from the same values the validator enforces.
- A mandatory "Limites" paragraph: write each field inside its limit from the
  first version, with complete sentences, never relying on a cut.
- Role guidance stays qualitative (rehook: one short sentence; point and
  twist: one or two short sentences).

The never-invent rule, the voice rules and the return contract are unchanged.
