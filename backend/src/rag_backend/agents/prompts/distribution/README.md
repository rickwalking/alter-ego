# `distribution/` prompt domain

Prompt templates for the **distribution** surface, loaded via
`agents.prompts.registry.render_prompt("distribution", "<name>", variables, version="v1")`.
Migrated from inline f-strings in AE-0243 (byte-for-byte parity, see
`backend/tests/unit/agents/test_prompt_registry_parity.py`).

## v1

- `linkedin_post.yaml` — single-language LinkedIn post from blog content (from `linkedin_post_generator._build_prompt`).
