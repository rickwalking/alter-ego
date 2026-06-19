# Alter-Ego — unified polyglot task runner (AE-0195)
# Thin root entrypoint that delegates to the two stacks:
#   backend  = Python / uv   (backend/)
#   frontend = Node / npm     (frontend/)
# Kept deliberately simple — NOT npm/pnpm workspaces (JS-only) or Nx/Turborepo.
.DEFAULT_GOAL := help
.PHONY: help setup build test lint typecheck dev board \
        be-setup be-test be-lint be-typecheck \
        fe-setup fe-build fe-test fe-lint fe-typecheck

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: be-setup fe-setup ## Install deps for both stacks
build: fe-build ## Production build (frontend; backend builds via Docker)
test: be-test fe-test ## Run all tests (pytest + vitest)
lint: be-lint fe-lint ## Lint both stacks
typecheck: be-typecheck fe-typecheck ## Type-check both stacks

dev: ## Run the full stack (docker compose)
	docker compose up

board: ## Regenerate the local Kanban board from .agent/tasks/ (BOARD.md is generated, not committed)
	uv run python scripts/agent_tasks/render_board.py

# --- backend (uv) ---
be-setup: ; cd backend && uv sync
be-test: ; cd backend && uv run pytest
be-lint: ; cd backend && uv run ruff check src/
be-typecheck: ; cd backend/src && uv run mypy rag_backend/ --explicit-package-bases

# --- frontend (npm) ---
fe-setup: ; cd frontend && npm ci
fe-build: ; cd frontend && npm run build
fe-test: ; cd frontend && npm run test -- --run
fe-lint: ; cd frontend && npm run lint
fe-typecheck: ; cd frontend && npm run typecheck
