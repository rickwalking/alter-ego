# Blog prompts v1 (AE-0424)

- `image_prompt.yaml` — wraps the owner-editable scene of a cover/section image
  with the no-text/no-brands rules (ADR-0025). The stored `image.prompt` is the
  scene, so "regenerate with an edited prompt" edits only the scene.
- `translate_section.yaml` — PT → EN translation of one section for the
  editor's "Generate EN translation" action (JSON `{heading, body_md}`).
