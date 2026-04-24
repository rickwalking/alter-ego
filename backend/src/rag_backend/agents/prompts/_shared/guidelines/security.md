# Security Guidelines for LLM Prompts

## Input Validation

- All user-provided text injected into prompts MUST be escaped/sanitized
- Never trust user input to be well-formed or safe
- Validate all IDs (UUIDs, project IDs) before database lookups

## Output Handling

- LLM outputs should be treated as untrusted until validated
- JSON responses must be parsed with strict schema validation
- CSS overrides must be sanitized before writing to disk
- Image prompts must be filtered for banned terms

## Prompt Injection Prevention

- Use structured prompts with clear delimiters
- Separate instructions from user input with markers like `<<< >>>`
- Never concatenate raw user input directly into system instructions
