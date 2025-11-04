# Alter Ego - AI-Powered Personal Chatbot

## Project Overview

Alter Ego is an AI-powered personal chatbot application that allows users to interact with an AI trained on a specific person's knowledge base. The project demonstrates modern full-stack development practices with a beautiful liquid glass morphism UI and clean hexagonal architecture.

## Repository Structure

This is a **multi-part monorepo** with separate frontend and backend applications:

```
alter_ego/
├── frontend/              # React + TypeScript + Vite frontend
│   ├── src/
│   ├── public/
│   ├── claude.md         # Frontend development guide
│   └── package.json
├── backend/               # FastAPI + Python backend
│   ├── app/
│   ├── claude.md         # Backend development guide
│   └── pyproject.toml
├── data/                  # Knowledge base data
│   └── knowledge_base.txt
├── docs/                  # Project documentation
│   ├── epics.md
│   ├── tech-spec.md
│   ├── ux-design-specification.md
│   ├── accessibility.md
│   └── stories/
├── bmad/                  # BMAD workflow system
└── .git/
```

## Technology Stack Summary

### Frontend
- **Framework**: React 19.1.1 with TypeScript 5.9.3
- **Build Tool**: Vite 7.1.7
- **Styling**: Tailwind CSS 4.1.16 with liquid glass morphism
- **UI Components**: Radix UI (accessible primitives)
- **HTTP Client**: Axios 1.13.1
- **Testing**: Vitest + Playwright
- **Component Docs**: Storybook 10.0.2

### Backend
- **Framework**: FastAPI 0.104.1
- **Server**: Uvicorn 0.24.0
- **Language**: Python 3.11+
- **AI Integration**: OpenAI GPT-4 Turbo
- **Validation**: Pydantic 2.5.0
- **Package Manager**: Poetry 2.0+

### Architecture Patterns
- **Frontend**: Component-based architecture with liquid glass morphism design system
- **Backend**: Hexagonal architecture (ports & adapters pattern)
- **Integration**: RESTful API communication via HTTP

## Quick Start

### Prerequisites
- **Node.js**: 18+ (for frontend)
- **Python**: 3.11+ (for backend)
- **Poetry**: 2.0+ (for Python dependency management)
- **OpenAI API Key**: Required for AI functionality

### Setup Instructions

#### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Install dependencies
poetry install

# Create .env file
cp .env.example .env

# Edit .env and add your credentials:
# OPENAI_API_KEY=your_key_here
# PERSON_NAME=Your Name
# KNOWLEDGE_BASE_PATH=../data/knowledge_base.txt
# CORS_ORIGINS=http://localhost:5173

# Run the server
poetry run uvicorn app.main:app --reload
```

Backend will run at: **http://localhost:8000**

#### 2. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env file (optional)
cp .env.example .env

# Run the development server
npm run dev
```

Frontend will run at: **http://localhost:5173**

#### 3. Knowledge Base Setup

Create or edit `data/knowledge_base.txt` with the person's information:

```txt
Name: John Doe
Role: Senior Software Engineer

Background:
- 10 years of experience in full-stack development
- Specializes in React, TypeScript, and Python
...
```

### Verify Setup

1. Open browser to http://localhost:5173
2. Type a message in the chat interface
3. Verify AI responds based on knowledge base

## Project Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  React Frontend (localhost:5173)                    │   │
│  │  - Liquid Glass Morphism UI                         │   │
│  │  - TypeScript + Tailwind CSS                        │   │
│  │  - Axios API Client                                 │   │
│  └──────────────────┬──────────────────────────────────┘   │
└─────────────────────┼──────────────────────────────────────┘
                      │
                      │ HTTP POST /api/chat
                      │ Request: { message: "..." }
                      │ Response: { response: "...", timestamp: "..." }
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│           FastAPI Backend (localhost:8000)                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API Layer (Primary Adapter)                        │   │
│  │  - Route handlers                                   │   │
│  │  - Request/response models                          │   │
│  │  - Error handling                                   │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │                                       │
│  ┌─────────────────▼──────────────────────────────────┐   │
│  │  Service Layer (Core Business Logic)               │   │
│  │  - Chat processing                                  │   │
│  │  - Knowledge base integration                       │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │                                       │
│  ┌─────────────────▼──────────────────────────────────┐   │
│  │  Adapters Layer (Secondary Adapters)               │   │
│  │  - OpenAI API client                                │   │
│  │  - File system (knowledge base)                     │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ API Call
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    OpenAI API                               │
│  - Model: GPT-4 Turbo Preview                              │
│  - System prompt with knowledge base                        │
│  - Returns AI-generated response                            │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Input** → Frontend captures message via ChatInterface component
2. **HTTP Request** → Axios sends POST to `/api/chat` with message
3. **Route Handler** → FastAPI route validates request via Pydantic
4. **Service Layer** → Calls `get_chat_response()` with user message
5. **OpenAI Integration** → Constructs system prompt with knowledge base + user message
6. **AI Response** → OpenAI returns generated response
7. **HTTP Response** → Backend returns JSON with response + timestamp
8. **UI Update** → Frontend displays AI message in chat interface

