# Carousel "Ponto de Vista" prompts, v4

Only `content.yaml` has a v4; it renders from `POV_PROMPT_CONTENT_VERSION`.
The hook renders from `v2`; outline and caption still render from `v1`. v3 and
v1 `content.yaml` are kept for rollback.

Changes from `v3/content.yaml` (AE-0599, prod gate blocks of 2026-11-02):

- This slide's contract limits are rendered inline in the "Limites" paragraph
  (`slide_limits`, the same block the instruction context carries, from
  `carousel_copy_budget/v2/slide_limits.yaml`), right before the rubric and the
  answer format. v3 only pointed at the block in the instruction context and
  the drafted copy came back 1.5 to 2.7 times over its limits (bodies of 287 to
  540 characters against 200, summary point bodies of 149 to 322 against 90).
  When the variable is empty the paragraph falls back to the v3 pointer.
- Count the characters, emphasis markers included, and stay a little below
  each limit.
- Items (features, summary_points) only when the slide's role asks for them.

Still no hardcoded number in the template: every number is the contract's.
The never-invent rule, the voice rules and the return contract are unchanged.
