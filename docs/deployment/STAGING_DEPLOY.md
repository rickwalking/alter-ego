# Staging Deployment — DEPLOY-001

Deploy the editorial workflow platform to a staging environment before production rollout.

## Prerequisites

- Docker and Docker Compose installed
- API keys configured (OpenAI, Anthropic, Pinecone, Gemini)
- DNS entry for staging (e.g. `staging.marinssolutions.com`)

## Quick Start

```bash
# From repository root
cp .env.staging.example .env.staging   # create from template below
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
```

## Environment Template (`.env.staging`)

```bash
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=<strong-random-password>
POSTGRES_DB=rag_db_staging
SECRET_KEY=<openssl rand -hex 32>
ANON_SECRET_KEY=<openssl rand -hex 32>
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=...
GEMINI_API_KEY=...
ALLOWED_ORIGINS=https://staging.marinssolutions.com

# Feature flags (DEPLOY-003) — toggle for canary rollout
FEATURE_FLAG_EDITORIAL_WORKFLOW=true
FEATURE_FLAG_QUALITY_CHECKS=true
FEATURE_FLAG_WORKFLOW_BOARD=true
FEATURE_FLAG_CONTENT_CALENDAR=true
WORKFLOW_ALERTS_ENABLED=true
```

## Post-Deploy Steps

1. **Run database migrations**
   ```bash
   docker compose -f docker-compose.staging.yml exec backend uv run alembic upgrade head
   ```

2. **Run Phase 5 data migration (dry run first)**
   ```bash
   docker compose -f docker-compose.staging.yml exec backend \
     uv run python scripts/migrate_phase5.py --dry-run
   docker compose -f docker-compose.staging.yml exec backend \
     uv run python scripts/migrate_phase5.py
   ```

3. **Verify health**
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8001/health/ready
   ```

4. **Run load tests (DEPLOY-002)**
   ```bash
   cd backend && uv run pytest tests/load/test_phase5_endpoints.py -v
   ```

## Production Rollout (DEPLOY-003)

1. Deploy to staging and validate all workflow features
2. Set feature flags to `false` in production initially
3. Enable flags incrementally:
   - `FEATURE_FLAG_WORKFLOW_BOARD=true`
   - `FEATURE_FLAG_EDITORIAL_WORKFLOW=true`
   - `FEATURE_FLAG_QUALITY_CHECKS=true`
   - `FEATURE_FLAG_CONTENT_CALENDAR=true`
4. Monitor alerts defined in `docs/deployment/workflow-alerts.yaml`

## Ports

| Service  | Staging Port |
|----------|-------------|
| Backend  | 8001        |
| Frontend | 3002        |

Production uses nginx reverse proxy — see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).
