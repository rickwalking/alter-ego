# CLAUDE.md - Frontend

Next.js React frontend for the Alter-Ego RAG system.

## Project Structure

```
frontend/
├── src/
│   ├── app/              # Next.js App Router
│   ├── components/       # Atomic design component library
│   │   ├── atoms/        # Primitives (NeonButton, NeonInput, NeonBadge, …)
│   │   ├── molecules/    # Composed units (NeonCard, NeonModal, NeonStatCard, …)
│   │   ├── organisms/    # Sections (NeonSidebar, NeonKanbanBoard, NeonTopBar, …)
│   │   └── layout/       # App shell layouts
│   ├── features/         # Feature-based modules
│   ├── lib/              # Utilities and API client
│   ├── schemas/          # Zod validation schemas (neon-*.ts)
│   ├── constants/        # Application constants (neon.ts, api.ts, …)
│   └── i18n/             # Internationalization
├── .storybook/           # Storybook 9 (CSF stories co-located in components/)
├── tests/
│   ├── features/         # Gherkin scenario definitions (*.feature)
│   ├── unit/             # Legacy unit test paths (if any)
│   └── e2e/              # Playwright E2E tests
└── package.json
```

### Component Import Conventions

| Layer | Import path | Example |
|-------|-------------|---------|
| Atoms | `@/components/atoms/neon-button` | `NeonButton` |
| Molecules | `@/components/molecules/neon-card` | `NeonCard`, `NeonCardHeader` |
| Organisms | `@/components/organisms/neon-sidebar` | `NeonSidebar` |
| Barrel | `@/components/atoms` (optional) | Re-export from `index.ts` |

- **Do not** import from `@/components/ui` — shadcn layer removed; use `Neon*` components directly.
- **Do not** use `../` for cross-folder imports — use `@/` path alias.
- **Presentation components** must not call `useQuery` or `fetch` — data flows via props from feature hooks/pages.

## Tech Stack

| Category | Technology |
|----------|-----------|
| Framework | Next.js 16 (App Router) |
| React | React 19 |
| Language | TypeScript 5 (strict) |
| Styling | Tailwind CSS v4 + CSS variables in `globals.css` `@theme` |
| State | TanStack Query v5 |
| Forms | React Hook Form + Zod |
| Testing | Vitest + RTL (unit), Playwright (E2E), StrykerJS (mutation) |
| Visual docs | Storybook 9 (`npm run storybook`) |
| UI Primitives | Custom Neon design system (CVA + compound components) |
| i18n | next-intl |
| Animation | Framer Motion |

## Legacy v1.0 removal

Do **not** reintroduce `ChatInterface`, `TopicForm`, `/(create)/*` routes, or `features/dashboard/chat/mock-data.ts`.

- **Plan (component inventory, phases, replacements):** [`docs/plans/frontend-legacy-removal.md`](../docs/plans/frontend-legacy-removal.md)
- **Gherkin:** `tests/features/frontend-legacy-removal.feature`
- **CI guards:** `npm run check:legacy` (blocking), `npm run check:legacy-inventory` (Phase 1 advisory)

## Development Commands

