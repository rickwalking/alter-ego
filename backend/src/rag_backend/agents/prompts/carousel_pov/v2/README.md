# Carousel "Ponto de Vista" prompts, v2 (AE-0580)

Only `hook.yaml` has a v2; every other prompt of the family still renders from
`v1` (`POV_PROMPT_VERSION`), while the hook renders from `POV_PROMPT_HOOK_VERSION`.

Changes from `v1/hook.yaml`:

- New `recent_hooks` variable: the owner's recent slide-1 openings, listed as
  data the model must not reuse — neither the phrases, variations of them, nor
  the formulas they already used.
- New mandatory diversity rule: the five candidates must sound clearly
  different from one another, in formula and sentence construction.

The never-invent rule, the thesis rule and the size limits are unchanged.
