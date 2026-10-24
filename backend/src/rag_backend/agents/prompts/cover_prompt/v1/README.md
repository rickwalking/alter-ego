# Cover prompt prompts v1

Loaded through `agents.prompts.registry`.

- `ideas.yaml` — "Mais ideias" under the Slide 1 photo prompt: the carousel topic
  (sanitised, delimited as data) and the slide palette → JSON `{"ideas": [...]}` with
  prompts for a new cover photo. Fast model queue. Only the topic and the palette reach
  the model, never personal data; the server re-validates
  every idea (length, no markup, no repeats) and keeps at most six.
