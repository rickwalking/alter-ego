"""FastAPI application factory with lifespan management."""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from rag_backend.api.middleware.error_handlers import add_error_handlers
from rag_backend.api.middleware.rate_limiting import setup_rate_limiting
from rag_backend.api.middleware.request_logging import RequestLoggingMiddleware
from rag_backend.api.middleware.security_headers import SecurityHeadersMiddleware
from rag_backend.api.routes import auth, carousels, conversations, documents, search
from rag_backend.api.schemas import HealthCheckResponse, HealthResponse
from rag_backend.api.websocket.chat import chat_handler
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.container import container
from rag_backend.infrastructure.database.config import close_db, init_db
from rag_backend.infrastructure.logging import get_logger, setup_logging
from rag_backend.infrastructure.monitoring import init_langsmith

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

    logger.info("application_startup", version=settings.app_version)

    await init_db(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )

    container.wire(packages=["rag_backend.api"])

    yield

    logger.info("application_shutdown")
    await close_db()


def create_app() -> FastAPI:
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
    allowed_origins = settings.allowed_origins.split(",") if settings.allowed_origins else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
            if settings.pinecone_api_key:
                from pinecone import Pinecone

                pc = Pinecone(api_key=settings.pinecone_api_key)
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
            if settings.openai_api_key:
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=settings.openai_api_key)
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
    app.include_router(documents.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(carousels.router, prefix="/api")

    # WebSocket endpoint for streaming chat
    @app.websocket("/ws/chat/{conversation_id}")
    async def websocket_chat(websocket: WebSocket, conversation_id: str):
        from uuid import UUID

        conv_id = UUID(conversation_id)
        await chat_handler.connect(websocket, conv_id)
        await chat_handler.handle_chat(websocket, conv_id)

    # Add error handlers
    add_error_handlers(app)

    return app
