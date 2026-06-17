# Alter-Ego Documentation Index

This is the entry point for all Alter-Ego documentation. Docs are grouped by area
below. Architecture, guides, decisions, deployment, and research are the live /
evergreen references; the **Plans & history** section links shipped or superseded
plans kept as historical record.

See also the root [`CLAUDE.md`](../CLAUDE.md) for project-wide rules and the ADR list.

## Architecture

System architecture, API contracts, and module boundaries.

- [Backend Architecture](architecture/BACKEND_ARCHITECTURE.md)
- [Technical Specification](architecture/TECHNICAL_SPECIFICATION.md)
- [API Contract](architecture/API_CONTRACT.md)
- [Module Conventions](architecture/module-conventions.md)
- [Domain Glossary](architecture/domain-glossary.md)
- [Concurrency Contract](architecture/concurrency-contract.md)
- [Checkpoint Inventory](architecture/checkpoint-inventory.md)
- [SSE Event Inventory](architecture/sse-event-inventory.md)
- [Carousel Project Field Ownership](architecture/carousel-project-field-ownership.md)
- [Presentation Surface Ownership](architecture/presentation-surface-ownership.md)
- [Publishing Surface Ownership](architecture/publishing-surface-ownership.md)
- [Carousel Rollback Drill](architecture/carousel-rollback-drill.md)
- [Phase 0 Risk Register](architecture/phase-0-risk-register.md)
- [Adversarial Test Matrix](architecture/adversarial-test-matrix.md)
- [LangChain Deep Agents Guide](architecture/langchain-deep-agents-guide.md)
- [LangGraph Deep Agents Research Report](architecture/langgraph-deep-agents-research-report.md)
- [Original Project Proposal](architecture/PROPOSAL.md) *(superseded — historical)*

## Guides

Development, testing, and workflow guides.

- [QA Checkpoints](guides/qa-checkpoints.md)
- [CI Quality Gates](guides/ci-quality-gates.md)
- [Architectural Quality Enforcement](guides/architectural-quality-enforcement.md)
- [Ticket Writing Guide](guides/ticket-writing-guide.md)
- [Agentic Team Operating Model](guides/agentic-team-operating-model.md)
- [Kanban Agent Workflow](guides/kanban-agent-workflow.md)
- [Editorial Workflow User Guide](guides/editorial-workflow-user-guide.md)
- [Workflow Resume Failure Analysis](guides/workflow-resume-failure-analysis.md)
- [Langfuse Observability Guide](guides/LANGFUSE_OBSERVABILITY_GUIDE.md)
- [Vitest Testing Guide](guides/VITEST_TESTING_GUIDE.md)
- [Zod Validation Guide](guides/ZOD_VALIDATION_GUIDE.md)
- [React 2026 Best Practices](guides/react-2026-best-practices.md)
- [React Components Guide 2026](guides/react-components-guide-2026.md)
- [Style Guide 2026](guides/style-guide-2026.md)
- [Suspense Data Loading Guide](guides/suspense-data-loading-guide.md)
- [Minimizing useEffect Guide](guides/minimizing-useeffect-guide.md)
- [Carousel Closing Slide Style](guides/carousel-closing-slide-style.md)
- [Carousel Export Techniques](guides/carousel-export-techniques.md)

## Decisions (ADRs)

Architecture Decision Records (MADR 4.x).

- [ADR-0001: Adopt MADR for ADRs](decisions/0001-adopt-madr-for-adrs.md)
- [ADR-0002: Use LangGraph for Workflow Engine](decisions/0002-use-langgraph-for-workflow-engine.md)
- [ADR-0003: Implement Persona-Driven AI Content](decisions/0003-implement-persona-driven-ai-content.md)
- [ADR-0004: Adopt Event-Driven Architecture](decisions/0004-adopt-event-driven-architecture.md)
- [ADR-0005: Adopt Mutation Testing](decisions/0005-adopt-mutation-testing.md)
- [ADR-0006: Use JSONB for Rich Content](decisions/0006-use-jsonb-for-rich-content.md)
- [ADR-0007: Consolidate Carousel Pipelines Under DeepAgents](decisions/0007-consolidate-carousel-pipelines-under-deepagents.md)
- [ADR-0008: Agentic Delivery Workflow](decisions/0008-agentic-delivery-workflow.md)
- [ADR-0009: Adopt Domain Modular Monolith](decisions/0009-adopt-domain-modular-monolith.md)
- [ADR-0010: Suspense Data Loading](decisions/0010-suspense-data-loading.md)

## Deployment

- [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)
- [Staging Deploy](deployment/STAGING_DEPLOY.md)
- [Docker Compose Commands](deployment/docker-compose.commands.md)

