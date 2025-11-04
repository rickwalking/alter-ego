# Backend Development Guide - Alter Ego

## Project Overview

This is the backend API for Alter Ego, an AI-powered personal chatbot. Built with FastAPI and Python 3.11+, following **hexagonal architecture** principles (ports and adapters pattern) for maintainability and testability.

## Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Framework** | FastAPI | 0.104.1 | Modern async web framework |
| **Server** | Uvicorn | 0.24.0 | ASGI server |
| **Language** | Python | 3.11+ | Programming language |
| **Validation** | Pydantic | 2.5.0 | Data validation and settings |
| **AI Integration** | OpenAI | 1.12.0+ | GPT-4 chat completions |
| **Environment** | python-dotenv | 1.0.0 | Environment variable management |
| **Package Manager** | Poetry | 2.0+ | Dependency management |

## Architecture Pattern: Hexagonal Architecture

### Overview

The backend follows **hexagonal architecture** (also known as ports and adapters), which separates:

1. **Core Business Logic** (Domain layer)
2. **Ports** (Interfaces/abstractions)
3. **Adapters** (Implementations)

This ensures the application is:
- **Testable**: Business logic can be tested without external dependencies
- **Maintainable**: Clear separation of concerns
- **Flexible**: Easy to swap implementations (e.g., switch from OpenAI to different LLM)

### Layer Structure

```
backend/app/
├── api/                 # PRIMARY ADAPTERS (HTTP Interface)
│   ├── routes.py       # Route handlers (API controllers)
│   └── __init__.py     # Router exports
├── services/            # CORE BUSINESS LOGIC (Application Services)
│   ├── openai_service.py  # AI service implementation
│   └── __init__.py     # Service exports
├── config/              # CONFIGURATION (Settings)
│   ├── settings.py     # Environment-based configuration
│   └── __init__.py     # Config exports
└── main.py              # APPLICATION ENTRY POINT
```

### Hexagonal Architecture Mapping

#### Primary Adapters (Driving Side)
**Location**: `app/api/`

These **drive** the application by receiving external requests.

```python
# app/api/routes.py - HTTP Adapter
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """HTTP adapter that receives requests and delegates to service"""
    ai_response = await get_chat_response(request.message)
    return ChatResponse(response=ai_response, timestamp=...)
```

**Responsibility**:
- Handle HTTP requests/responses
- Validate input via Pydantic models
- Delegate to application services
- Format responses

#### Application Services (Core)
**Location**: `app/services/`

The **core business logic** - independent of external frameworks.

```python
# app/services/openai_service.py - Application Service
async def get_chat_response(message: str) -> str:
    """Core business logic for chat processing"""
    system_prompt = f"""You are {settings.PERSON_NAME}..."""
    response = await client.chat.completions.create(...)
    return response.choices[0].message.content
```

**Responsibility**:
- Orchestrate business logic
- Call secondary adapters (OpenAI client)
- Transform data
- Implement use cases

#### Secondary Adapters (Driven Side)
**Location**: External clients (OpenAI SDK, future database clients)

These are **driven** by the application to interact with external systems.

```python
# app/services/openai_service.py - Uses OpenAI Adapter
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
```

**Current Secondary Adapters**:
- OpenAI API (via `AsyncOpenAI` client)
- File system (for knowledge base loading)

**Future Secondary Adapters** (as needed):
- Database (PostgreSQL, MongoDB)
- Message queues (RabbitMQ, Redis)
- Cache layer (Redis)

#### Configuration (Infrastructure)
**Location**: `app/config/`

Environment-based settings using Pydantic.

```python
# app/config/settings.py
class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    PERSON_NAME: str
    KNOWLEDGE_BASE_PATH: str = "../data/knowledge_base.txt"
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173"
```

## Project Structure

```
backend/
├── app/
│   ├── api/                    # PRIMARY ADAPTERS
│   │   ├── __init__.py        # Export router
│   │   └── routes.py          # HTTP route handlers
│   ├── services/               # CORE BUSINESS LOGIC
│   │   ├── __init__.py        # Export services
│   │   └── openai_service.py  # AI integration service
│   ├── config/                 # CONFIGURATION
│   │   ├── __init__.py        # Export settings
│   │   └── settings.py        # Pydantic settings
│   ├── __init__.py
│   └── main.py                 # FastAPI app initialization
├── .env                        # Environment variables
├── .env.example                # Environment template
├── pyproject.toml              # Poetry dependencies
├── poetry.lock                 # Locked dependencies
└── .python-version             # Python version (3.11+)
```

## Standards for Creating New Features

### 1. Adding a New Route (Primary Adapter)

**File**: `app/api/routes.py` or `app/api/<domain>_routes.py` for new domains

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services import your_service_function

# Define request/response models
class YourRequest(BaseModel):
    """Request model with validation"""
    field: str = Field(..., min_length=1, description="Field description")

