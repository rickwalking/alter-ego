# `quality/` prompt domain

Prompt templates for the **quality** surface, loaded via
`agents.prompts.registry.render_prompt("quality", "<name>", variables, version="v1")`.
Migrated from inline f-strings in AE-0243 (byte-for-byte parity, see
`backend/tests/unit/agents/test_prompt_registry_parity.py`).

## v1

- `evaluate.yaml` — rubric evaluation prompt (from `QualityAgent._build_evaluation_prompt`).
- `improve_suggestions.yaml` — improvement suggestions for a failing criterion (from `QualityAgent.generate_improvement_suggestions`).
