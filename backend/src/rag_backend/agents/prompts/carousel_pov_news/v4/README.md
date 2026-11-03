# Carousel "Ponto de Vista: Notícia" prompts, v4

Only `content.yaml` has a v4; it mirrors `carousel_pov/v4/content.yaml` for
the news-analysis voice and renders from `POV_PROMPT_CONTENT_VERSION`. The
hook renders from `v2`; outline and caption still render from `v1`. v3 and v1
`content.yaml` are kept for rollback.

Changes from `v3/content.yaml` (AE-0599, prod gate blocks of 2026-11-02):

- This slide's contract limits are rendered inline in the "Limites" paragraph
  (`slide_limits`, from `carousel_copy_budget/v2/slide_limits.yaml`), before
  the rubric and the answer format; v3 only pointed at the instruction context.
- Count the characters, emphasis markers included, and stay a little below
  each limit; items only when the slide's role asks for them.

Facts first, the verified-quote rules, the voice rules and the return contract
are unchanged. No hardcoded number in the template.
