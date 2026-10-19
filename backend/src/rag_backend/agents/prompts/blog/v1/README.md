# Blog prompts v1 (AE-0424, AE-0425; ADR-0025)

Loaded through `agents.prompts.registry`.

Editor (AE-0424):

- `image_prompt.yaml` — wraps the owner-editable scene of a cover/section image
  with the no-text/no-brands rules (ADR-0025). The stored `image.prompt` is the
  scene, so "regenerate with an edited prompt" edits only the scene. The
  AE-0425 bulk generation uses the same template (one image template).
- `translate_section.yaml` — PT → EN translation of one section for the
  editor's "Generate EN translation" action (JSON `{heading, body_md}`).

Writer (AE-0425, `agents/blog_writer/`):

- `system.md` — shared writer rules (data-not-instructions, PT canonical, no verbatim copies, no H1, JSON only).
- `draft.yaml` — ONE continuous article (PT + EN translation), exactly N sections with one narrative role each. Fast model.
- `rewrite.yaml` — the single quality-gate rewrite pass of one language. Fast model.
- `judge.yaml` — reasoning-model revision notes for an article that failed the voice gate.

Never edit a released version in place: copy to `v2/`, change, and switch the default version.
