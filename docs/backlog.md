# Engineering Backlog

This backlog collects cross-cutting or future action items that emerge from reviews and planning.

Routing guidance:

- Use this file for non-urgent optimizations, refactors, or follow-ups that span multiple stories/epics.
- Must-fix items to ship a story belong in that story's `Tasks / Subtasks`.
- Same-epic improvements may also be captured under the epic Tech Spec `Post-Review Follow-ups` section.

| Date | Story | Epic | Type | Severity | Owner | Status | Notes |
| ---- | ----- | ---- | ---- | -------- | ----- | ------ | ----- |
| 2025-11-02 | 1.1 | 1 | TechDebt | Low | TBD | Open | Add null check on OpenAI response content (backend/app/services/openai_service.py:53) |
| 2025-11-02 | 1.1 | 1 | TechDebt | Low | TBD | Open | Replace generic Exception with specific openai.OpenAIError handling (backend/app/services/openai_service.py:55) |
| 2025-11-02 | 1.1 | 1 | TechDebt | Low | TBD | Open | Add max_length validation to ChatRequest.message field - suggest 2000 chars (backend/app/api/routes.py:10) |
| 2025-11-02 | 1.1 | 1 | TechDebt | Low | TBD | Open | Consider raising exception instead of silent fallback for missing knowledge base in production (backend/app/services/openai_service.py:17-19) |
| 2025-11-02 | 1.1 | 1 | Enhancement | Low | TBD | Open | Add rate limiting middleware (slowapi) for production deployment (backend/app/main.py) |
| 2025-11-02 | 1.1 | 1 | TechDebt | Low | TBD | Open | Tighten CORS allow_methods to ["GET", "POST"] instead of ["*"] (backend/app/main.py:20) |
| 2025-11-02 | 1.1 | 1 | TechDebt | Low | TBD | Open | Remove poetry.lock from .gitignore and commit it for reproducibility (.gitignore:27) |
| 2025-11-02 | 1.1 | 1 | Testing | Medium | TBD | Open | Add pytest and configure testing framework (poetry add --group dev pytest pytest-asyncio pytest-cov) |
| 2025-11-02 | 1.1 | 1 | Testing | Medium | TBD | Open | Add unit tests for get_chat_response with mocked OpenAI client (test_openai_service.py) |
| 2025-11-02 | 1.1 | 1 | Testing | Medium | TBD | Open | Add unit tests for ChatRequest/ChatResponse Pydantic models (test_models.py) |
| 2025-11-02 | 1.1 | 1 | Testing | Medium | TBD | Open | Add integration tests for POST /api/chat endpoint with test fixtures (test_routes.py) |
| 2025-11-02 | 1.1 | 1 | Testing | Medium | TBD | Open | Add unit tests for Settings configuration loading (test_settings.py) |
| 2025-11-02 | 1.1 | 1 | Testing | Medium | TBD | Open | Add edge case tests: empty messages, very long messages, special characters, concurrent requests |
| 2025-11-02 | 1.1 | 1 | Testing | Low | TBD | Open | Add tests for error handling scenarios: invalid API key, OpenAI API failures, network timeouts |
