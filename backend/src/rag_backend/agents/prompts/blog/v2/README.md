# Blog prompts v2 (AE-0435)

The blog writer (`agents/blog_writer/`, `PROMPT_VERSION = "v2"`) loads these. The
editor prompts (`image_prompt.yaml`, `translate_section.yaml`) stay on `v1/`.

Why v2: prod 2026-10-19/20 stored Portuguese as `translations.en` (posts ba37f6f9,
99886e71). The EN article failed the voice gate; the persona scorer (Portuguese
samples) answered with Portuguese suggestions, the v1 judge forwarded them without
knowing the article's language, and the v1 rewrite (Portuguese samples + Portuguese
notes) wrote Portuguese.

Changes from v1:

- `judge.yaml` — told the article's language (`language_name`); ignores suggestions
  that change the language; notes keep the article in that language.
- `rewrite.yaml` — persona samples carry the voice, never the language; ignores
  notes that ask to switch the language.
- `draft.yaml` — the `en` article is English only (no copied Portuguese sentence).
- `system.md` — unchanged copy.

The deterministic EN language gate (`application/services/blog/blog_english_gate.py`)
is the safety net when a model still answers in Portuguese.