```bash
npm run dev                      # Development server (Turbopack)
npm run build                    # Production build
npm run test                     # Unit tests (Vitest)
npm run test:coverage            # Coverage report (90%+ project target)
npm run test:e2e                 # E2E tests (Playwright)
npm run test:mutate              # StrykerJS mutation testing
npm run typecheck                # TypeScript check
npm run check:legacy             # Block v1 imports in dashboard app
npm run check:legacy-inventory   # Phase 1 scheduled file deletions
npm run lint                     # ESLint
npm run storybook                # Storybook dev server
npm run build-storybook          # Static Storybook build
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
- **Neon tokens** — Colors, borders, shadows in `src/constants/neon.ts` and `globals.css` `@theme`
- **Constants in `src/constants/`** — One file per domain
- **Naming**: `UPPER_SNAKE_CASE`
- Example: `API_ENDPOINTS.CHAT`, `NEON_CYAN`, `BG_CARD`

### i18n
- **No hardcoded text in components** — All user-facing strings use i18n
- **Translation files in `src/i18n/locales/`**
- **Use `useTranslations` hook** for client components
- **Use `getTranslations` for server components**

### Component Architecture
- **Atomic design** — atoms → molecules → organisms; pages compose organisms
- **Server Components by default** — Add `'use client'` only when needed
- **Max 400 lines per file** — Split large pages into subcomponents (see `dashboard/chat/`, `dashboard/rubrics/`)
- **Max 20 lines per function** — Extract complex logic
- **Named exports only** — `export function Button()`, not default exports (pages may use default export)
- **Generic components are dumb** — No state, receive everything via props
- **Use CVA for component variants**
- **Compound components for complex UI patterns**

### NEVER use useEffect for Data Fetching
- Use Server Components for initial data
- Use TanStack Query for client-side data
- Use React 19 `use()` hook with Suspense

### File Organization
- **Constants in `src/constants/`** — Separate files per domain
- **Zod schemas in `src/schemas/`** — `neon-*.ts` for design system props
- **Tests co-located with components** — `*.test.tsx` next to source (excluded from `tsc` via stories pattern)
- **Gherkin in `tests/features/`** — Reference scenarios in test comments
- **Storybook stories** — `*.stories.tsx` co-located; excluded from ESLint and `tsc`

### Testing
- **90%+ branch coverage** — Project target; neon components should have strong unit tests
- **Gherkin-first** — Write `.feature` files before implementing tests
  - See `tests/features/neon-*.feature` for design system scenarios
  - Tests must reference Gherkin scenarios in comments
- **Test behavior, not implementation**
- **Use MSW for API mocking**
- **Mutation testing (StrykerJS)** — ADR-005 thresholds in `stryker.conf.json`:
  - UI components: break **30%**, low **50%**, high **65%**
  - Business logic hooks: higher bars (see ADR-005)
  - Do **not** add neon component tests to `ignorePatterns` — that hides weak assertions
  - Run scoped: `npx stryker run --mutate "src/components/atoms/neon-button.tsx"`

### Styling
- **Tailwind CSS utility classes** — Prefer theme tokens (`text-neon-cyan`, `bg-bg-card`)
- **CSS variables** — Shared shadows/borders in `globals.css`; reference via `var(--shadow-neon-button)`
- **`cn()` utility** for conditional classes
- **Dark mode** — Neon shell is dark-first via `@theme` tokens

### Control Flow
- **Early returns** — Use guard clauses, avoid nested `if` statements
- **Complex conditionals** — Use object maps instead of switch/if chains

### Workflow UI Patterns
- **Approval gates** — Show clear action buttons (Approve / Request Changes / Reject)
- **Phase indicators** — Visual progress through workflow stages
- **Timeout warnings** — Show countdown for human review deadlines
- **Conflict resolution** — Diff view when concurrent edits detected
- **Version history** — Side-by-side comparison with restore capability
- **AI suggestions** — Inline tooltips with "Apply" / "Dismiss" actions
- **Source attribution** — Show which sources were used for each content section

### Accessibility
- **WCAG 2.1 AA compliance**
- **All interactive elements keyboard accessible**
- **ARIA labels where needed**
- **`aria-hidden="true"` on decorative icons**
- **`role` attributes for semantic structure**

## Architecture Decision Records

See `../docs/decisions/` for all ADRs:
- [ADR-001: Adopt MADR for ADRs](../docs/decisions/0001-adopt-madr-for-adrs.md)
- [ADR-003: Implement Persona-Driven AI Content](../docs/decisions/0003-implement-persona-driven-ai-content.md)
- [ADR-004: Adopt Event-Driven Architecture](../docs/decisions/0004-adopt-event-driven-architecture.md)
- [ADR-005: Adopt Mutation Testing](../docs/decisions/0005-adopt-mutation-testing.md)

## Documentation References

- **Neon migration plan**: `../docs/plans/neon-shell-migration-complete.md`
- **API Contract**: `../docs/architecture/API_CONTRACT.md`
- **Style Guide**: `../docs/guides/style-guide-2026.md`
- **Testing Guide**: `../docs/guides/VITEST_TESTING_GUIDE.md`
- **Zod Guide**: `../docs/guides/ZOD_VALIDATION_GUIDE.md`
- **LangGraph Deep Agents Guide**: `../docs/architecture/langchain-deep-agents-guide.md`
- **Professional Pivot Plan**: `../docs/PROFESSIONAL_PIVOT_PLAN.md`
