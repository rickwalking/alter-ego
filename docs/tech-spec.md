# Alter Ego - Technical Specification

**Author:** BMad
**Date:** 2025-10-30
**Project Level:** 1
**Project Type:** software
**Development Context:** greenfield

---

## Source Tree Structure

```
alter_ego/
├── backend/
│   ├── app/
│   │   ├── __init__.py                [CREATE] # Package initialization
│   │   ├── main.py                    [CREATE] # FastAPI application entry point
│   │   ├── api/
│   │   │   ├── __init__.py            [CREATE] # Package initialization
│   │   │   └── routes.py              [CREATE] # API endpoints for chat
│   │   ├── services/
│   │   │   ├── __init__.py            [CREATE] # Package initialization
│   │   │   └── openai_service.py      [CREATE] # OpenAI integration
│   │   └── config/
│   │       ├── __init__.py            [CREATE] # Package initialization
│   │       └── settings.py            [CREATE] # Environment configuration
│   ├── pyproject.toml                 [CREATE] # Poetry dependencies and project config
│   ├── poetry.lock                    [CREATE] # Poetry lock file (auto-generated)
│   └── .env.example                   [CREATE] # Environment variables template
├── frontend/
│   ├── public/
│   │   └── index.html                 [CREATE] # HTML template
│   ├── src/
│   │   ├── App.tsx                    [CREATE] # Main React component
│   │   ├── components/
│   │   │   ├── ui/                    [CREATE] # Shadcn UI components library
│   │   │   │   ├── button.tsx         [CREATE] # Button component (Shadcn)
│   │   │   │   ├── card.tsx           [CREATE] # Card component (Shadcn)
│   │   │   │   ├── input.tsx          [CREATE] # Input component (Shadcn)
│   │   │   │   ├── scroll-area.tsx    [CREATE] # ScrollArea component (Shadcn)
│   │   │   │   └── avatar.tsx         [CREATE] # Avatar component (Shadcn)
│   │   │   ├── ChatInterface.tsx      [CREATE] # Chat UI component
│   │   │   └── LandingPage.tsx        [CREATE] # Landing page component
│   │   ├── lib/
│   │   │   └── utils.ts               [CREATE] # Utility functions (cn helper, etc.)
│   │   ├── services/
│   │   │   └── api.ts                 [CREATE] # API client for backend
│   │   ├── types/
│   │   │   └── index.ts               [CREATE] # TypeScript type definitions
│   │   └── main.tsx                   [CREATE] # React entry point
│   ├── components.json                [CREATE] # Shadcn UI configuration
│   ├── package.json                   [CREATE] # Node dependencies
│   ├── tsconfig.json                  [CREATE] # TypeScript configuration
│   ├── tailwind.config.js             [CREATE] # Tailwind CSS configuration
│   ├── postcss.config.js              [CREATE] # PostCSS configuration
│   ├── vite.config.ts                 [CREATE] # Vite configuration
│   └── .env.example                   [CREATE] # Frontend environment variables
├── data/
│   └── knowledge_base.txt             [CREATE] # Career and personal information
├── .gitignore                         [CREATE] # Git ignore rules
└── README.md                          [CREATE] # Project documentation
```

---

## Technical Approach

**Architecture:** Decoupled frontend/backend architecture with REST API communication

**Backend Strategy:**
- FastAPI server handling chat requests
- OpenAI GPT-4 integration for conversation handling
- Knowledge base loaded from text file containing career/personal information
- CORS enabled for frontend communication
- Environment-based configuration for API keys

**Frontend Strategy:**
- React SPA with Vite as build tool
- Single landing page with embedded chat interface
- Real-time chat UI with message history
- API client service for backend communication
- Responsive design for desktop and mobile

**Data Flow:**
1. User sends message through React chat interface
2. Frontend API client sends POST request to FastAPI backend
3. Backend loads knowledge base context and user message
4. OpenAI API processes request with system prompt + knowledge base
5. Response streamed back to frontend
6. Chat interface displays AI response

---

## Implementation Stack

**Backend:**
- Python 3.11
- FastAPI 0.104.1
- OpenAI Python SDK 1.3.7
- Uvicorn 0.24.0 (ASGI server)
- Python-dotenv 1.0.0 (environment management)
- Pydantic 2.5.0 (data validation)
- Poetry 1.7.0 (dependency management)

**Frontend:**
- Node.js 22.x LTS (minimum 22.12+ for Vite 7.0)
- React 19.2.0
- TypeScript 5.9.3
- Vite 7.0
- Axios 1.12.2 (HTTP client)
- Tailwind CSS 4.0 (with @tailwindcss/vite plugin)
- Shadcn UI (CLI-managed, latest via npx)
- Radix UI (installed as Shadcn dependencies)
- Storybook 9.x (component development and visual testing)

**Development Tools:**
- Git 2.42+
- VS Code (recommended IDE)
- Postman/curl (API testing)

**Environment:**
- OpenAI API Key (required)
- CORS configuration for local development

---

## Technical Details

**API Endpoints:**