### Integration Points

#### Frontend → Backend

**Endpoint**: `POST http://localhost:8000/api/chat`

**Request Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "message": "Tell me about your experience with React"
}
```

**Response**:
```json
{
  "response": "I have over 5 years of experience with React...",
  "timestamp": "2025-11-04T12:00:00Z"
}
```

**Error Response** (500):
```json
{
  "detail": "Failed to process chat message: ..."
}
```

#### Backend → OpenAI

**Model**: `gpt-4-turbo-preview` (configurable)

**API Call**:
```python
response = await client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ],
    temperature=0.7,
    max_tokens=500
)
```

**System Prompt Template**:
```
You are {PERSON_NAME}. Answer questions about your career and personal
background based on the provided knowledge base. Be conversational and helpful.

Knowledge Base:
{KNOWLEDGE_BASE_CONTENT}
```

## Development Guides

### Frontend Development
See **`frontend/claude.md`** for:
- Liquid glass morphism styleguide
- Component patterns
- Typography, spacing, colors
- Animation standards
- Accessibility guidelines
- Testing practices

### Backend Development
See **`backend/claude.md`** for:
- Hexagonal architecture patterns
- Service layer standards
- Route creation guidelines
- Configuration management
- API design standards
- Error handling

## Project Documentation

### Planning & Design
- **`docs/epics.md`** - Feature epics and breakdown
- **`docs/tech-spec.md`** - Technical specification
- **`docs/ux-design-specification.md`** - UX design system
- **`docs/accessibility.md`** - WCAG 2.1 AA compliance documentation
- **`docs/backlog.md`** - Product backlog

### Development Stories
- **`docs/stories/`** - User stories with acceptance criteria
  - `story-personal-chatbot-1.md` - Backend API implementation
  - `story-personal-chatbot-2.md` - Frontend chat interface
  - `story-ux-alignment-2-1.md` - UX design alignment
  - `story-project-improvements-3.md` - Accessibility improvements

### Retrospectives
- **`docs/retrospectives/`** - Sprint retrospectives
  - `epic-1-retro-2025-11-03.md` - Epic 1 retrospective

## Environment Configuration

### Frontend Environment Variables

**File**: `frontend/.env`

```env
VITE_API_URL=http://localhost:8000
```

### Backend Environment Variables

**File**: `backend/.env`

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here
PERSON_NAME=Your Name

# Optional (with defaults)
OPENAI_MODEL=gpt-4-turbo-preview
KNOWLEDGE_BASE_PATH=../data/knowledge_base.txt
CORS_ORIGINS=http://localhost:5173
```

## Development Workflow

### Starting Development

```bash
# Terminal 1: Start backend
cd backend
poetry run uvicorn app.main:app --reload

# Terminal 2: Start frontend
cd frontend
npm run dev

# Terminal 3: Run Storybook (optional)
cd frontend
npm run storybook
```

### Making Changes

#### Frontend Changes
1. Components → `frontend/src/components/`
2. Apply liquid glass styles → Use utility classes from `index.css`
3. Document in Storybook → Create `.stories.tsx` file
4. Follow accessibility guidelines → Add ARIA labels
5. Test → `npm run test`

#### Backend Changes
1. Routes → `backend/app/api/routes.py`
2. Business logic → `backend/app/services/<feature>_service.py`
3. Follow hexagonal architecture → Separate concerns
4. Update models → Use Pydantic for validation
5. Test → Create tests in `tests/`

### Adding New Features

#### 1. Frontend Feature
```bash
# Create component
touch frontend/src/components/NewFeature.tsx

# Create story
touch frontend/src/components/NewFeature.stories.tsx

# Add to App.tsx or relevant parent
```

#### 2. Backend Feature
```bash
# Create service
touch backend/app/services/new_feature_service.py

# Add routes
# Edit backend/app/api/routes.py or create new router

# Update settings if needed
# Edit backend/app/config/settings.py
```

#### 3. Update Integration
- Update TypeScript types in `frontend/src/types/`
- Update API service in `frontend/src/services/api.ts`
- Test end-to-end flow

## Testing

