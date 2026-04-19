# CLAUDE.md - Frontend

Next.js React frontend for the Alter-Ego RAG system.

## Project Structure

```
frontend/
├── src/
│   ├── app/              # Next.js App Router
│   ├── components/       # Reusable UI components
│   │   ├── ui/           # Base primitives (Button, Input, etc.)
│   │   └── layout/       # Layout components
│   ├── features/         # Feature-based modules
│   │   ├── chat/
│   │   └── knowledge/
│   ├── lib/              # Utilities and API client
│   ├── schemas/          # Zod validation schemas
│   ├── i18n/             # Internationalization
│   └── constants/        # Application constants
├── tests/
│   ├── unit/             # Component and hook unit tests
│   ├── e2e/              # Playwright E2E tests
│   └── fixtures/         # Test fixtures and helpers
└── package.json
```

## Tech Stack

| Category | Technology |
|----------|-----------|
| Framework | Next.js 16 (App Router) |
| React | React 19 |
| Language | TypeScript 5 (strict) |
| Styling | Tailwind CSS v4 |
| State | TanStack Query v5 |
| Forms | React Hook Form + Zod |
| Testing | Vitest + RTL (unit), Playwright (E2E) |
| UI Primitives | Radix UI |
| i18n | next-intl |
| Animation | Framer Motion |

## Development Commands

```bash
npm run dev                      # Development server (Turbopack)
npm run build                    # Production build
npm run test                     # Unit tests (Vitest)
npm run test:coverage            # Coverage report (90%+ required)
npm run test:e2e                 # E2E tests (Playwright)
npm run typecheck                # TypeScript check
npm run lint                     # ESLint
```

## Code Rules

### TypeScript Strict Mode
- **No `any` types** — Use explicit, specific types
- **No `object` types** — Use `Record<string, unknown>` or specific interfaces
- **All functions must have explicit return types**
- **Use `type` for object shapes, `interface` for extendable contracts**
- **Props interfaces defined for all components**

### Constants
- **No magic strings** — Extract all string literals to named constants
- **Constants in `src/constants/`** — One file per domain
- **Naming**: `UPPER_SNAKE_CASE`
- Example: `API_ENDPOINTS.CHAT`, `ROUTE_PATHS.KNOWLEDGE`

### i18n
- **No hardcoded text in components** — All user-facing strings use i18n
- **Translation files in `src/i18n/locales/`**
- **Use `useTranslations` hook** for client components
- **Use `getTranslations` for server components**

### Component Architecture
- **Server Components by default** — Add `'use client'` only when needed
- **Max 400 lines per file** — Split large components
- **Max 20 lines per function** — Extract complex logic
- **Named exports only** — `export function Button()`, not default exports
- **Generic components are dumb** — No state, receive everything via props
- **Use CVA for component variants**
- **Compound components for complex UI patterns**

### NEVER use useEffect for Data Fetching
- Use Server Components for initial data
- Use TanStack Query for client-side data
- Use React 19 `use()` hook with Suspense

### File Organization
- **Constants in `src/constants/`** — Separate files per domain
- **Types in same folder as component** — Co-located `types.ts` files
- **Tests in `tests/` folder** — Not co-located with components
- **Interfaces in their own files** — Separate from implementations

### Testing
- **90%+ branch coverage required** — Focus on branches, not just lines
- **Gherkin-first** — Write `.feature` files before implementing tests
  - See `tests/features/` for scenario definitions
  - Tests must reference Gherkin scenarios in comments
- **Test behavior, not implementation**
- **Use MSW for API mocking**
- **Unit tests in `tests/unit/`**, **E2E tests in `tests/e2e/`**

### Styling
- **Tailwind CSS utility classes** — No custom CSS unless necessary
- **`cn()` utility** for conditional classes
- **Dark mode support** via `.dark` class
- **OKLCH color system**

### Control Flow
- **Early returns** — Use guard clauses, avoid nested `if` statements
- **Complex conditionals** — Use object maps instead of switch/if chains:
  ```typescript
  const statusColors: Record<DocumentStatus, string> = {
    completed: "bg-green-100 text-green-800",
    processing: "bg-yellow-100 text-yellow-800",
    pending: "bg-blue-100 text-blue-800",
    failed: "bg-red-100 text-red-800",
  };
  ```

### Accessibility
- **WCAG 2.1 AA compliance**
- **All interactive elements keyboard accessible**
- **ARIA labels where needed**
- **`aria-hidden="true"` on decorative icons**
- **`role` attributes for semantic structure**

## Documentation References

- **Implementation Plan**: `../docs/frontend/`
- **API Contract**: `../docs/architecture/API_CONTRACT.md`
- **Style Guide**: `../docs/guides/style-guide-2026.md`
- **Testing Guide**: `../docs/guides/VITEST_TESTING_GUIDE.md`
- **Zod Guide**: `../docs/guides/ZOD_VALIDATION_GUIDE.md`
