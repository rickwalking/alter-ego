"""FastAPI application factory with lifespan management.

Composition root (ADR-0009 §9): this module assembles the FastAPI application
and wires its middleware, routes, lifespan, container, and checkpointer. It was
relocated from ``rag_backend.api.app`` with zero behavior change;
``rag_backend.api.app`` re-exports ``create_app`` for backward compatibility.

The HTTP router stays off the package facade: model registration imports the facade, and
the router imports the shared slowapi limiter under ``rag_backend.api``, so pulling it
through the facade would make infrastructure depend on the API layer.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rag_backend.agents.harness import build_checkpointer
from rag_backend.api.middleware.carousel_conflict_handler import (
    add_carousel_conflict_handler,
)
from rag_backend.api.middleware.error_handlers import add_error_handlers
from rag_backend.api.middleware.no_cors_job_inputs import NoCorsOnJobInputsMiddleware
from rag_backend.api.middleware.rate_limiting import setup_rate_limiting
from rag_backend.api.middleware.request_logging import RequestLoggingMiddleware
from rag_backend.api.middleware.security_headers import SecurityHeadersMiddleware
from rag_backend.api.routes import (
    admin,
    admin_migration,
    auth,
    blog_generate,
    blog_post,
    blog_post_ai,
    blog_post_comments,
    blog_post_images,
    blog_post_quality,
    blog_post_schedule,
    blog_post_sections,
    blog_post_versions,
    blog_post_workflow,
    carousels,
    chat_stream,
    content_calendar,
    conversations,
    document_scope,
    documents,
    image_bridge_inputs,
    manual_reprocess,
    notifications,
    palettes,
    personas,
    public_blog_post,
    rubrics,
    search,
    sources,
    workflow_audit,
    workflow_board,
)
from rag_backend.api.schemas import HealthCheckResponse, HealthResponse
from rag_backend.application.services.blog.blog_generation_runner import (
    cancel_blog_generation_tasks,
)
from rag_backend.application.services.chat_turns import drain_detached_turns
from rag_backend.application.workers.workflow_workers import (
    WorkflowWorkerServices,
    run_workflow_workers,
)
from rag_backend.bootstrap.autopilot_worker_factory import (
    autopilot_engine_factory,
    build_autopilot_worker_steps,
)
from rag_backend.bootstrap.blog_generation import build_blog_generation_reaper
from rag_backend.bootstrap.generation_queue_web import (
    check_generation_queue,
    start_progress_relay,
    start_queue_monitor,
)
from rag_backend.bootstrap.observability import init_observability
from rag_backend.bootstrap.startup_validation import run_startup_validations
from rag_backend.domain.clock import utc_now
from rag_backend.domain.constants.chat_stream import DETACHED_TURN_DRAIN_SECONDS
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.container import container
from rag_backend.infrastructure.database.carousel_auto_archiver import (
    CarouselIdleArchiver,
)
from rag_backend.infrastructure.database.config import close_db, init_db
from rag_backend.infrastructure.database.workflow_timeout_repository import (
    WorkflowTimeoutRepository,
)
from rag_backend.infrastructure.logging import get_logger
from rag_backend.infrastructure.telemetry.opentelemetry import instrument_fastapi
from rag_backend.modules.autopilot import prepare_instagram_credentials
from rag_backend.modules.autopilot.api.insights import (
    router as instagram_insights_router,
)
from rag_backend.modules.autopilot.api.queue_board import router as queue_board_router
from rag_backend.modules.autopilot.api.router import router as autopilot_router
from rag_backend.modules.autopilot.api.telegram_webhook import (
    router as telegram_webhook_router,
)
from rag_backend.modules.autopilot.webhook_constants import APP_STATE_ENGINE
from rag_backend.modules.image_bridge.api.router import router as image_bridge_router

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Initialize database on startup
    - Close database connections on shutdown

    Startup validations (durable checkpointer, default image-provider key) run before
    wiring and DB setup so a misconfigured production deploy fails fast; dev and test
    only warn. The carousel checkpointer is lifecycle-managed by an ``AsyncExitStack``
    so its DB connection closes on shutdown; ``settings.carousel_checkpoint_backend``
    selects sqlite (dev), postgres (prod), memory (ephemeral) or disabled (no resume).
    On shutdown, in-flight blog runs mark their rows recoverable-failed.

    Carousel generation runs in the generation worker: this loop keeps
    only the light steps, and the progress relay brings the worker's SSE events in.
    """
    settings = get_settings()
    init_observability(settings)

    logger.info("application_startup", version=settings.app_version)

    run_startup_validations(settings)

    await init_db(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    await prepare_instagram_credentials(settings)

    container.wire(packages=["rag_backend.api"])

    async with AsyncExitStack() as stack:
        app.state.carousel_checkpointer = await build_checkpointer(settings, stack)
        engine_factory = autopilot_engine_factory(app.state.carousel_checkpointer)
        setattr(app.state, APP_STATE_ENGINE, engine_factory)
        autopilot = build_autopilot_worker_steps(settings, engine_factory)
        worker_stop = asyncio.Event()
        worker_task = asyncio.create_task(
            run_workflow_workers(
                settings,
                worker_stop,
                WorkflowWorkerServices(
                    auto_rejector_factory=WorkflowTimeoutRepository,
                    blog_generation_reaper=build_blog_generation_reaper(settings),
                    carousel_auto_archiver=CarouselIdleArchiver(
                        settings.workflow_run_heartbeat_stale_seconds
                    ),
                    instagram_publish=autopilot.instagram_publish,
                    credential_refresh=autopilot.credential_refresh,
                    telegram_notify=autopilot.telegram_notify,
                ),
            )
        )
        relay_task = start_progress_relay(engine_factory, worker_stop)
        monitor_task = start_queue_monitor(settings, worker_stop)
        app.state.workflow_worker_stop = worker_stop
        app.state.workflow_worker_task = worker_task

        yield

        worker_stop.set()
        await worker_task
        await relay_task
        await monitor_task
        await cancel_blog_generation_tasks()

    logger.info("application_shutdown")
    await drain_detached_turns(DETACHED_TURN_DRAIN_SECONDS)
    await close_db()


async def _check_database(checks: dict[str, dict[str, str | int]]) -> None:
    """Check database connectivity and update checks dict."""
    try:
        from rag_backend.infrastructure.database.config import c_engine

        if c_engine:
            async with c_engine.connect() as conn:
                await conn.execute(
                    __import__("sqlalchemy").select(__import__("sqlalchemy").literal(1))
                )
            checks["database"] = {"status": "connected"}
        else:
            checks["database"] = {"status": "not_initialized"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}


def _check_pinecone(
    checks: dict[str, dict[str, str | int]], settings: Settings
) -> None:
    """Check Pinecone connectivity and update checks dict."""
    try:
        if settings.pinecone_api_key.get_secret_value():
            from pinecone import Pinecone

            pc = Pinecone(api_key=settings.pinecone_api_key.get_secret_value())
            indexes = pc.list_indexes()
            checks["pinecone"] = {
                "status": "connected",
                "index_count": len(list(indexes)),
            }
        else:
            checks["pinecone"] = {"status": "not_configured"}
    except Exception as e:
        checks["pinecone"] = {"status": "error", "detail": str(e)}


async def _check_openai(
    checks: dict[str, dict[str, str | int]], settings: Settings
) -> None:
    """Check OpenAI connectivity and update checks dict."""
    try:
        if settings.openai_api_key.get_secret_value():
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
            await client.models.list()
            checks["openai"] = {"status": "connected"}
        else:
            checks["openai"] = {"status": "not_configured"}
    except Exception as e:
        checks["openai"] = {"status": "error", "detail": str(e)}


def _setup_middleware(app: FastAPI, settings: Settings) -> None:
    """Configure all middleware on the app."""
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    if settings.debug:
        allowed_origins = ["*"]
    else:
        allowed_origins = (
            settings.allowed_origins.split(",") if settings.allowed_origins else ["*"]
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    )
    app.add_middleware(NoCorsOnJobInputsMiddleware)
    setup_rate_limiting(app, settings)


def _register_routes(app: FastAPI) -> None:
    """Register all route handlers on the app.

    The blog generation entry points register before the blog CRUD routes.
    """
    app.include_router(auth.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(admin_migration.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(document_scope.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(carousels.router, prefix="/api")
    app.include_router(blog_generate.router, prefix="/api")
    app.include_router(blog_post.router, prefix="/api")
    app.include_router(public_blog_post.router, prefix="/api")
    app.include_router(blog_post_ai.router, prefix="/api")
    app.include_router(blog_post_workflow.router, prefix="/api")
    app.include_router(blog_post_schedule.router, prefix="/api")
    app.include_router(blog_post_images.router, prefix="/api")
    app.include_router(blog_post_sections.router, prefix="/api")
    app.include_router(blog_post_versions.router, prefix="/api")
    app.include_router(blog_post_comments.router, prefix="/api")
    app.include_router(blog_post_quality.router, prefix="/api")
    app.include_router(personas.router, prefix="/api")
    app.include_router(rubrics.router, prefix="/api")
    app.include_router(sources.router, prefix="/api")
    app.include_router(notifications.router, prefix="/api")
    app.include_router(content_calendar.router, prefix="/api")
    app.include_router(palettes.router, prefix="/api")
    app.include_router(workflow_audit.router, prefix="/api")
    app.include_router(workflow_board.router, prefix="/api")
    app.include_router(chat_stream.router, prefix="/api")
    app.include_router(autopilot_router, prefix="/api")
    app.include_router(instagram_insights_router, prefix="/api")
    app.include_router(queue_board_router, prefix="/api")
    app.include_router(manual_reprocess.router, prefix="/api")
    app.include_router(telegram_webhook_router, prefix="/api")
    app.include_router(image_bridge_router, prefix="/api")
    app.include_router(image_bridge_inputs.router, prefix="/api")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        redirect_slashes=False,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    _setup_middleware(app, settings)

    @app.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            timestamp=utc_now(),
        )

    @app.get("/health/ready", response_model=HealthCheckResponse)
    async def readiness_check() -> HealthCheckResponse:
        checks: dict[str, dict[str, str | int]] = {}
        await _check_database(checks)
        await check_generation_queue(checks)
        _check_pinecone(checks, settings)
        await _check_openai(checks, settings)

        has_error = any(v.get("status") == "error" for v in checks.values())
        overall_status = "unhealthy" if has_error else "ready"

        return HealthCheckResponse(
            status=overall_status,
            version=settings.app_version,
            timestamp=utc_now(),
            checks=checks,
        )

    _register_routes(app)
    add_carousel_conflict_handler(app)
    add_error_handlers(app)

    instrument_fastapi(app)

    return app
