# AGENTS.md - Frontend

## General Guidelines for AI Agents

This document provides general guidelines for AI agents working on the Next.js frontend. For project-specific context, see `CLAUDE.md`.

---

## Core Principles

### 1. Type Safety

- **TypeScript strict mode** — No `any` without explicit justification
- **No `object` types** — Use `Record<string, unknown>` or specific interfaces
- **Explicit return types** — All functions must declare return types
- **Props interfaces** — Every component must have a defined props interface
- **Use `type` for object shapes, `interface` for extendable contracts**
- **Component-type location (AE-0144, enforced)** — Inside `src/modules/**`, a
  component (`*.tsx`) or hook (`use-*.ts`) file MUST NOT declare object-shape
  types (`interface Foo {}` / `type Foo = {}`) inline; put them in a colocated
  `types.ts`. Gated by `npm run lint:component-types` (in `npm run lint` +
  `gates.sh frontend:component-types`) with a down-only baseline. See
  [`src/modules/README.md`](src/modules/README.md#component-type-location-convention-ae-0144).

### 1a. No Unchecked Indexed Access (AE-0324, enforced)

- **`Record[key]` / array indexing must be guarded** — an unguarded lookup
  destructure crashed the whole admin blog listing in prod (AE-0295:
  `BLOG_POST_BADGE_COLORS[color]` with a non-key status → `TypeError`).
- Gated by `npm run lint:strict-index` (in `npm run lint` → the frontend lint
  gate): `tsc -p tsconfig.strict-index.json` (`noUncheckedIndexedAccess: true`
  over the whole tree) against the DOWN-ONLY per-file baseline
  `scripts/strict-index-baseline.json`. New files must be clean; baselined
  legacy files must not grow; ratchet down with `npm run strict-index:baseline`
  after fixing errors. When the baseline hits 0, fold the flag into
  `tsconfig.json` (follow-up AE-0329).
- Write `map[key]?.field ?? fallback` (or narrow with `in`/`has`) — do NOT
  silence the flag with `!` non-null assertions (that is gaming; reviewers
  treat a net-new `!` on indexed access as suspect).

### 1b. No Copy-Paste Duplication (AE-0149, enforced)

- **Source-scoped jscpd gate** — `src/**` `.ts`/`.tsx` files are scanned for
  copy-paste clones. New source duplication above the threshold in
  `frontend/.jscpd.json` **fails the build**. Extract shared logic into a hook,
  util, or helper instead of duplicating.
- Gated by `npm run lint:dup` (in `npm run lint` + `gates.sh frontend:duplication`
  - the `frontend / Duplication` CI job).
- The `threshold` may only **ratchet DOWN** — raising it is flagged as
  gate-loosening by `scripts/ci/check-integrity.sh`.
- **Test/spec/story files are excluded** from the blocking gate by design
  (acceptable boilerplate); egregious test duplication is surfaced by the
  non-blocking `frontend / Duplication (tests, advisory)` job (AE-0151).
- Run it locally: `cd frontend && npm run lint:dup`.

### 1c. No Dead Exports (AE-0152, enforced)

- **knip dead-export gate** — exported symbols/types that nothing imports are
  flagged. A NEW unused export in a file you changed **fails the build**. Delete
  it, or wire it up; do not leave orphaned exports (ESLint only sees unused
  locals, not cross-file exports).
- **Scope:** unused **exports/types** only (`--include exports,types,nsExports,
nsTypes`) — the orphaned-constant class. Unused-**file** detection is out of
  scope for now (noisier; a possible future advisory).
- Gated by `npm run lint:dead-code` (`gates.sh frontend:dead-code` + the
  `frontend / Dead code` CI job). Identity-keyed baseline lives in
  `frontend/scripts/dead-code-baseline.json` (`type|file|symbol`).
- **Day-one blocking is changed-file-scoped:** net-new findings in PR-changed
  files block; pre-existing/unchanged-file findings are **advisory** (the
  grandfathered debt) until the full-tree flip.
- The baseline is **down-only** — raising its `count` is flagged by
  `scripts/ci/check-integrity.sh`. Regenerate (only to ratchet DOWN, after
  removing dead code) with `npm run dead-code:baseline`.
- **Operating model:** the gate adds a `knip` run to CI (~seconds; owned by the
  frontend quality-gates workflow). **Flip to full-tree blocking** (set
  `DEAD_CODE_FULL_TREE_BLOCKING=1` in the gate) once the grandfathered `count`
  reaches 0 — at that point there is no advisory debt left to defer.
- Run it locally: `cd frontend && npm run lint:dead-code`.

### 2. No Magic Strings

- Extract all string literals to named constants
- Constants live in `src/constants/` directory
- Use `UPPER_SNAKE_CASE` for constant names
- API endpoints, route paths, status values, error messages — all as constants

### 3. No Hardcoded Text

- **All user-facing text must use i18n**
- Use `useTranslations` hook for client components
- Use `getTranslations` for server components
- Translation keys follow pattern: `feature.component.key`

### 4. Component Architecture

- **Single Responsibility** — Each component does one thing well
- **Composition over Inheritance** — Build complex UIs from simple pieces
- **Props Down, Events Up** — Clear data flow
- **DRY** — Extract shared logic
- **Generic components are dumb** — No state, receive everything via props

### 5. Testing is Non-Negotiable

- **90%+ branch coverage** — Focus on branches, not lines
- **Gherkin scenarios first** — Write `.feature` files before tests, for
  **behavior-changing** work. **Pure refactors and CI/config/tooling tickets** may
  substitute focused unit tests + the gate's seeded-violation test, provided the
  ticket documents no-behavior-change + reviewer sign-off (AE-0153; full rule in
  root `CLAUDE.md` → Testing). Default to requiring a `.feature` when in doubt.
- **Test behavior, not implementation**
- **Mock external dependencies with MSW**

---

## File Organization

### Naming Conventions

| Type       | Convention           | Example             |
| ---------- | -------------------- | ------------------- |
| Components | PascalCase           | `UserProfile.tsx`   |
| Hooks      | camelCase with `use` | `useAuth.ts`        |
| Utils      | camelCase            | `formatDate.ts`     |
| Constants  | UPPER_SNAKE_CASE     | `API_ENDPOINTS`     |
| Types      | PascalCase           | `UserTypes.ts`      |
| Tests      | Same name + `.test`  | `Button.test.tsx`   |
| Features   | kebab-case           | `message-input.tsx` |

### Directory Structure

```
src/
├── app/                    # Next.js App Router
├── components/
│   ├── ui/                 # Base primitives (dumb, tested)
│   ├── forms/              # Form-specific components
│   ├── layout/             # Layout components
│   └── providers/          # Context providers
├── features/               # Feature-based modules
│   ├── chat/
│   │   ├── components/     # Chat-specific components
│   │   ├── hooks/          # Chat hooks
│   │   └── types/          # Chat types
│   └── knowledge/
│       ├── components/
│       ├── hooks/
│       └── types/
├── lib/
│   ├── utils.ts            # Utility functions
│   └── api-client.ts       # API client with Zod validation
├── hooks/                  # Global custom hooks
├── schemas/                # Zod validation schemas
├── constants/              # Application constants
├── i18n/                   # Internationalization
│   ├── locales/
│   │   ├── en.json
│   │   └── pt.json
│   └── config.ts
└── types/                  # TypeScript type definitions

tests/
├── unit/                   # Component and hook unit tests
├── e2e/                    # Playwright E2E tests
├── features/               # Gherkin .feature files
├── fixtures/               # Test fixtures
└── setup.ts                # Test setup
```

---

## React Best Practices

### Component Structure

```typescript
// 1. Imports
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

// 2. Types
interface ComponentProps {
  title: string;
  onAction: () => void;
}

// 3. Component
export function Component({ title, onAction }: ComponentProps) {
  const t = useTranslations("component");

  const handleClick = () => {
    onAction();
  };

  return (
    <div>
      <h1>{title}</h1>
      <button onClick={handleClick}>{t("action")}</button>
    </div>
  );
}
```

### Server vs Client Components

| Use Server Components | Use Client Components               |
| --------------------- | ----------------------------------- |
| Data fetching         | React hooks (useState, useEffect)   |
| Static content        | Browser APIs (localStorage, window) |
| Accessing backend     | Event handlers (onClick, onChange)  |
|                       | Third-party DOM libraries           |

### Early Returns

```typescript
// Good
export function MessageItem({ message }: MessageItemProps) {
  if (message.role === "system") return null;

  const isUser = message.role === "user";
  if (!isUser) return <AssistantMessage content={message.content} />;

  return <UserMessage content={message.content} />;
}

// Bad
export function MessageItem({ message }: MessageItemProps) {
  if (message.role !== "system") {
    if (message.role === "user") {
      return <UserMessage content={message.content} />;
    } else {
      return <AssistantMessage content={message.content} />;
    }
  }
  return null;
}
```

---

## Testing Guidelines

### Test Structure

```typescript
// Feature: Chat Interface
// Scenario: User sends a message
//   Given a chat interface with an active conversation
//   When the user types a message and clicks send
//   Then the message appears in the message list
//   And the input field is cleared
describe("ChatInterface", () => {
  it("displays sent message and clears input", async () => {
    const user = userEvent.setup();
    render(<ChatInterface />);

    const input = screen.getByRole("textbox");
    await user.type(input, "Hello");
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(screen.getByText("Hello")).toBeInTheDocument();
    expect(input).toHaveValue("");
  });
});
```

### Gherkin-Style Comments

All tests must reference their Gherkin scenario:

```typescript
// Feature: Knowledge Base
// Scenario: Upload document successfully
//   Given a valid PDF file
//   When the user uploads the file
//   Then the document appears in the list
//   And the status shows "processing"
it("uploads document and shows processing status", async () => { ... });
```

---

## Code Review Checklist

Before submitting code:

- [ ] All tests pass
- [ ] No TypeScript errors
- [ ] No ESLint warnings
- [ ] Code formatted with Prettier (let the pre-commit hook do this — avoid
      `git commit --no-verify`; see the `--no-verify` policy in root `CLAUDE.md` →
      Git & Commits, AE-0168)
- [ ] Components have prop types
- [ ] Functions have return types
- [ ] No hardcoded text (use i18n)
- [ ] No magic strings (use constants)
- [ ] No files over 400 lines
- [ ] Tests cover all branches
- [ ] No console.log statements
- [ ] No commented-out code
- [ ] Documentation updated (if needed)

---

_These guidelines ensure consistency and quality across the frontend codebase._
