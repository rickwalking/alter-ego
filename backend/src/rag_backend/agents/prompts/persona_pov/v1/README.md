# Persona context for "Ponto de Vista" prompts, v1 (AE-0371, PR #106 review)

`context.yaml` renders the `persona_context` block of `carousel_pov/v1/outline.yaml`
from the project's persona (`PovOutlineMixin.generate_pov_outline`):

- voice: description, opinion expression, sentence and paragraph style;
- signature phrases: the persona's `preferred_phrases` (the persona model has no
  separate "signature line" field, so the preferred phrases play that role);
- forbidden phrases: the persona's `forbidden_phrases`.

The persona shapes how the text sounds, never what the author thinks or lived
(growth plan core rule). A project with no persona renders an explicit empty
context instead (`NO_PERSONA_CONTEXT`).

Change the template by adding a `v2/` folder; never edit v1 in place.