class YourResponse(BaseModel):
    """Response model"""
    result: str = Field(..., description="Result description")

# Create router if new domain
router = APIRouter(prefix="/api/<domain>", tags=["<domain>"])

@router.post("/endpoint", response_model=YourResponse)
async def your_endpoint(request: YourRequest) -> YourResponse:
    """
    Endpoint description.

    Args:
        request: YourRequest with required data

    Returns:
        YourResponse with result

    Raises:
        HTTPException: If processing fails
    """
    try:
        # Delegate to service layer
        result = await your_service_function(request.field)

        return YourResponse(result=result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process: {str(e)}"
        )
```

**Standards**:
- Use Pydantic models for request/response
- Add type hints everywhere
- Include docstrings with Args/Returns/Raises
- Handle exceptions and return appropriate HTTP codes
- Delegate business logic to services layer

### 2. Adding a Service (Core Business Logic)

**File**: `app/services/<feature>_service.py`

```python
"""Service for <feature> functionality"""
from app.config import settings

async def your_service_function(input_data: str) -> str:
    """
    Core business logic for <feature>.

    Args:
        input_data: Description of input

    Returns:
        Processed result string

    Raises:
        Exception: If processing fails
    """
    try:
        # Business logic here
        # Call secondary adapters (database, external APIs)
        result = await external_api_call(input_data)

        # Transform/process data
        processed = transform_data(result)

        return processed

    except Exception as e:
        print(f"✗ Service error: {str(e)}")
        raise Exception(f"Failed to process: {str(e)}")
```

**Standards**:
- Keep services independent of HTTP concerns
- Use dependency injection for external clients
- Handle errors at service level
- Return domain objects, not HTTP responses
- Log errors with clear messages (✓ for success, ✗ for errors)

### 3. Adding Configuration

**File**: `app/config/settings.py`

```python
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    """Application configuration settings"""

    # Add new configuration
    NEW_SETTING: str
    NEW_OPTIONAL: str = "default_value"

    @field_validator('NEW_SETTING', mode='before')
    @classmethod
    def validate_new_setting(cls, value):
        """Custom validation logic"""
        if not value:
            raise ValueError("NEW_SETTING cannot be empty")
        return value

    class Config:
        env_file = ".env"
        case_sensitive = True
```

**Update** `.env.example`:
```env
NEW_SETTING=value
NEW_OPTIONAL=optional_value
```

**Standards**:
- Use Pydantic validators for complex validation
- Provide sensible defaults when appropriate
- Document in `.env.example`
- Keep settings in a single `Settings` class

### 4. Adding a Secondary Adapter (External Integration)

**File**: `app/services/<integration>_adapter.py` or within service file

```python
"""Adapter for <external system> integration"""
from external_library import ExternalClient
from app.config import settings

# Initialize client at module level
client = ExternalClient(api_key=settings.EXTERNAL_API_KEY)

async def call_external_system(data: str) -> dict:
    """
    Adapter for external system communication.

    Args:
        data: Input data for external system

    Returns:
        Response from external system

    Raises:
        Exception: If external call fails
    """
    try:
        response = await client.make_request(data)
        return response.to_dict()

    except Exception as e:
        print(f"✗ External system error: {str(e)}")
        raise Exception(f"External call failed: {str(e)}")
```

**Standards**:
- Initialize clients at module level or use dependency injection
- Keep adapter logic focused on external communication
- Transform external data formats to internal domain models
- Handle connection errors gracefully

## API Design Standards

### Request/Response Models

Use Pydantic for all request and response models:

```python
from pydantic import BaseModel, Field
from datetime import datetime

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message"
    )

class ChatResponse(BaseModel):
    """Chat response model"""
    response: str = Field(..., description="AI-generated response")
    timestamp: str = Field(..., description="Response timestamp in ISO8601 format")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "Hello! How can I help you?",
                "timestamp": "2025-11-04T12:00:00Z"
            }
        }
```

**Standards**:
- Use descriptive Field annotations
- Validate string lengths, ranges, etc.
- Provide example schemas for documentation
- Use ISO8601 format for timestamps
- Keep models close to routes that use them

### Error Handling

```python
from fastapi import HTTPException

# 400 - Bad Request (validation failures)
raise HTTPException(status_code=400, detail="Invalid input")

# 404 - Not Found
raise HTTPException(status_code=404, detail="Resource not found")

# 500 - Internal Server Error (unexpected errors)
raise HTTPException(status_code=500, detail="Internal server error")
```

**Standards**:
- Use appropriate HTTP status codes
- Provide clear error messages
- Log detailed errors server-side
- Return safe error messages to client

### Routing Organization

```python
# app/api/__init__.py
from fastapi import APIRouter
from app.api import routes

router = APIRouter()
router.include_router(routes.router)