```
POST /api/chat
Request: { "message": "string" }
Response: { "response": "string", "timestamp": "ISO8601" }
```

**Backend Configuration (settings.py):**
- `OPENAI_API_KEY`: OpenAI API key from environment
- `OPENAI_MODEL`: "gpt-4-turbo-preview"
- `PERSON_NAME`: Person's name from environment variable
- `KNOWLEDGE_BASE_PATH`: "../data/knowledge_base.txt"
- `CORS_ORIGINS`: ["http://localhost:5173"] (Vite default port)

**OpenAI Integration (openai_service.py):**
- System prompt: f"You are {PERSON_NAME}. Answer questions about your career and personal background based on the provided knowledge base. Be conversational and helpful."
- Knowledge base loaded at startup and included in system context
- Temperature: 0.7 (balanced creativity/accuracy)
- Max tokens: 500 per response

**Frontend API Client (api.ts):**
- Base URL: `http://localhost:8000`
- Axios instance with timeout: 30000ms
- Error handling for network failures
- TypeScript interfaces for request/response types

**React Components (TypeScript):**
- `LandingPage.tsx`: Hero section with project introduction using Card component
- `ChatInterface.tsx`: Chat UI with message list and input field
  - Uses ScrollArea for message container
  - Uses Input component for message input
  - Uses Button component for send action
  - Uses Avatar for message display
- Message state managed with useState hook
- Auto-scroll to latest message
- Shadcn UI components styled with Tailwind CSS
- Reusable UI components in `components/ui/` directory

---

## Development Setup

**Prerequisites:**
- Python 3.11 installed
- Node.js 20.10.0 LTS installed
- Poetry 1.7.0 installed (`curl -sSL https://install.python-poetry.org | python3 -`)
- Git initialized in project root
- OpenAI API key obtained from https://platform.openai.com/api-keys

**Backend Setup:**
```bash
cd backend
poetry init --no-interaction --name alter-ego-backend --python "^3.11"
poetry add fastapi uvicorn openai python-dotenv pydantic
poetry install
cp .env.example .env
# Edit .env and add OPENAI_API_KEY and PERSON_NAME
```

**Frontend Setup:**
```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install

# Install Tailwind CSS 4.0 with Vite plugin (NEW CONFIG APPROACH)
npm install -D tailwindcss@next @tailwindcss/vite@next

# Install other dependencies
npm install axios

# Initialize Shadcn UI
npx shadcn@latest init
# Select: Default style, Neutral colors, CSS variables: yes

# Add required Shadcn components
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add input
npx shadcn@latest add scroll-area
npx shadcn@latest add avatar

# Initialize Storybook
npx storybook@latest init

cp .env.example .env
# Edit .env if needed for API URL override
```

**Storybook Scripts:**
```bash
npm run storybook    # Start Storybook on localhost:6006
npm run build-storybook  # Build static Storybook for deployment
```

**IMPORTANT: Tailwind CSS 4.0 Changes:**
- No more `tailwind.config.js` or PostCSS config needed
- Configuration is now CSS-first using `@theme` directive in your CSS file
- Automatic content detection (no need to configure file paths)
- Use `@tailwindcss/vite` plugin in vite.config.ts

**Environment Variables:**

Backend `.env`:
```
OPENAI_API_KEY=sk-...
PERSON_NAME=Your Name
OPENAI_MODEL=gpt-4-turbo-preview
KNOWLEDGE_BASE_PATH=../data/knowledge_base.txt
```

Frontend `.env`:
```
VITE_API_BASE_URL=http://localhost:8000
```

---

## Implementation Guide

**Phase 1: Project Initialization (1-2 hours)**
1. Create project directory structure
2. Initialize Git repository
3. Set up backend with Poetry:
   - Run `poetry init` in backend directory
   - Add dependencies: fastapi, uvicorn, openai, python-dotenv, pydantic
   - Create pyproject.toml and install dependencies
4. Set up frontend with Vite:
   - Run `npm create vite` with React TypeScript template
   - Install Tailwind CSS and configure
   - Initialize Shadcn UI with `npx shadcn-ui@latest init`
   - Add required Shadcn components (button, card, input, scroll-area, avatar)
   - Install axios for API calls
5. Create .env.example files for both backend and frontend
6. Create .gitignore for Python and Node.js

**Phase 2: Backend API Development (2-3 hours)**
1. Create `app/config/settings.py`:
   - Load environment variables (OPENAI_API_KEY, PERSON_NAME, etc.)
   - Export configuration as Settings object
2. Create `app/services/openai_service.py`:
   - Initialize OpenAI client with API key
   - Load knowledge base from file
   - Implement `get_chat_response(message: str)` function
   - Build system prompt with PERSON_NAME and knowledge base context
3. Create `app/api/routes.py`:
   - Define POST /api/chat endpoint
   - Validate request with Pydantic model
   - Call openai_service and return response
4. Create `app/main.py`:
   - Initialize FastAPI app
   - Configure CORS middleware
   - Include API routes
   - Add health check endpoint

