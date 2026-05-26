# Remediation Plan — Alter-Ego Assessment

> Generated: 2026-05-04
> Based on codebase audit across backend, frontend, and infrastructure.
> Each item includes: action, affected files, test/Gherkin requirement, and risk if deferred.

---

## Phase 0 — Firefighting (Days 1-2)

### P0.1: Secure WebSocket Token

**Problem**: JWT tokens leaked in WebSocket query string (`?token=...`), visible in proxy logs, browser history, and `Referer` headers.

**Action**:
1. Backend: Add `Sec-WebSocket-Protocol` subprotocol negotiation in WebSocket handshake (`api/websocket.py`).
2. Frontend: Update `use-websocket-chat.ts:51` and `create/[id]/page.tsx:78-82` to pass token via subprotocol header instead of query param.
3. Middleware: Strip `token` query param from WebSocket upgrade requests in `nginx/*.conf`.

**Gherkin**: `backend/tests/features/websocket_auth.feature` — new
```gherkin
Feature: WebSocket Authentication via Subprotocol
  Scenario: Token passed via Sec-WebSocket-Protocol is accepted
    Given a valid JWT token
    When a WebSocket connection is opened with the token in Sec-WebSocket-Protocol
    Then the connection is authenticated and chat messages flow

  Scenario: Token in query string is rejected
    When a WebSocket connection is opened with ?token=<valid_token>
    Then the connection is rejected with 403

  Scenario: Missing token is rejected
    When a WebSocket connection is opened without authentication
    Then the connection is rejected with 401
```

**Tests**: Backend: `tests/unit/api/test_websocket_auth.py`, Frontend: `tests/unit/hooks/use-websocket-chat.test.ts`
**Risk if deferred**: **HIGH** — token exfiltration via referrer headers, proxy logs

---

### P0.2: Remove/Secure Duplicate Blog Component

**Problem**: `components/blog/post-content.tsx` is a duplicate of the route-level version and lacks `allowedElements` sanitization on `react-markdown` — XSS vector if imported.

**Action**:
1. Remove `components/blog/post-content.tsx` and `components/blog/post-header.tsx` (duplicates).
2. Update all imports in the codebase to point to `app/(blog)/blog/[id]/blog-post-content.tsx` and `blog-post-header.tsx`.
3. Verify the canonical versions have `allowedElements` set on `react-markdown`.

**Gherkin**: Update `tests/features/blog_content_cleanup.feature`
```gherkin
Scenario: Duplicate component is removed
  Given the blog components directory
  When I check for duplicate post-content files
  Then there is exactly one canonical post-content component
  And the canonical component has allowedElements sanitization
```

**Tests**: Add import resolution test in `tests/unit/blog/component-resolution.test.ts`
**Risk if deferred**: **HIGH** — XSS via rendered blog content

---

### P0.3: Wire Husky Hooks

**Problem**: `husky`, `lint-staged`, `commitlint` are in `devDependencies` but `.husky/` directory doesn't exist. No pre-commit hooks run.

**Action**:
1. Run `npx husky init` to create `.husky/` directory.
2. Create `.husky/pre-commit` running `lint-staged`.
3. Create `.husky/commit-msg` running `commitlint --edit $1`.
4. Configure `lint-staged` in `package.json`:
   - `*.{ts,tsx}`: `eslint --fix`, `prettier --write`
   - `*.{json,css,md}`: `prettier --write`

**Gherkin**: Not applicable (tooling configuration)
**Tests**: Manual verification — `git commit` triggers hooks
**Risk if deferred**: **HIGH** — bad commits, inconsistent code style, no commit message convention

---

### P0.4: Create Frontend CI Quality Gates

**Problem**: No frontend CI workflow. No TypeScript typecheck, no ESLint, no test enforcement for frontend PRs.

**Action**: Create `.github/workflows/frontend-quality-gates.yml`:
```yaml
name: Frontend Quality Gates
on: [pull_request]
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm, cache-dependency-path: frontend/ }
      - run: npm ci
        working-directory: frontend
      - run: npm run typecheck
        working-directory: frontend
      - run: npm run lint
        working-directory: frontend
      - run: npm run test:run
        working-directory: frontend
```

**Gherkin**: Not applicable
**Risk if deferred**: **HIGH** — TypeScript errors, lint violations, and test failures merge unchecked

---

## Phase 1 — Security Hardening (Days 3-5)

### P1.1: Add CSP Headers

