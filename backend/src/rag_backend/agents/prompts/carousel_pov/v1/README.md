# Carousel "Ponto de Vista" prompts, v1 (AE-0375, ADR-0021)

The prompt family for `content_mode = pov` carousels (growth plan 16.3 E).
Directory-discovered by `agents/prompts/registry.py`; rendered with `version="v1"`.

**Core rule:** the model may sharpen the owner's thesis, but never invent his
opinion, experiences, test results or numbers. Every template states it; the
personal proof is the only source of first-person anecdotes and numbers.

| File | Rendered by | Purpose |
|---|---|---|
| `hook.yaml` | `PovOutlineAgent.hook_candidates` | 5 slide-1 hooks in PT, one per formula, ≤10 words / ≤60 chars, stored on outline slide 1 (`hook_candidates`); the owner picks or edits one at the outline gate (`PUT /api/carousels/{id}/hook`). |
| `outline.yaml` | `PovOutlineAgent.generate_outline` | The 8-10 slide sequence of `pov_hook_v1` (roles listed in order); the format picks the narrative. Roles are re-stamped by position afterwards. |
| `content.yaml` | `ContentDraftAgent.draft_slide` (POV) | One slide in first person with the v6 return contract (`draft_text`, `long_form_notes`, ...) and per-role guidance; slide 1 uses the chosen hook verbatim. |
| `caption.yaml` | `build_caption_prompt` (POV) | Hook on line 1, 2-4 first-person lines, one question, one CTA by `cta_goal`, 3-5 mostly-PT hashtags. |

Change a template by adding a `v2/` folder; never edit v1 in place.
