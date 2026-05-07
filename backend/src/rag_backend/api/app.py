"""FastAPI application factory with lifespan management."""

from contextlib import AsyncExitStack, asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from rag_backend.api.middleware.error_handlers import add_error_handlers
from rag_backend.api.middleware.rate_limiting import setup_rate_limiting
from rag_backend.api.middleware.request_logging import RequestLoggingMiddleware
from rag_backend.api.middleware.security_headers import SecurityHeadersMiddleware
from rag_backend.api.routes import admin, auth, carousels, conversations, documents, search
from rag_backend.api.schemas import HealthCheckResponse, HealthResponse
from rag_backend.api.websocket.chat import chat_handler
from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.container import container
from rag_backend.infrastructure.database.config import close_db, init_db
from rag_backend.infrastructure.logging import get_logger, setup_logging
from rag_backend.infrastructure.monitoring import init_langsmith
from rag_backend.monitoring_langfuse import init_langfuse

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Initialize database on startup
    - Close database connections on shutdown
    """
    settings = get_settings()
    setup_logging(debug=settings.debug)
    init_langsmith(settings)
    langfuse_handler = init_langfuse(
        settings.langfuse_public_key,
        settings.langfuse_secret_key.get_secret_value() if settings.langfuse_secret_key else "",
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

        yield

    logger.info("application_shutdown")
    await close_db()


async def _build_checkpointer(
    settings: Settings, stack: AsyncExitStack
) -> BaseCheckpointSaver[object] | None:
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
            AsyncPostgresSaver.from_conn_string(settings.carousel_checkpoint_postgres_url)
        )
        await saver_pg.setup()  # idempotent DDL for checkpoint tables
        return saver_pg
    if not settings.carousel_checkpoint_sqlite_path:
        return None
    Path(settings.carousel_checkpoint_sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    return await stack.enter_async_context(
        AsyncSqliteSaver.from_conn_string(settings.carousel_checkpoint_sqlite_path)
    )


def create_app() -> FastAPI:  # noqa: C901, PLR0915 — app factory configures all middleware/routes
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
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
        allowed_origins = settings.allowed_origins.split(",") if settings.allowed_origins else ["*"]
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
    async def health_check():
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            timestamp=datetime.utcnow(),
        )

    # Detailed health check with dependency status
    @app.get("/health/ready", response_model=HealthCheckResponse)
    async def readiness_check():
        checks = {}

        # Check database
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
    app.include_router(documents.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(carousels.router, prefix="/api")

    # WebSocket endpoint for streaming chat
    @app.websocket("/ws/chat/{conversation_id}")
    async def websocket_chat(websocket: WebSocket, conversation_id: str):
        from uuid import UUID

        from rag_backend.infrastructure.auth import (
            decode_access_token,
            decode_anonymous_token,
        )

        conv_id = UUID(conversation_id)
        settings = get_settings()

        # Extract token from Sec-WebSocket-Protocol header (subprotocol),
        # then fall back to cookies
        subprotocols = websocket.headers.get("sec-websocket-protocol", "")
        token = subprotocols.strip() or None
        if not token:
            token = websocket.cookies.get(COOKIE_ACCESS_TOKEN) or websocket.cookies.get(
                "anon_token"
            )

        is_authorized = False

        if token:
            auth_payload = decode_access_token(settings, token)
            if auth_payload is not None:
                is_authorized = True
                await websocket.accept(subprotocol=token)
            else:
                anon_payload = decode_anonymous_token(settings, token)
                if (
                    anon_payload is not None
                    and anon_payload.get("conversation_id") == conversation_id
                ):
                    is_authorized = True
                    await websocket.accept(subprotocol=token)

        if not is_authorized:
            await websocket.close(code=1008)
            return

        await chat_handler.connect(websocket, conv_id)
        await chat_handler.handle_chat(websocket, conv_id)

    # Add error handlers
    add_error_handlers(app)

    return app
