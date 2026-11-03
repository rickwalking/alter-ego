# carousel_copy_budget, v2

Only `slide_limits.yaml` has a v2; it renders from
`COPY_BUDGET_LIMITS_PROMPT_VERSION`. `fit_fields.yaml` still renders from v1
(`COPY_BUDGET_PROMPT_VERSION`). v1 `slide_limits.yaml` is kept for rollback.

Changes from `v1/slide_limits.yaml` (AE-0599, prod gate blocks of 2026-11-02):

- The item limits apply only to items the slide's role asks for. v1 listed
  `features[].title` / `features[].body` on every content slide and the
  drafting model started returning feature lists (inside a bilingual JSON
  draft) on slides whose role asks for one idea: 12 of 18 POV slides came back
  as such blobs after AE-0588, against 8 of 108 in the 12 runs before it.
- Emphasis cost per locale: Portuguese `**...**` (4 characters of markup),
  English `<strong>...</strong>` (17). English copy the drafting model writes
  in a blob used the Portuguese markers; once converted to `<strong>` a field
  that looked inside its limit can be 13 characters over it.

The numbers still come from the contract through the validator's resolvers
(`copy_budget_limits.py`); none is written in this file.
