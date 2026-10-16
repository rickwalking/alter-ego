# Carousel "Ponto de Vista: Notícia" prompts, v1 (AE-0406, ADR-0023)

The prompt family for `content_mode = pov_news` carousels: news analysis told
through the owner's point of view. Same contract (`pov_hook_v1`), roles, thesis
step and validators as `carousel_pov/v1`; only the voice differs. Directory-
discovered by `agents/prompts/registry.py`; selected by
`domain.content_mode.pov_prompt_domain()` and rendered with `version="v1"`.

**Voice (spec §3.1):** facts first (what happened, who, when, from the sources),
then why it matters to a software developer, then the owner's first-person read on
the `pov` and `twist` (verdict) slides only. No hype, no invented numbers, general
software-dev examples, and never a word about how content is approved.

**Quotes (spec §4):** the scout's verified quotes reach the outline and the content
prompt as data (`quotes`: id, name, handle, `text_pt`). On a `point` or `twist`
slide the model may return `quote_id`; it never writes the quote. Code places the
card verbatim (`text_pt` on PT, `text_en` on EN, at most 2 per deck,
`domain/news_quote_cards.py`) and the autopilot content gate re-checks it.

| File | Rendered by | Differs from `carousel_pov/v1` |
|---|---|---|
| `outline.yaml` | `PovOutlineMixin.generate_pov_outline` | News narrative (fact → why it matters → my read → evidence → counterpoint → twist → verdict); lists the quotes. |
| `hook.yaml` | `PovOutlineMixin.hook_candidates` | News-analysis hook formulas. |
| `content.yaml` | `ContentDraftAgent.draft_slide` | Facts-first voice, first person only on pov/twist, optional `quote_id`. |
| `caption.yaml` | `build_caption_prompt` | Adds the fact line; forbids a source list (the `Fontes:` footer is appended by code, `domain/source_footer.py`). |

Change a template by adding a `v2/` folder; never edit v1 in place.