**Problem**: No Content Security Policy header in nginx, FastAPI, or Next.js.

**Action**:
1. Add `add_header Content-Security-Policy` to all nginx server blocks.
2. Start with a restrictive policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' wss:; font-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`

**Gherkin**: `tests/features/security_headers.feature` — new
```gherkin
Feature: Security Headers
  Scenario: All responses include CSP header
    When a request is made to any page
    Then the response includes Content-Security-Policy header

  Scenario: CSP blocks inline scripts
    Given a page with inline <script> tag
    When the page loads
    Then the script is blocked by CSP
```

**Risk if deferred**: **MEDIUM** — XSS against API can load arbitrary scripts

---

### P1.2: Refactor 7 Raw fetch() Calls to Use apiCall()

**Problem**: Admin dialogs, login page, and `use-upload.ts` use raw `fetch()`/`XMLHttpRequest`, bypassing centralized auth header injection, error handling, CSRF.

**Files**:
- `components/admin/create-user-dialog.tsx:33-37`
- `components/admin/edit-user-dialog.tsx:34-37`
- `components/admin/delete-user-dialog.tsx:31`
- `components/admin/change-password-dialog.tsx:35-37`
- `app/(admin)/admin/users/page.tsx:28`
- `app/login/page.tsx:21-26`
- `hooks/use-upload.ts:30-51`

**Action**:
1. Add `upload` method to `api-client.ts` that returns a function using `XMLHttpRequest` internally but exposes the same `apiCall()` interface.
2. Refactor each file to use `apiCall()` from `@/lib/api-client`.
3. Remove duplicate token extraction and error parsing code.

**Gherkin**: Update `tests/features/auth.feature`
```gherkin
Scenario: Admin CRUD uses centralized API client
  Given an authenticated admin user
  When they create/edit/delete a user
  Then the request includes the auth header via apiCall()
  And errors are standardized through the error handler
```

**Tests**: Add unit tests for each admin dialog: `components/admin/*.test.tsx` (7 new test files)
**Risk if deferred**: **HIGH** — auth header missing on admin operations, inconsistent error handling

---

### P1.3: Add `SecretStr` to Config and Path Traversal Protection

**Backend actions**:
1. Replace `str` with `SecretStr` for all API keys in `infrastructure/config.py:45`.
2. Add path traversal validation in `infrastructure/storage.py:40` — reject paths containing `..` or `/`.
3. Add file size limits and content-type validation in `infrastructure/storage.py:50-70`.
4. Add file locking for concurrent writes in `infrastructure/storage.py:80`.

**Gherkin**: `tests/features/security_path_traversal.feature` — new
```gherkin
Feature: Path Traversal Protection
  Scenario: Directory traversal in file path is rejected
    Given a file storage operation
    When the path contains ".." or absolute paths
    Then the operation is rejected with 400

  Scenario: Oversized file upload is rejected
    Given an upload request
    When the file exceeds size limits
    Then the operation is rejected with 413
```

**Tests**: `tests/unit/infrastructure/test_storage_security.py`
**Risk if deferred**: **HIGH** — arbitrary file read/write, secret exposure in logs

---

### P1.4: Add `NODE_ENV=production` and Disable Swagger in Prod

**Problem**: FastAPI `/docs` and `/redoc` exposed in production. Backend runs as root.