**Phase 3: Frontend Component Library Setup (1-2 hours)**
1. Verify Shadcn UI components installed in `src/components/ui/`:
   - Button, Card, Input, ScrollArea, Avatar
2. Create `src/lib/utils.ts`:
   - Add cn() helper function for conditional Tailwind classes
3. Create TypeScript types in `src/types/index.ts`:
   - Message interface { id, content, role, timestamp }
   - ChatRequest/ChatResponse types
4. Create `src/services/api.ts`:
   - Set up axios instance with base URL from env
   - Implement `sendMessage(message: string)` function
   - Error handling wrapper

**Phase 4: Frontend UI Development (3-4 hours)**
1. Create `src/components/LandingPage.tsx`:
   - Use Card component for hero section
   - Project title, description, and introduction
   - Responsive layout with Tailwind
2. Create `src/components/ChatInterface.tsx`:
   - Use ScrollArea for message list container
   - Map messages with Avatar component for user/AI distinction
   - Use Input component for message input
   - Use Button component for send action
   - Loading state during API call
   - Error handling display
   - Auto-scroll to bottom on new messages
3. Create `src/App.tsx`:
   - Combine LandingPage and ChatInterface
   - Main application layout with Tailwind grid/flex
   - Dark mode support (optional)

**Phase 5: Knowledge Base Creation (30 minutes)**
1. Create `data/knowledge_base.txt`
2. Add career information, skills, experience
3. Add personal background relevant for recruiters
4. Format as plain text for easy loading

---

## Testing Approach

**Backend Testing:**
1. **Manual API Testing:**
   - Use Postman or curl to test POST /api/chat endpoint
   - Verify OpenAI integration with sample messages
   - Test error handling (invalid API key, network errors)
   - Verify knowledge base loading and context injection

2. **Test Cases:**
   - Valid chat message returns AI response
   - Empty message returns validation error
   - CORS headers present for frontend origin
   - Health check endpoint returns 200 OK
   - Environment variables loaded correctly

**Frontend Testing:**
1. **Manual UI Testing:**
   - Test chat interface with real backend
   - Verify message sending and display
   - Test loading states
   - Test error states (backend down, network error)
   - Test responsive design on mobile/desktop

2. **Component Testing:**
   - Verify Shadcn UI components render correctly
   - Test button click handlers
   - Test input field validation
   - Test scroll behavior on new messages

**Integration Testing:**
1. Start backend on localhost:8000
2. Start frontend on localhost:5173
3. Send test messages and verify:
   - Messages appear in chat interface
   - AI responds with knowledge base information
   - Timestamps display correctly
   - No CORS errors in browser console

**Acceptance Criteria:**
- User can send message and receive AI response within 5 seconds
- Chat interface displays message history correctly
- No console errors during normal operation
- Mobile responsive design works on 375px+ screens

---

## Deployment Strategy

**Development Environment:**
- Backend: `poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Frontend: `npm run dev` (Vite dev server on port 5173)
- Both services run locally for development

**Production Deployment:**

**Backend: Render.com**
- Web Service with automatic Poetry detection
- Free tier available for MVP testing
- Auto-deploy from Git repository (main branch)
- Environment variables configured in dashboard
- Automatic HTTPS
- Build command: `poetry install`
- Start command: `poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Frontend: Vercel**
- Automatic Vite build detection
- Free tier with unlimited bandwidth
- Auto-deploy from Git repository (main branch)
- Environment variable VITE_API_BASE_URL set to Render backend URL
- CDN distribution included
- Automatic HTTPS with custom domain support
- Build command: `npm run build`
- Output directory: `dist`

**Deployment Checklist:**
1. Push code to GitHub repository
2. **Backend (Render.com):**
   - Create new Web Service
   - Connect GitHub repository
   - Set environment variables in dashboard:
     - OPENAI_API_KEY (from OpenAI dashboard)
     - PERSON_NAME (your full name)
     - OPENAI_MODEL=gpt-4-turbo-preview
     - KNOWLEDGE_BASE_PATH=../data/knowledge_base.txt
   - Note the deployed URL (e.g., https://alter-ego-api.onrender.com)
3. **Frontend (Vercel):**
   - Import GitHub repository
   - Set environment variable:
     - VITE_API_BASE_URL (Render backend URL from step 2)
   - Deploy
   - Note the deployed URL (e.g., https://alter-ego.vercel.app)
4. **Update backend CORS:**
   - Add Vercel frontend URL to CORS_ORIGINS in Render dashboard
5. Test production deployment with sample chat messages
6. Monitor OpenAI API usage in OpenAI dashboard
7. (Optional) Configure custom domains in Render and Vercel

**Environment Variables for Production:**
```
# Backend (Render.com dashboard)
OPENAI_API_KEY=sk-prod-...
PERSON_NAME=Your Full Name
OPENAI_MODEL=gpt-4-turbo-preview
KNOWLEDGE_BASE_PATH=../data/knowledge_base.txt
CORS_ORIGINS=https://alter-ego.vercel.app

# Frontend (Vercel dashboard)
VITE_API_BASE_URL=https://alter-ego-api.onrender.com
```
