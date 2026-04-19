# Alter-Ego Frontend

A modern, AI-powered RAG (Retrieval-Augmented Generation) chat application frontend built with **Next.js 16**, **React 19**, and **TypeScript**. Provides an intelligent conversational interface backed by a personal knowledge base, enabling users to chat with an AI that understands their documents.

Part of the **Alter-Ego** full-stack RAG system — see the [root README](../README.md) for the complete architecture.

## Features

- **AI-Powered Chat** — Natural conversations with an AI that understands your knowledge base via RAG
- **Knowledge Management** — Upload, organize, and manage documents (PDF, TXT, MD)
- **Real-time Messaging** — Interactive chat interface with message history and streaming responses
- **Internationalization** — Full i18n support via `next-intl` (English, Portuguese ready)
- **Dark Mode** — Toggle between light and dark themes with system preference detection
- **Responsive Design** — Works on desktop, tablet, and mobile
- **Accessibility First** — WCAG 2.1 AA compliant with ARIA labels and keyboard navigation
- **Type Safety** — End-to-end Zod validation with TypeScript strict mode

## Tech Stack

| Category | Technology |
|----------|------------|
| Framework | [Next.js 16](https://nextjs.org/) (App Router) |
| Language | [TypeScript](https://www.typescriptlang.org/) (strict mode) |
| Styling | [Tailwind CSS v4](https://tailwindcss.com/) |
| State Management | [TanStack Query v5](https://tanstack.com/query) |
| Forms | [React Hook Form](https://react-hook-form.com/) + [Zod](https://zod.dev/) |
| UI Components | [Radix UI](https://www.radix-ui.com/) primitives |
| i18n | [next-intl v4](https://next-intl.dev/) |
| Unit Testing | [Vitest](https://vitest.dev/) + [React Testing Library](https://testing-library.com/) |
| E2E Testing | [Playwright](https://playwright.dev/) |
| API Mocking | [MSW](https://mswjs.io/) |
| Icons | [Lucide React](https://lucide.dev/) |
| Animation | [Framer Motion](https://www.framer.com/motion/) |
| Analytics | [Vercel Analytics](https://vercel.com/analytics) + [Speed Insights](https://vercel.com/speed-insights) |

## Quick Start

### Prerequisites

- Node.js 22+
- npm
- Backend API running on port 8000 (see [root project](../README.md))

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |

## Development

### Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server with Turbopack |
| `npm run build` | Create production build |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |
| `npm run typecheck` | Run TypeScript type checking |
| `npm test` | Run unit tests in watch mode |
| `npm run test:coverage` | Run tests with coverage report |
| `npm run test:e2e` | Run Playwright E2E tests |

### Project Structure

```
src/
├── app/                          # Next.js App Router
│   ├── (public)/                 # Public route group (no auth required)
│   │   ├── layout.tsx            # Public layout with Header
│   │   └── page.tsx              # Landing page (/)
│   ├── (dashboard)/              # Dashboard route group
│   │   ├── layout.tsx            # Dashboard layout with Header
│   │   ├── chat/                 # Chat page (/chat)
│   │   └── knowledge/            # Knowledge base page (/knowledge)
│   ├── layout.tsx                # Root layout (providers only)
│   ├── not-found.tsx             # Custom 404 page
│   ├── robots.ts                 # Dynamic robots.txt
│   ├── sitemap.ts                # Dynamic sitemap.xml
│   └── globals.css               # Global styles
├── components/
│   ├── ui/                       # Base UI primitives (button, card, input...)
│   ├── layout/                   # Layout components (header, container...)
│   └── providers/                # Context providers (theme, query, i18n)
├── features/                     # Feature-based modules
│   ├── chat/                     # Chat feature
│   │   ├── components/           # Chat-specific components
│   │   ├── hooks/                # Chat hooks (use-chat, use-websocket-chat)
│   │   └── types/                # Chat types
│   └── knowledge/                # Knowledge base feature
│       ├── components/           # Document management components
│       ├── hooks/                # Document hooks
│       └── types/                # Document types
├── hooks/                        # Global custom hooks
├── lib/                          # Utilities
│   ├── api-client.ts             # Typed API client with Zod validation
│   └── utils.ts                  # Shared utilities (cn, formatDate, debounce...)
├── schemas/                      # Zod validation schemas
├── constants/                    # Application constants
├── i18n/                         # Internationalization
│   ├── locales/                  # Translation files
│   └── request.ts                # Server-side i18n config
└── test/                         # Test utilities
    ├── fixtures/                 # Test data
    ├── mocks/                    # MSW handlers
    └── setup.ts                  # Vitest setup

tests/
├── e2e/                          # Playwright E2E tests
└── features/                     # Gherkin .feature files
```

### Architecture Decisions

- **Server Components First** — Pages and layouts use Server Components by default; Client Components only when interactivity is needed
- **React Compiler** — Automatic memoization without manual `useMemo`/`useCallback`
- **Route Groups** — `(public)` and `(dashboard)` groups for shared layouts without URL segments
- **TanStack Query** — Server state management with caching, optimistic updates, and background refetching
- **Zod Validation** — Runtime type safety for all API responses and form inputs
- **Feature-Based Organization** — Code organized by feature domain, not by type
- **Gherkin-First Testing** — `.feature` files define behavior before implementation

## Testing

### Unit Tests

```bash
# Run all tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests once (CI mode)
npm test -- --run
```

Tests follow Gherkin-style descriptions:

```typescript
// Feature: Chat Interface
// Scenario: User sends a message
//   Given a chat interface with an active conversation
//   When the user types a message and clicks send
//   Then the message appears in the message list
describe("MessageInput", () => {
  it("calls onSend with message text and clears input", async () => { ... });
});
```

### E2E Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run with UI
npm run test:e2e:ui
```

E2E tests cover:
- Home page rendering and navigation
- Chat interface interaction
- Knowledge base document management
- Cross-page navigation
- 404 error page

## Code Standards

See [AGENTS.md](./AGENTS.md) and [CLAUDE.md](./CLAUDE.md) for detailed guidelines. Key rules:

- **TypeScript strict mode** — No `any`, no `object`, explicit return types
- **No magic strings** — All literals extracted to `src/constants/`
- **No hardcoded text** — All user-facing text via i18n
- **90%+ branch coverage** — Focus on branches, not lines
- **Max 400 lines per file** — Split large files into focused modules
- **Early returns** — Guard clauses over nested conditionals
- **Conventional commits** — `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`

## Deployment

### Docker

```bash
# Build and run
docker build -t alter-ego-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=https://api.your-domain.com alter-ego-frontend
```

### Vercel

```bash
# Install Vercel CLI and deploy
npm i -g vercel
vercel
```

### Full Stack (Docker Compose)

From the project root:

```bash
docker-compose up --build
```

This starts PostgreSQL, the FastAPI backend, and the Next.js frontend together.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/amazing-feature`
3. Write Gherkin scenarios in `tests/features/`
4. Implement the feature with tests
5. Ensure `npm run lint`, `npm run typecheck`, and `npm test` all pass
6. Commit with conventional commit message
7. Open a Pull Request

## Related

- [Backend API](../backend/) — FastAPI + LangChain + Pinecone RAG backend
- [Architecture Docs](../docs/) — System design and API contracts
- [Deployment Guide](../docs/deployment/) — Production deployment instructions

---

Built with Next.js, React, and TypeScript
