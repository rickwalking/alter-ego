# bootstrap/ — Composition Root

**Purpose:** the single composition root for the backend. This is where the
dependency-injection container is constructed and the FastAPI application is
assembled and wired together.

Per [ADR-0009](../../../../../docs/decisions/0009-adopt-domain-modular-monolith.md)
§9, dependency injection is **manual constructor injection** (no DI framework
in new code) and the composition root lives here.

## What belongs here

- Application factory / app assembly wiring (`create_app`)
- DI container construction and lifecycle wiring
- Lifespan startup/shutdown orchestration that stitches subsystems together

## What does NOT belong here

- Domain, application, or infrastructure business logic
- Route handlers (they stay under `api/routes/`)
- Schemas, services, repositories, adapters

## Current contents

- `app_factory.py` — the FastAPI application factory (`create_app`) and its
  middleware/route/lifespan wiring, relocated from `api/app.py` in AE-0080.
  `api/app.py` remains as a thin re-export shim so existing imports
  (`from rag_backend.api.app import create_app`) keep working unchanged.
