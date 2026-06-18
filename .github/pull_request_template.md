<!-- Conventional PR title, e.g. feat(api): add foo (AE-####) -->

## Summary

<!-- What changed and why. Link the ticket: AE-#### -->

## Test evidence

<!-- Commands run + results. Reproduce CI gates locally: bash scripts/ci/gates.sh <scope> -->

## Checklist

- [ ] One logical change; conventional commit messages
- [ ] Tests added/updated; `bash scripts/ci/gates.sh <scope>` reproduced green
- [ ] No secrets or API keys committed
- [ ] ADR added/updated if architecturally significant (`docs/decisions/`)
- [ ] **⚠️ I understand merging this to `main` triggers an immediate production
      deploy** (`deploy.yml` → DigitalOcean redeploy, ~12-min blip). This PR is
      safe to deploy now (no unreconciled Alembic head, not mid-incident).
