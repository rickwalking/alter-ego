# `persona/` prompt domain

Prompt templates for the **persona** surface, loaded via
`agents.prompts.registry.render_prompt("persona", "<name>", variables, version="v1")`.
Migrated from inline f-strings in AE-0243 (byte-for-byte parity, see
`backend/tests/unit/agents/test_prompt_registry_parity.py`).

## v1

- `enforce.yaml` — persona voice style guide (from `PersonaAgent._build_style_guide`).