## Backend

- [Quality Enforcement](backend/QUALITY_ENFORCEMENT.md)
- [Carousel Pipeline Plan](backend/carousel-pipeline-plan.md)

## Security

- [Security & Admin Panel Reference](SECURITY_IMPLEMENTATION_PLAN.md) *(implemented)*

## Research

- [Backend Quality Synthesis](research/backend-quality-synthesis.md)
- [CI/CD Quality Gates (Python)](research/cicd-quality-gates-python.md)
- [Content Platform Architecture Patterns](research/content-platform-architecture-patterns.md)

## Frontend

- [Phase 7 Baseline](frontend/phase-7-baseline.md)

## Operations & Maintenance

- [Technical Debt](TECHNICAL_DEBT.md)
- [WebSocket / Cloudflare Debug Record](cloudflare-ws-debug.md) *(superseded — historical)*

## Plans & History

Shipped phase plans (`Status: Done`) and superseded historical plans kept for the record.

### Domain modularization phases

- [Phase 0 — Domain Modularization](plans/domain-modularization-phase0.md)
- [Phase 1 — Architecture Scaffolding](plans/phase-1-architecture-scaffolding.md) *(done)*
- [Phase 2 — Knowledge Module](plans/phase-2-knowledge-module.md) *(done)*
- [Phase 3 — Identity & Conversation](plans/phase-3-identity-conversation.md) *(done)*
- [Phase 4 — Editorial Carousel](plans/phase-4-editorial-carousel.md) *(done)*
- [Phase 5 — Presentation](plans/phase-5-presentation.md) *(done)*
- [Phase 6 — Publishing, Blog & Distribution](plans/phase-6-publishing-blog-distribution.md) *(done)*
- [Phase 7 — Frontend Alignment](plans/phase-7-frontend-alignment.md)
- [Phase 8 — Legacy Removal](plans/phase-8-legacy-removal.md)

### Agentic delivery

- [Agentic Delivery System (overview)](plans/agentic-delivery-system.md)
- [Agentic Delivery System — Implementation Plan](plans/agentic-delivery-system-implementation-plan.md) *(implemented)*
- [Original Agentic Delivery System Plan](plans/alter_ego_agentic_delivery_system_plan.md) *(superseded — historical)*

### Carousel & content

- [Carousel Pipeline Consolidation](plans/carousel-pipeline-consolidation.md)
- [Carousel Slide Layout Strategies](plans/carousel-slide-layout-strategies.md)
- [Carousel Style Improvements](plans/carousel-style-improvements.md)
- [Carousel Agent Improvement Plan](plans/carousel-agent-improvement-plan.md) *(superseded — historical)*
- [Carousel Editorial & Publish Fixes](plans/carousel-editorial-publish-fixes.md) *(superseded — historical)*
- [Carousel HD Export](plans/carousel-hd-export.md) *(superseded — historical)*
- [Image Phase Resilience & Prompt Review](plans/image-phase-resilience-and-prompt-review.md) *(superseded — historical)*
- [Editorial Workflow Resume Gap](plans/editorial-workflow-resume-gap.md) *(superseded — historical)*

### UI / shell

- [Frontend Legacy Removal](plans/frontend-legacy-removal.md)
- [Landing Page CSS Effects & Responsive](plans/landing-page-css-effects-responsive.md)
- [Neon Dashboard Backend Integration](plans/neon-dashboard-backend-integration.md)
- [Public Shell UX Fixes](plans/public-shell-ux-fixes.md)
- [Public Chat & Create Workflow Fixes](plans/public-chat-and-create-workflow-fixes.md) *(superseded — historical)*
- [Neon Shell Migration Complete](plans/neon-shell-migration-complete.md) *(superseded — historical)*
- [SSE Migration v2](plan-sse-migration-v2.md) *(superseded — historical)*

### Refactoring & remediation

- [AE-0040 PR #11 Quality & Architecture Refactoring](plans/ae-0040-pr11-quality-architecture-refactoring.md) *(superseded — historical)*
- [AE-0040 Rollback Plan](rollback/ae-0040-rollback.md) *(superseded — historical)*
- [Backend Agentic Refactor Plan](backend/AGENTIC_REFACTOR_PLAN.md) *(superseded — historical)*
- [Backend Implementation Plan](backend/BACKEND_IMPLEMENTATION_PLAN.md) *(superseded — historical)*
- [Professional Pivot Plan](PROFESSIONAL_PIVOT_PLAN.md) *(superseded — historical)*
- [Assessment Remediation Plan](assessment/REMEDIATION_PLAN.md) *(superseded — historical)*
