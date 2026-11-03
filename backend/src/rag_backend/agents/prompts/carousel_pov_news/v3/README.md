# Carousel "Ponto de Vista: Notícia" prompts, v3

Only `content.yaml` has a v3; it mirrors `carousel_pov/v3/content.yaml` for
the news-analysis voice and renders from `POV_PROMPT_CONTENT_VERSION`. The
hook renders from `v2`; outline and caption still render from `v1`. v1
`content.yaml` is kept for rollback.

Changes from `v1/content.yaml` (Pedro's decision, 2026-11-01):

- No hardcoded character numbers per role (v1's sub-hook "até 80"
  contradicted the contract). The contract limits arrive per slide in the
  instruction context ("Copy limits of this slide",
  `carousel_copy_budget/v1/slide_limits.yaml`), from the values the validator
  enforces.
- A mandatory "Limites" paragraph: every field within its limit from the first
  version, complete sentences, never relying on a cut.

Facts first, the verified-quote rules, the voice rules and the return
contract are unchanged.
