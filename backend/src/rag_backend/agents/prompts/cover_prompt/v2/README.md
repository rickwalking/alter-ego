# Cover prompt prompts v2

Loaded through `agents.prompts.registry` (AE-0562; v1 kept for rollback).

- `ideas.yaml` — "Mais ideias": the same inputs as v1 (sanitised topic, palette line,
  language), but each idea must differ from the others on location, wardrobe, pose,
  angle and light, tie the topic through a prop or metaphor (no title text in the
  image) and name colours in words, never hex. The answer is
  `{"ideas": [{"location", "wardrobe", "pose", "angle", "light", "prompt"}]}`; the
  server keeps only the `prompt`, drops ideas with hex codes and drops an idea that
  repeats another's location and pose. Plain string ideas are still read.