# Future: Add more routers as features grow
# from app.api import user_routes, admin_routes
# router.include_router(user_routes.router)
# router.include_router(admin_routes.router)
```

```python
# app/main.py
from app.api import router

app.include_router(router)
```

**Standards**:
- Group related routes in separate files (`chat_routes.py`, `user_routes.py`)
- Use `APIRouter` with prefix and tags
- Register all routers in `app/api/__init__.py`
- Include main router in `app/main.py`

## Middleware & CORS

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # From .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Standards**:
- Configure CORS via environment variables
- Use middleware for cross-cutting concerns (logging, auth, etc.)
- Keep middleware configuration in `main.py`

## Dependency Injection (Future)

For more complex services, use FastAPI's dependency injection:

```python
from fastapi import Depends

# Dependency
async def get_db_session():
    session = database.get_session()
    try:
        yield session
    finally:
        await session.close()

# Route using dependency
@router.get("/users")
async def get_users(db = Depends(get_db_session)):
    users = await db.query(User).all()
    return users
```

**Standards**:
- Use `Depends()` for database sessions, auth, etc.
- Define dependencies in `app/dependencies.py`
- Clean up resources in `finally` blocks

## Development Workflow

### Environment Setup

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Or run commands directly
poetry run uvicorn app.main:app --reload
```

### Running the Application

```bash
# Development (with auto-reload)
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Environment Variables

Create `.env` file in backend root:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview
PERSON_NAME=Your Name
KNOWLEDGE_BASE_PATH=../data/knowledge_base.txt
CORS_ORIGINS=http://localhost:5173
```

### API Documentation

FastAPI automatically generates interactive API docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Testing Guidelines (Future)

When adding tests, follow hexagonal architecture:

```python
# tests/services/test_chat_service.py
import pytest
from app.services.openai_service import get_chat_response

@pytest.mark.asyncio
async def test_chat_service_with_mock():
    """Test service layer with mocked adapter"""
    # Mock the OpenAI client
    with mock.patch('app.services.openai_service.client') as mock_client:
        mock_client.chat.completions.create.return_value = ...

        result = await get_chat_response("test message")

        assert result == "expected response"
```

**Standards**:
- Test services independently (mock secondary adapters)
- Test routes with TestClient
- Use pytest and pytest-asyncio
- Mock external dependencies (OpenAI, databases)

## Best Practices

### Code Organization

1. **Separate concerns**: Routes → Services → Adapters
2. **Single Responsibility**: Each module has one purpose
3. **Dependency Direction**: Adapters depend on core, not vice versa

### Type Safety

1. **Type hints everywhere**: Functions, variables, return types
2. **Use Pydantic models**: For validation and serialization
3. **Avoid `Any`**: Be explicit with types

### Error Handling

1. **Log errors clearly**: Use ✓ for success, ✗ for errors
2. **Fail gracefully**: Always provide fallbacks
3. **Raise at service level**: Let routes handle HTTP responses

### Configuration

1. **Use environment variables**: Never hardcode secrets
2. **Provide defaults**: When reasonable
3. **Validate early**: Use Pydantic validators

### Async/Await

1. **Use async for I/O**: Database, HTTP calls, file operations
2. **Await external calls**: OpenAI API, database queries
3. **Don't block event loop**: Avoid sync I/O in async functions

## Integration Points

### Frontend Integration

**Endpoint**: `POST /api/chat`

**Request**:
```json
{
  "message": "Tell me about your experience"
}
```

**Response**:
```json
{
  "response": "AI-generated response based on knowledge base",
  "timestamp": "2025-11-04T12:00:00Z"
}
```

### OpenAI Integration

**Model**: GPT-4 Turbo Preview (configurable via `OPENAI_MODEL`)

**System Prompt Structure**:
```python
system_prompt = f"""You are {settings.PERSON_NAME}.
Answer questions about your career and personal background
based on the provided knowledge base. Be conversational and helpful.

Knowledge Base:
{KNOWLEDGE_BASE}"""
```

**Parameters**:
- Temperature: `0.7` (balanced creativity/consistency)
- Max Tokens: `500` (response length limit)

## Hexagonal Architecture Benefits

### Why This Matters

1. **Testability**: Mock external dependencies easily
2. **Flexibility**: Swap OpenAI for different LLM without changing core logic
3. **Maintainability**: Clear boundaries between layers
4. **Scalability**: Add features without tangling code

### Example: Swapping OpenAI for Different LLM

**Before** (current):
```python
# app/services/openai_service.py
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
```

**After** (switch to Anthropic Claude):
```python
# app/services/claude_service.py
client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

# Same function signature - no changes to routes!
async def get_chat_response(message: str) -> str:
    # Different implementation, same interface
    ...
```

Only update the service layer - routes remain unchanged!

---

**Generated:** 2025-11-04
**Last Updated:** 2025-11-04
**Architecture**: Hexagonal (Ports & Adapters)