### Frontend Testing
```bash
cd frontend

# Run all tests
npm run test

# Run Storybook tests
npm run storybook

# Build and verify
npm run build
```

### Backend Testing
```bash
cd backend

# Run tests (when implemented)
poetry run pytest

# Type checking
poetry run mypy app/

# Linting
poetry run ruff check app/
```

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Design System

### Frontend: Liquid Glass Morphism

**Key Characteristics**:
- Translucent surfaces with `backdrop-filter: blur(30px)`
- Subtle borders with `rgba(255, 255, 255, 0.12)`
- Layered shadows for depth
- Smooth transitions (`0.5s cubic-bezier`)
- Glow effects on hover/focus
- Dark background with purple/blue accents

**Primary Color**: Cyber Purple (`#8b5cf6`)
**Alternative**: Electric Blue (`#2563eb`)

See `frontend/claude.md` for complete styleguide.

### Backend: Hexagonal Architecture

**Core Principle**: Dependency Inversion
- Core business logic depends on NO external frameworks
- External dependencies (FastAPI, OpenAI) are adapters
- Easy to test, maintain, and swap implementations

**Layers**:
1. **API Layer** (Primary Adapters) - HTTP interface
2. **Service Layer** (Core) - Business logic
3. **Adapters Layer** (Secondary) - External integrations

See `backend/claude.md` for architecture details.

## Deployment (Future)

### Frontend Deployment
```bash
cd frontend
npm run build
# Deploy dist/ folder to:
# - Vercel
# - Netlify
# - AWS S3 + CloudFront
```

### Backend Deployment
```bash
cd backend
poetry export -f requirements.txt --output requirements.txt
# Deploy with:
# - Docker
# - AWS Lambda
# - Railway
# - Render
```

### Environment Variables
- Use platform-specific secret management
- Never commit `.env` files
- Update CORS_ORIGINS for production domain

## Troubleshooting

### Frontend Issues

**Issue**: API calls failing
```bash
# Check backend is running
curl http://localhost:8000/health

# Check CORS configuration in backend/.env
CORS_ORIGINS=http://localhost:5173
```

**Issue**: Styling not working
```bash
# Rebuild Tailwind
npm run dev

# Check index.css is imported in main.tsx
```

### Backend Issues

**Issue**: OpenAI API errors
```bash
# Verify API key in backend/.env
echo $OPENAI_API_KEY

# Check knowledge base exists
cat ../data/knowledge_base.txt
```

**Issue**: Import errors
```bash
# Reinstall dependencies
poetry install

# Verify Python version
python --version  # Should be 3.11+
```

## Contributing Guidelines

### Code Style

**Frontend**:
- TypeScript for all components
- Functional components with hooks
- Use Tailwind utilities (avoid custom CSS)
- Apply liquid glass morphism classes

**Backend**:
- Type hints everywhere
- Follow hexagonal architecture
- Use async/await for I/O
- Document with docstrings

### Commit Messages
```
feat: add user authentication
fix: resolve chat message timestamp issue
docs: update API documentation
style: apply liquid glass to login form
refactor: extract chat logic to service
test: add unit tests for chat service
```

### Pull Request Process
1. Create feature branch from `main`
2. Implement feature following guidelines
3. Test locally (frontend + backend)
4. Update documentation if needed
5. Create PR with clear description
6. Address review feedback

## Helpful Commands

### Frontend
```bash
npm run dev          # Development server
npm run build        # Production build
npm run preview      # Preview build
npm run test         # Run tests
npm run storybook    # Component docs
npm run lint         # Lint code
```

### Backend
```bash
poetry run uvicorn app.main:app --reload    # Dev server
poetry run uvicorn app.main:app             # Production
poetry run pytest                            # Tests
poetry run mypy app/                         # Type checking
poetry add <package>                         # Add dependency
```

### Git
```bash
git status                    # Check status
git add .                     # Stage changes
git commit -m "message"       # Commit
git push origin <branch>      # Push
git pull origin main          # Pull latest
```

## Resources

### Frontend Resources
- [React Documentation](https://react.dev)
- [Tailwind CSS v4](https://tailwindcss.com)
- [Radix UI](https://www.radix-ui.com)
- [Vite Guide](https://vitejs.dev/guide/)

### Backend Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Pydantic Documentation](https://docs.pydantic.dev)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)

### Design Resources
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Glass Morphism Generator](https://glassmorphism.com/)

---

**Project**: Alter Ego
**Version**: 1.0.0
**Created**: 2025-10-30
**Last Updated**: 2025-11-04
**Architecture**: Multi-part monorepo (React frontend + FastAPI backend)
