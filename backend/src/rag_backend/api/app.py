"""FastAPI application factory with lifespan management."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from rag_backend.api.middleware.error_handlers import add_error_handlers
from rag_backend.api.middleware.rate_limiting import setup_rate_limiting
from rag_backend.api.middleware.request_logging import RequestLoggingMiddleware
from rag_backend.api.middleware.security_headers import SecurityHeadersMiddleware
from rag_backend.api.routes import (
    admin,
    admin_migration,
    auth,
    blog_post,
    blog_post_ai,
    blog_post_comments,
    blog_post_quality,
    blog_post_versions,
    blog_post_workflow,
    carousels,
    chat_stream,
    content_calendar,
    conversations,
    documents,
    notifications,
    personas,
    rubrics,
    search,
    sources,
    workflow_audit,
    workflow_board,
)
from rag_backend.api.schemas import HealthCheckResponse, HealthResponse
from rag_backend.application.workers.workflow_workers import run_workflow_workers
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.container import container
from rag_backend.infrastructure.database.config import close_db, init_db
from rag_backend.infrastructure.langfuse_client import init_langfuse
from rag_backend.infrastructure.logging import get_logger, setup_logging
from rag_backend.infrastructure.monitoring import init_langsmith
from rag_backend.infrastructure.telemetry.opentelemetry import (
    init_opentelemetry,
    instrument_fastapi,
)

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Initialize database on startup
    - Close database connections on shutdown
    """
    settings = get_settings()
    setup_logging(debug=settings.debug)
    init_langsmith(settings)
    init_opentelemetry(
        service_name=settings.otel_service_name,
        exporter_endpoint=settings.otel_exporter_endpoint,
        enabled=settings.otel_enabled,
    )
    langfuse_handler = init_langfuse(
        settings.langfuse_public_key,
        settings.langfuse_secret_key.get_secret_value()
        if settings.langfuse_secret_key
        else "",
        settings.langfuse_host,
    )
    if langfuse_handler:
        logger.info("langfuse_initialized", host=settings.langfuse_host)

    logger.info("application_startup", version=settings.app_version)

    await init_db(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )

    container.wire(packages=["rag_backend.api"])

    # Carousel LangGraph checkpointer — lifecycle-managed by an
    # AsyncExitStack so the DB connection closes on shutdown. The
    # backend is selected via `settings.carousel_checkpoint_backend`:
    # sqlite (dev), postgres (prod), memory (ephemeral), disabled (no resume).
    async with AsyncExitStack() as stack:
        app.state.carousel_checkpointer = await _build_checkpointer(settings, stack)
        worker_stop = asyncio.Event()
        worker_task = asyncio.create_task(run_workflow_workers(settings, worker_stop))
        app.state.workflow_worker_stop = worker_stop
        app.state.workflow_worker_task = worker_task

        yield

        worker_stop.set()
        await worker_task

    logger.info("application_shutdown")
    await close_db()


async def _build_checkpointer(
    settings: Settings, stack: AsyncExitStack
) -> BaseCheckpointSaver | None:
    """Construct the configured checkpointer, registering cleanup on the stack."""
    backend = settings.carousel_checkpoint_backend.lower()

    if backend == "disabled":
        return None
    if backend == "memory":
        return InMemorySaver()
    if backend == "postgres":
        if not settings.carousel_checkpoint_postgres_url:
            logger.warning(
                "carousel_checkpoint_postgres_missing_url",
                hint="set carousel_checkpoint_postgres_url or switch backend",
            )
            return None
        saver_pg = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(
                settings.carousel_checkpoint_postgres_url
            )
        )
        await saver_pg.setup()  # idempotent DDL for checkpoint tables
        return saver_pg
    if not settings.carousel_checkpoint_sqlite_path:
        return InMemorySaver()
    try:
        Path(settings.carousel_checkpoint_sqlite_path).parent.mkdir(
            parents=True, exist_ok=True
        )
        return await stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(settings.carousel_checkpoint_sqlite_path)
        )
    except Exception:
        logger.warning(
            "carousel_checkpoint_sqlite_fallback",
            hint="sqlite path not available, using memory",
        )
        return InMemorySaver()


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

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # CORS middleware
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

    # Rate limiting
    setup_rate_limiting(app, settings)

    # Health check endpoint
    @app.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            timestamp=datetime.utcnow(),
        )

    # Detailed health check with dependency status
    @app.get("/health/ready", response_model=HealthCheckResponse)
    async def readiness_check() -> HealthCheckResponse:
        checks: dict[str, dict[str, str | int]] = {}

        # Check database
        try:
            from rag_backend.infrastructure.database.config import c_engine

            if c_engine:
                async with c_engine.connect() as conn:
                    await conn.execute(
                        __import__("sqlalchemy").select(
                            __import__("sqlalchemy").literal(1)
                        )
                    )
                checks["database"] = {"status": "connected"}
            else:
                checks["database"] = {"status": "not_initialized"}
        except Exception as e:
            checks["database"] = {"status": "error", "detail": str(e)}

        # Check Pinecone
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

        # Check OpenAI
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

        # Determine overall status
        has_error = any(v.get("status") == "error" for v in checks.values())
        overall_status = "unhealthy" if has_error else "ready"

        return HealthCheckResponse(
            status=overall_status,
            version=settings.app_version,
            timestamp=datetime.utcnow(),
            checks=checks,
        )

    # API routes
    app.include_router(auth.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(admin_migration.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(carousels.router, prefix="/api")

    # New Phase 1 routes
    app.include_router(blog_post.router, prefix="/api")
    app.include_router(blog_post_ai.router, prefix="/api")
    app.include_router(blog_post_workflow.router, prefix="/api")
    app.include_router(blog_post_versions.router, prefix="/api")
    app.include_router(blog_post_comments.router, prefix="/api")
    app.include_router(blog_post_quality.router, prefix="/api")
    app.include_router(personas.router, prefix="/api")
    app.include_router(rubrics.router, prefix="/api")
    app.include_router(sources.router, prefix="/api")

    # Phase 3: workflow, notifications, calendar
    app.include_router(notifications.router, prefix="/api")
    app.include_router(content_calendar.router, prefix="/api")
    app.include_router(workflow_audit.router, prefix="/api")
    app.include_router(workflow_board.router, prefix="/api")

    # SSE streaming chat endpoints
    app.include_router(chat_stream.router, prefix="/api")

    # Add error handlers
    add_error_handlers(app)

    instrument_fastapi(app)

    return app