**Action**:
1. Add `DISABLE_DOCS=true` env var check in `api/main.py` — conditionally disable `/docs` and `/redoc`.
2. Add `USER alterego` in both Dockerfiles, with `chown -R` for app directories.
3. Set `NODE_ENV=production` in frontend Dockerfile (verify it's already set before build).

**Risk if deferred**: **MEDIUM** — full API schema publicly readable in production

---

## Phase 2 — Architecture & Code Quality (Days 6-10)

### P2.1: Refactor Files Exceeding 400 Lines

| File | Lines | Action |
|------|-------|--------|
| `application/use_cases.py` | 537 | Split into `use_cases/carousel.py`, `use_cases/research.py`, `use_cases/search.py` |
| `api/routes.py` | 487 | Already split into `routes/` directory (verify no monolithic `routes.py` remains) |
| `frontend/app/(public)/page.tsx` | 251 | Extract `HeroSection`, `LatestPosts`, `FeaturesGrid` into `components/home/` |
| `frontend/features/publish/publish-panel.tsx` | ~340 | Extract Instagram/LinkedIn tabs into `components/publish/` |

**Gherkin**: Feature files exist for carousel, publish flow. Update scenarios to cover refactored boundaries.
**Tests**: Existing tests must pass after refactor. Add boundary tests for extracted sub-components.

---

### P2.2: Eliminate All Magic Strings and Numbers

**Action**: Create dedicated constants files and replace all magic values:

| Location | Magic Value | Constants File |
|----------|-------------|----------------|
| `entities.py:28` | `"gpt-4"` | `domain/constants.py` |
| `entities.py:79` | `0.7`, `2048` | `domain/constants.py` |
| `use_cases.py:110` | `5` (top_k) | `application/constants.py` |
| `use_cases.py:112` | `0.3` (threshold) | `application/constants.py` |
| `llm.py:20-40` | `"gpt-4"`, `0.7`, `2048` | `infrastructure/constants.py` |
| `embeddings.py:15` | `"text-embedding-3-small"` | `infrastructure/constants.py` |
| `vector_store.py:15` | `"default"` | `infrastructure/constants.py` |
| All files | `"You are a helpful assistant"` | `domain/constants.py: SYSTEM_PROMPT` |
| All files | `except Exception` | Replace with specific exception types |

**Gherkin**: Not applicable (refactoring, no behavior change)
**Tests**: All existing tests must continue passing
**Risk if deferred**: **MEDIUM** — scattered magic values make maintenance and configuration changes error-prone

---

### P2.3: Add Retry Logic, Timeouts, and Error Handling

**Backend** — Add retry with exponential backoff to:
- `infrastructure/llm.py:70` — LLM API calls
- `infrastructure/embeddings.py:30` — Embedding API calls
- `infrastructure/vector_store.py:50` — Vector store operations
- `infrastructure/database.py:60` — Database connections
- `infrastructure/reranker.py:30` — Reranker model loading

**Backend** — Replace `except Exception` (20+ locations) with specific exception types:
- `LLMAPIError`, `EmbeddingError`, `VectorStoreError`, `DatabaseError`, `StorageError`

**Gherkin**: `tests/features/resilience.feature` — new
```gherkin
Feature: Resilience and Retry Logic
  Scenario: LLM API call retries on transient failure
    Given the LLM provider returns a 503 error
    When a completion is requested
    Then the system retries up to 3 times with exponential backoff
    And returns a graceful error after all retries fail

  Scenario: Database connection pool exhaustion handled
    Given all database connections are in use
    When a query is attempted
    Then the system waits for a connection (with timeout)
    And returns a 503 if timeout is exceeded
```

**Tests**: `tests/unit/infrastructure/test_llm_retry.py`, `tests/unit/infrastructure/test_database_resilience.py`

---

### P2.4: Fix `formatRelativeTime` i18n

**Problem**: `lib/utils.ts:32-36` has hardcoded English strings for relative time formatting.

**Action**:
1. Add locale keys: `common.justNow`, `common.minutesAgo`, `common.hoursAgo`, `common.daysAgo` to both `en.json` and `pt.json`.
2. Modify `formatRelativeTime` to accept a `t` (translate) function parameter.
3. Update all callers to pass the i18n translate function.

**Gherkin**: Update `tests/features/home.feature`
```gherkin
Scenario: Relative time respects locale
  Given the current locale is "pt"
  When a post was created 2 minutes ago
  Then the relative time shows "há 2 minutos"
```

**Tests**: `tests/unit/lib/utils.test.ts` — update existing tests
**Risk if deferred**: **LOW** — Portuguese users see English time strings

---

### P2.5: Replace Hardcoded CSS with CSS Variables in Admin/Login

**Files**:
- `login/page.tsx` — `bg-indigo-*`, `text-gray-900`
- `admin/layout.tsx` — `bg-gray-50`
- `admin/users/page.tsx` — `bg-indigo-*`, `text-gray-900`
- All admin dialogs — hardcoded Tailwind colors

**Action**: Replace hardcoded color classes with CSS variable-based tokens:
- `bg-indigo-600` → `bg-primary`
- `text-indigo-600` → `text-primary`
- `text-gray-900` → `text-foreground`
- `bg-gray-50` → `bg-background`

**Gherkin**: Update admin feature file
```gherkin
Scenario: Admin pages respect dark mode
  Given dark mode is enabled
  When I navigate to the admin users page
  Then all text has sufficient contrast against the dark background
```

**Risk if deferred**: **MEDIUM** — admin pages break in dark mode, inconsistent UX

---

## Phase 3 — Testing Coverage (Days 11-14)

### P3.1: Backend Coverage Gaps

| Component | Existing Tests | Required |
|-----------|---------------|----------|
| `infrastructure/llm.py` | None | `test_llm_provider_selection.py`, `test_llm_retry.py`, `test_llm_streaming.py` |
| `infrastructure/embeddings.py` | None | `test_embeddings_batch.py`, `test_embeddings_validation.py` |
| `infrastructure/vector_store.py` | None | `test_vector_store_crud.py`, `test_vector_store_search.py` |
| `infrastructure/storage.py` | None | `test_storage_security.py`, `test_storage_concurrency.py` |
| `infrastructure/search.py` | None | `test_search_types.py`, `test_search_fallback.py` |
| `infrastructure/reranker.py` | None | `test_reranker_fallback.py` |
| `infrastructure/audio.py` | None | `test_audio_validation.py` |
| `infrastructure/carousel_factory.py` | None | `test_carousel_factory_types.py` |
| `infrastructure/similarity.py` | None | `test_similarity_metrics.py` |
| `api/rate_limiter.py` | None | `test_rate_limiter_distributed.py` |
| `api/sse.py` | None | `test_sse_reconnection.py` |
| `agents/carousel.py` | None | `test_carousel_graph_validation.py` |
| `agents/crew.py` | None | `test_agent_creation.py`, `test_agent_timeout.py` |
| `agents/tools.py` | None | `test_tool_validation.py` |
| `agents/nodes.py` | None | `test_node_retry.py`, `test_node_output_validation.py` |
| `agents/research.py` | None | `test_research_depth.py` |

---

### P3.2: Frontend Coverage Gaps

| Component | Existing Tests | Required |
|-----------|---------------|----------|
| All 7 admin components | 0 | `test_create_user_dialog.tsx`, `test_edit_user_dialog.tsx`, `test_delete_user_dialog.tsx`, `test_change_password_dialog.tsx`, `test_user_table.tsx`, `test_role_badge.tsx`, `test_admin_sidebar.tsx` |
| `publish-panel.tsx` | 0 | `test_publish_instagram_tab.tsx`, `test_publish_linkedin_tab.tsx`, `test_publish_character_count.tsx`, `test_publish_bilingual.tsx` |
| `use-carousel.ts` | Partial | `test_carousel_phase_lifecycle.ts`, `test_carousel_sse_reconnect.ts` |
| `carousel-preview.tsx` | 0 | `test_carousel_preview_rendering.tsx` |
| `carousel-progress.tsx` | 0 | `test_carousel_progress_states.tsx` |
| `topic-form.tsx` | 0 | `test_topic_form_validation.tsx` |
| `horizontal-carousel-viewer.tsx` | 0 | `test_carousel_viewer_navigation.tsx` |
| `role-badge.tsx` | 0 | `test_role_badge_i18n.tsx` |

---

### P3.3: Gherkin-to-Test Traceability Matrix

Current gap: 13 Gherkin feature files, but many scenarios lack test implementations.

| Feature File | Scenarios | Implemented Tests | Gap |
|-------------|-----------|-------------------|-----|
| `auth.feature` | 8 | Partial (E2E only) | Missing admin CRUD unit tests |
| `chat.feature` | 8 | 4 E2E | Missing 4 unit tests |
| `admin.feature` | 8 | 0 | No test implementation at all |
| `blog.feature` | 14 | Partial | Missing 6-8 unit tests |
| `knowledge.feature` | 7 | 4 E2E | Missing 3 unit tests |
| `publish.feature` | 10 | 0 | No test implementation at all |
| `header_public_chat.feature` | 8 | 1 unit | Missing 7 tests |
| `carousel_content_generation.feature` | 12 | 2 backend | Missing 10 tests |
| `agent_split/` features | 10 | Partial | Missing 5 tests |

**Action**: For every Gherkin scenario without a corresponding test, add `// Gherkin: <feature_file>:<line>` comment referencing the scenario, then implement the test.

---

## Phase 4 — Infrastructure Hardening (Days 15-18)

### P4.1: Docker Security Hardening

| Action | Files | Priority |
|--------|-------|----------|
| Add custom Docker network with `docker network create alter-ego-net` | `docker-compose*.yml` | HIGH |
| Remove PostgreSQL port exposure in dev compose | `docker-compose.yml:9` | MEDIUM |
| Add `restart: unless-stopped` to all services | `docker-compose*.yml` | MEDIUM |
| Add resource limits (`mem_limit`, `cpus`) | `docker-compose*.yml` | MEDIUM |
| Add healthchecks to PostgreSQL, Redis, backend | `docker-compose*.yml` | MEDIUM |
| Add `USER` directive to both Dockerfiles | `backend/Dockerfile`, `frontend/Dockerfile` | HIGH |
| Add `.dockerignore` files | `backend/.dockerignore`, `frontend/.dockerignore` | LOW |
| Pin `appleboy/ssh-action` to commit SHA | `.github/workflows/deploy.yml` | MEDIUM |

### P4.2: CI/CD Hardening

| Action | Files | Priority |
|--------|-------|----------|
| Create `frontend-quality-gates.yml` | `.github/workflows/` | HIGH |
| Create `.github/dependabot.yml` | `.github/` | MEDIUM |
| Add Docker layer caching to deploy workflow | `.github/workflows/deploy.yml` | MEDIUM |
| Replace inline secret interpolation with environment files | `.github/workflows/deploy.yml` | HIGH |
| Add `git stash` before `git reset --hard` for safe deploy | `.github/workflows/deploy.yml` | MEDIUM |
| Add `radon mi` and `xenon` quality gates for backend | `.github/workflows/backend-quality-gates.yml` | LOW |
| Add `pytest-archon` architectural boundary tests | `backend/tests/` | LOW |

### P4.3: Create `.env.example`

**Action**: Create `.env.example` with all required environment variables (empty values, documented):
```
# LLM Providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=

# Vector Store
PINECONE_API_KEY=
PINECONE_ENVIRONMENT=
PINECONE_INDEX_NAME=

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/alterego

# Auth
SECRET_KEY=
ANON_SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000

# Feature Flags
DISABLE_DOCS=false
```

---

## Phase 5 — LangFuse Observability Platform (Days 17-22)

### P5.0: Why LangFuse

[LangFuse](https://langfuse.com) is an open-source LLM observability platform (alternative to LangSmith) that provides:

- **Tracing**: Full trace trees of LLM calls, tool usage, retrievals, agent orchestration — all nested in a single trace per carousel/chat
- **LangGraph Visualization**: Agent graphs rendered in the UI showing the exact node execution path
- **Session Tracking**: Group multi-turn conversations into sessions (carousel creation flow, chat history)
- **Prompt Management**: Version-controlled prompts deployable without code changes
- **User Tracking**: Per-user cost and latency monitoring
- **Evaluation**: LLM-as-a-judge, human feedback, custom scoring
- **Self-Hostable**: Docker Compose deployment with PostgreSQL, ClickHouse, Redis, S3

### P5.1: Self-Host LangFuse Infrastructure

**Architecture**: LangFuse requires 3 backing services + 2 app containers. All observability data (traces, observations, scores) lives in ClickHouse — no S3/Minio needed.

```
langfuse-web     → Web UI + API (port 3000)
langfuse-worker  → Async event processor
postgres         → Transactional data (users, projects, prompts)
clickhouse       → OLAP observability data (traces, observations, scores)
redis            → Queue + cache
```

**Data retention**: LangFuse stores all trace data in ClickHouse with TTL-based auto-deletion. Traces older than the retention window are purged automatically at the ClickHouse partition level (zero-copy, no manual cleanup). No local files to manage.

**Action**: Add LangFuse services to `docker-compose.yml` and `docker-compose.prod.yml`:

```yaml
services:
  langfuse-postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: langfuse
      POSTGRES_USER: langfuse
      POSTGRES_PASSWORD: ${LANGFUSE_POSTGRES_PASSWORD}
    volumes:
      - langfuse_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langfuse"]
      interval: 10s

  langfuse-redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  langfuse-clickhouse:
    image: clickhouse/clickhouse-server:24.3-alpine
    environment:
      CLICKHOUSE_DB: langfuse
      CLICKHOUSE_USER: langfuse
      CLICKHOUSE_PASSWORD: ${LANGFUSE_CLICKHOUSE_PASSWORD}
    volumes:
      - langfuse_clickhouse_data:/var/lib/clickhouse

  langfuse-web:
    image: ghcr.io/langfuse/langfuse:latest
    depends_on:
      langfuse-postgres: { condition: service_healthy }
      langfuse-redis: { condition: service_healthy }
      langfuse-clickhouse: { condition: service_started }
    environment:
      DATABASE_URL: postgresql://langfuse:${LANGFUSE_POSTGRES_PASSWORD}@langfuse-postgres:5432/langfuse
      REDIS_CONNECTION_STRING: redis://langfuse-redis:6379
      CLICKHOUSE_URL: http://langfuse-clickhouse:8123
      CLICKHOUSE_USER: langfuse
      CLICKHOUSE_PASSWORD: ${LANGFUSE_CLICKHOUSE_PASSWORD}
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET}
      NEXTAUTH_URL: ${LANGFUSE_BASE_URL}
      LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES: "true"
    ports:
      - "3001:3000"

  langfuse-worker:
    image: ghcr.io/langfuse/langfuse-worker:latest
    depends_on:
      langfuse-web: { condition: service_started }
    environment:
      DATABASE_URL: postgresql://langfuse:${LANGFUSE_POSTGRES_PASSWORD}@langfuse-postgres:5432/langfuse
      REDIS_CONNECTION_STRING: redis://langfuse-redis:6379
      CLICKHOUSE_URL: http://langfuse-clickhouse:8123
      CLICKHOUSE_USER: langfuse
      CLICKHOUSE_PASSWORD: ${LANGFUSE_CLICKHOUSE_PASSWORD}
```

**Data retention configuration**: Set ClickHouse TTL via LangFuse UI (Settings → Data Retention → set to 7 days) or via database migration:

```sql
-- LangFuse creates ClickHouse tables with TTL support.
-- Default retention is 30 days. Set to 7 days via UI or env:
ALTER TABLE langfuse.observations MODIFY TTL toDateTime(created_at) + INTERVAL 7 DAY;
ALTER TABLE langfuse.traces MODIFY TTL toDateTime(timestamp) + INTERVAL 7 DAY;
ALTER TABLE langfuse.scores MODIFY TTL toDateTime(timestamp) + INTERVAL 7 DAY;
```

After 7 days, traces are auto-purged by ClickHouse's TTL merge process — no manual cleanup, no cron jobs, no local disk filling up.

**Add to `.env.example`**:
```
# LangFuse Observability
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=http://localhost:3001
LANGFUSE_POSTGRES_PASSWORD=changeme
LANGFUSE_CLICKHOUSE_PASSWORD=changeme
LANGFUSE_NEXTAUTH_SECRET=generate-with-openssl-rand-64
LANGFUSE_RETENTION_DAYS=7
```

---

### P5.2: Backend LangFuse Integration — Python SDK

**Installation**:
```bash
uv add langfuse
```

**Initialization** (`infrastructure/observability.py` — new file):
```python
from langfuse import Langfuse, observe, get_client
from langfuse.langchain import CallbackHandler

langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    base_url=settings.LANGFUSE_BASE_URL,
)

langfuse_handler = CallbackHandler()

def get_langfuse_handler() -> CallbackHandler:
    return langfuse_handler

def verify_langfuse_connection() -> bool:
    try:
        return get_client().auth_check()
    except Exception:
        return False
```

**Add to application dependencies** (`application/dependencies.py`):
```python
def get_langfuse_handler() -> Generator[CallbackHandler, None, None]:
    yield langfuse_handler
```

---

### P5.3: Carousel Creation — Full Trace Tree

**Goal**: Every carousel creation produces a single trace showing:
```
TRACE: "Carousel: How Photosynthesis Works"
├── 🧠 research_topic           [span: LLM + Web Search]
│   ├── 🔍 search_web           [span: vector_store.similarity_search]
│   ├── 📄 rag_retrieval        [span: document_processor.parse]
│   └── 🤖 llm_summarize        [generation: gpt-4o]
├── 🎯 generate_carousel        [span: LangGraph agent]
│   ├── 🤖 create_outline       [generation: gpt-4o]
│   ├── 🎨 generate_images      [span: DALL-E 3]
│   │   ├── 🖼️ image_1_slide1   [generation: dall-e-3]
│   │   ├── 🖼️ image_2_slide2   [generation: dall-e-3]
│   │   └── 🖼️ image_3_slide3   [generation: dall-e-3]
│   └── ✍️ write_slide_content  [generation: gpt-4o]
├── ✅ review_carousel          [span: human review]
├── 📤 export_carousel          [span: PDF builder]
│   ├── 📄 build_slides         [span: pdf_slide_builder.build]
│   └── 💾 save_to_storage      [span: storage.save]
└── 📢 publish_carousel         [span: social publisher]
    ├── 📷 instagram_upload     [span: instagram_api.post]
    └── 💼 linkedin_upload      [span: linkedin_api.post]
```

**Implementation** (`agents/carousel.py`):

```python
from langfuse import observe, get_client
from langfuse.langchain import CallbackHandler

@observe(as_type="trace")
async def create_carousel_trace(
    topic: str,
    user_id: str,
    session_id: str,
    langfuse_handler: CallbackHandler,
) -> CarouselResult:
    langfuse = get_client()

    langfuse.set_current_trace_io(
        input={"topic": topic},
    )

    with langfuse.start_as_current_observation(
        as_type="span", name="🔍 research_topic"
    ) as research_span:
        research = await research_topic(
            topic, callbacks=[langfuse_handler]
        )
        research_span.update(output={"findings_count": len(research.findings)})

    with langfuse.start_as_current_observation(
        as_type="span", name="🎯 generate_carousel"
    ) as gen_span:
        carousel = await carousel_graph.ainvoke(
            {"research": research},
            config={"callbacks": [langfuse_handler]},
        )
        gen_span.update(output={"slide_count": len(carousel.slides)})

    with langfuse.start_as_current_observation(
        as_type="span", name="📤 export_carousel"
    ) as export_span:
        pdf = await build_pdf(carousel)
        path = await storage.save(pdf)
        export_span.update(output={"path": str(path)})

    with langfuse.start_as_current_observation(
        as_type="span", name="📢 publish_carousel"
    ) as publish_span:
        result = await publish_to_social(carousel)
        publish_span.update(output={
            "instagram": result.instagram_status,
            "linkedin": result.linkedin_status,
        })

    langfuse.set_current_trace_io(
        output={"carousel_id": carousel.id, "slides": len(carousel.slides)},
    )

    return CarouselResult(carousel=carousel, pdf_path=path, publish_result=result)
```

---

### P5.4: Chat Conversation — Session Tracking

**Goal**: Each chat conversation is a LangFuse session, with every message exchange as a trace.

**Implementation** (`api/websocket.py`):

```python
from langfuse import get_client
from langfuse.langchain import CallbackHandler

async def handle_chat_message(
    websocket: WebSocket,
    message: ChatMessage,
    session_id: str,
    user_id: str | None,
):
    langfuse = get_client()
    langfuse_handler = CallbackHandler()

    trace_id = Langfuse.create_trace_id(seed=message.id)

    with langfuse.start_as_current_observation(
        as_type="span",
        name="💬 chat_message",
        trace_context={"trace_id": trace_id},
        session_id=session_id,
        user_id=user_id or "anonymous",
        tags=["chat"],
    ) as span:
        span.update(input={"message": message.content})

        response = await llm.ainvoke(
            message.to_langchain(),
            config={"callbacks": [langfuse_handler]},
        )

        span.update(output={"response": response.content})

        if message.feedback:
            langfuse.score(
                trace_id=trace_id,
                name="user-feedback",
                value=message.feedback.score,
                data_type="NUMERIC",
                comment=message.feedback.comment,
            )

    return response
```

---

### P5.5: LangGraph Auto-Instrumentation via `with_config`

**For the carousel agent graph** (`agents/carousel.py`):

```python
from langfuse.langchain import CallbackHandler

langfuse_handler = CallbackHandler()

carousel_graph = graph_builder.compile().with_config(
    {"callbacks": [langfuse_handler]}
)
```

This means every `carousel_graph.ainvoke(...)` automatically produces a nested trace tree in LangFuse showing:
- Each node execution (research, generate, review)
- Each LLM generation inside nodes
- Tool calls (web search, image generation)
- Retries and error paths
- Latency per node

---

### P5.6: LangFuse Dashboard and Alerting

**Set up in LangFuse UI** (self-hosted at `http://localhost:3001`):

1. **Project**: Create a project named `alter-ego`
2. **API Keys**: Generate `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`
3. **Dashboards**:
   - **Carousel Creation**: Latency P50/P95/P99, cost per carousel, success rate, image gen vs LLM time
   - **Chat**: Messages per session, average response time, user satisfaction score
   - **Cost**: Per-model spend (GPT-4o vs DALL-E vs embeddings), per-user cost
4. **LLM-as-a-Judge Evaluators**:
   - `carousel_quality`: Evaluate generated carousels for factual accuracy, structure, image relevance
   - `chat_helpfulness`: Score assistant responses for helpfulness
5. **Alerts** (via webhook → backend `/api/webhooks/langfuse`):
   - Latency P99 > 30s for carousel creation
   - Error rate > 5% for chat
   - Daily cost > threshold

---

### P5.7: Prompt Management with LangFuse

Replace hardcoded system prompts with LangFuse-managed prompts:

```python
from langfuse import get_client

def get_carousel_prompt() -> str:
    langfuse = get_client()
    prompt = langfuse.get_prompt("carousel_system_prompt", label="production")
    return prompt.get_langchain_prompt()
```

**Benefits**:
- Update prompts via UI without code deployment
- A/B test prompt versions using labels
- Rollback instantly to previous version
- Each prompt version is linked to traces showing performance

---

### P5.8: Health Check, Logging, Graceful Shutdown

**Health Check** — Add `GET /api/health` that includes LangFuse status:

```python
@router.get("/health")
async def health_check():
    langfuse_ok = verify_langfuse_connection()
    return {
        "status": "ok",
        "database": await check_db(),
        "vector_store": await check_pinecone(),
        "langfuse": "connected" if langfuse_ok else "unavailable",
        "version": VERSION,
        "uptime_seconds": int(time() - START_TIME),
    }
```

**Graceful Shutdown** — Ensure LangFuse events flush before exit:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.langfuse_initialized = verify_langfuse_connection()
    yield
    get_client().shutdown()
```

**Error Tracking** — Tag LangFuse traces on failures:

```python
try:
    result = await create_carousel_trace(...)
except Exception as e:
    langfuse_handler.trace.update(
        metadata={"error": str(e), "error_type": type(e).__name__}
    )
    raise
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation | Phase |
|------|-----------|--------|------------|-------|
| WebSocket token exfiltration | High | High | Move token to subprotocol | P0.1 |
| XSS via blog rendering | Medium | High | Remove duplicate component | P0.2 |
| Unauthenticated API access | Medium | High | Already mitigated (auth exists) | — |
| Secret exposure in logs | Medium | Medium | Use `SecretStr` | P1.3 |
| Path traversal in file storage | Low | High | Add path validation | P1.3 |
| Admin pages broken in dark mode | High | Low | Replace hardcoded CSS | P2.5 |
| Docker supply chain attack | Low | High | Pin action SHAs | P4.1 |
| LLM API cost spike | Medium | Medium | Add rate limiting at provider level | P1.1 |
| Database connection exhaustion | Medium | High | Add pool configuration | P2.3 |
| Zombie WebSocket connections | High | Low | Add heartbeat/ping | P1.1 |
| Pre-commit bypass | High | Medium | Wire husky | P0.3 |
| Frontend type errors merge | High | Medium | Add CI quality gates | P0.4 |
| LangFuse self-host infra complexity | Medium | Medium | Use pinned stable images, healthchecks, backup strategy | P5.1 |
| LangFuse TTL data loss if retention too short | Low | Low | Default 7 days, visible in UI, traces survive in ClickHouse until TTL merge | P5.1 |
| LangFuse event loss on flush failure | Low | Medium | Buffer to disk, retry on shutdown | P5.8 |

---

## Effort Estimates

| Phase | Days | Focus |
|-------|------|-------|
| Phase 0 — Firefighting | 2 | Security vulnerabilities, tooling, CI |
| Phase 1 — Security Hardening | 3 | CSP, auth refactor, secrets, production config |
| Phase 2 — Architecture & Code Quality | 5 | File splitting, constants, retry logic, i18n, CSS |
| Phase 3 — Testing Coverage | 4 | 30+ new test files, Gherkin traceability |
| Phase 4 — Infrastructure Hardening | 4 | Docker, CI/CD, .env.example |
| Phase 5 — LangFuse Observability | 6 | Self-host LangFuse, tracing, prompt mgmt, health checks |
| **Total** | **24 days** | |

---

## Quick Wins (Can Be Done in Parallel)

These items are low-risk, high-value and can be distributed across the team:

1. **Fix `formatRelativeTime` i18n** — 1 file, ~30 min
2. **Remove duplicate blog components** — ~1 hour
3. **Create `.env.example`** — ~15 min
4. **Add `USER` directive to Dockerfiles** — ~30 min each
5. **Add `.dockerignore` files** — ~15 min each
6. **Replace redundant re-exports** (`chat/types`, `knowledge/types`) — ~15 min
7. **Replace inline SVG with `lucide-react`** in `blog/page.tsx` — ~15 min
8. **Fix `robots.ts` placeholder domain** — ~5 min
9. **Fix pre-existing test failures** — ~2 hours
10. **Add Dependabot config** — ~15 min
