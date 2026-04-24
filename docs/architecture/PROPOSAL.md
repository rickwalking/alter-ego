# RAG System Frontend - Comprehensive Project Proposal

## Project Overview

This document outlines the standards, architecture, and best practices for building a modern React-based frontend for your RAG (Retrieval-Augmented Generation) system about yourself. The goal is to create a beautiful, accessible, and performant SSR application.

---

## 1. Project Stack

| Category | Technology | Purpose |
|----------|------------|---------|
| Framework | Next.js 15+ (App Router) | SSR, Server Components, routing |
| Language | TypeScript 5+ | Type safety |
| Styling | Tailwind CSS v4 | Utility-first CSS |
| State Management | TanStack Query v5 | Server state, caching |
| Validation | Zod | Runtime type validation |
| Testing | Vitest + RTL | Unit & integration tests |
| Animation | Framer Motion | Smooth interactions |
| Icons | Lucide React | Consistent iconography |

---

## 2. CLAUDE.md / AGENTS.md Standards

### File Structure

```
project-root/
├── CLAUDE.md                    # Primary project instructions (Claude-specific)
├── AGENTS.md                    # Generic agent instructions
├── .claude/
│   └── CLAUDE.md                # Alternative location
```

### CLAUDE.md Best Practices

**Key Differences:**
- **CLAUDE.md**: Claude Code specific, project-specific or user-specific
- **AGENTS.md**: Generic guidelines for any AI coding agent

**Recommended Structure:**

```markdown
# CLAUDE.md

@AGENTS.md  # Import generic guidelines if exists

## Project Overview
Brief description of this RAG system project.

## Tech Stack
- Next.js 15 with App Router
- React 19
- Tailwind CSS v4
- TanStack Query
- Zod

## Development Commands
| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Production build |
| `npm run test` | Run Vitest tests |
| `npm run test:coverage` | Run tests with coverage |
| `npm run lint` | Run ESLint |

## Architecture Guidelines

### Component Rules
- Use Server Components by default
- Add `'use client'` only when needed (hooks, browser APIs)
- Keep Client Components small and compose them inside Server Components
- NEVER use `useEffect` for data fetching (use Server Components or TanStack Query)

### File Organization
```
app/
├── (marketing)/       # Route groups
├── (dashboard)/
├── api/               # API routes
├── layout.tsx         # Root layout
├── page.tsx           # Home page
├── globals.css
components/
├── ui/                # shadcn/ui components
├── forms/             # Form components
├── layout/            # Layout components
├── providers/         # Context providers
features/
├── chat/              # Feature-based organization
├── knowledge-base/
└── profile/
```

### Code Standards
- TypeScript strict mode required
- No `any` types without explicit justification
- All functions must have explicit return types
- Props interfaces must be defined for all components
- Maximum 300 lines per file
- Maximum 20 lines per function
- Use named exports over default exports

### Testing Requirements
- 90%+ coverage required for all logic
- Test behavior, not implementation
- Use MSW for API mocking
- Integration tests for feature workflows

### Critical Rules
- Always validate external data with Zod
- Use React Compiler (automatic memoization)
- Implement proper error boundaries
- All UI components must be accessible (ARIA, keyboard navigation)
- Use `use server` for server actions
- Protect server-only code with `server-only` package

## Documentation Map
| Topic | Location |
|-------|----------|
| Component patterns | `docs/components.md` |
| API integration | `docs/api.md` |
| Styling guide | `docs/styling.md` |
| Testing guide | `docs/testing.md` |
```

### Recommended File Size
- Target: Under **200 lines** per CLAUDE.md file
- Split into `.claude/rules/` directory for path-specific rules

---

## 3. React 2026 Best Practices

### Server Components First

```tsx
// ✅ CORRECT: Server Component fetches data directly
// app/page.tsx
async function getKnowledgeBase() {
  const res = await fetch('https://api.example.com/kb', {
    next: { revalidate: 60 }
  });
  return res.json();
}

export default async function HomePage() {
  const kb = await getKnowledgeBase(); // Server-side fetch

  return (
    <div>
      <h1>My Knowledge Base</h1>
      <KnowledgeList data={kb} />
      <ChatInterface /> {/* Client Component for interactivity */}
    </div>
  );
}
```

### React 19 Features

```tsx
// useActionState for form handling
function ChatForm() {
  const [error, submitAction, isPending] = useActionState(
    async (prevState, formData) => {
      const message = formData.get('message');
      const result = await sendMessage(message);
      if (result.error) return result.error;
      return null;
    },
    null
  );

  return (
    <form action={submitAction}>
      <input name="message" />
      <button disabled={isPending}>Send</button>
      {error && <p>{error}</p>}
    </form>
  );
}

// useOptimistic for immediate UI updates
function MessageList({ messages }) {
  const [optimisticMessages, addOptimisticMessage] = useOptimistic(
    messages,
    (state, newMessage) => [...state, { ...newMessage, sending: true }]
  );

  async function sendMessage(formData) {
    const message = formData.get('message');
    addOptimisticMessage({ text: message });
    await api.sendMessage(message);
  }
}

// use() for consuming promises
function MessageContent({ messagePromise }) {
  const message = use(messagePromise); // Can be used conditionally!
  return <div>{message.content}</div>;
}
```

### Component Boundaries

| Use Server Component | Use Client Component |
|---------------------|---------------------|
| Data fetching | Event handlers (onClick, onChange) |
| Backend resource access | Browser APIs (localStorage, window) |
| API keys/secrets | React hooks (useState, useEffect*) |
| Reducing bundle size | Third-party libraries needing DOM |

*Note: `useEffect` should be minimized, see Section 6

### File Organization

```
app/
├── (marketing)/
│   ├── layout.tsx
│   ├── page.tsx
│   └── about/
│       └── page.tsx
├── (app)/
│   ├── layout.tsx
│   ├── dashboard/
│   │   ├── page.tsx
│   │   ├── loading.tsx    # Suspense fallback
│   │   └── error.tsx      # Error boundary
│   ├── chat/
│   │   └── page.tsx
│   └── settings/
│       └── page.tsx
├── api/
│   └── chat/
│       └── route.ts
├── layout.tsx
├── page.tsx
├── loading.tsx
├── error.tsx
└── globals.css
```

---

## 4. Component Creation Best Practices

### Component Template

```tsx
// components/ui/Button/Button.tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

// Types
export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

// Styles with CVA
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/90',
        outline: 'border border-input bg-background hover:bg-accent',
        ghost: 'hover:bg-accent',
        danger: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4 text-base',
        lg: 'h-12 px-6 text-lg',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

// Component
export function Button({
  className,
  variant,
  size,
  isLoading,
  leftIcon,
  rightIcon,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <Spinner className="mr-2" />
      ) : (
        leftIcon
      )}
      {children}
      {rightIcon}
    </button>
  );
}
```

### Compound Components Pattern

```tsx
// components/ui/Accordion/Accordion.tsx
const AccordionContext = createContext<{
  openItem: string | null;
  setOpenItem: (id: string | null) => void;
} | null>(null);

function useAccordion() {
  const context = useContext(AccordionContext);
  if (!context) throw new Error('Must be used within Accordion');
  return context;
}

export function Accordion({ children }: { children: React.ReactNode }) {
  const [openItem, setOpenItem] = useState<string | null>(null);

  return (
    <AccordionContext.Provider value={{ openItem, setOpenItem }}>
      <div className="divide-y">{children}</div>
    </AccordionContext.Provider>
  );
}

export function AccordionItem({
  id,
  children
}: {
  id: string;
  children: React.ReactNode
}) {
  return <div className="py-2">{children}</div>;
}

export function AccordionTrigger({
  itemId,
  children
}: {
  itemId: string;
  children: React.ReactNode
}) {
  const { openItem, setOpenItem } = useAccordion();
  const isOpen = openItem === itemId;

  return (
    <button
      onClick={() => setOpenItem(isOpen ? null : itemId)}
      className="flex w-full items-center justify-between"
    >
      {children}
      <ChevronDown className={cn('transition-transform', isOpen && 'rotate-180')} />
    </button>
  );
}

export function AccordionContent({
  itemId,
  children
}: {
  itemId: string;
  children: React.ReactNode
}) {
  const { openItem } = useAccordion();
  if (openItem !== itemId) return null;

  return <div className="pt-2">{children}</div>;
}

// Usage
<Accordion>
  <AccordionItem id="faq1">
    <AccordionTrigger itemId="faq1">What is RAG?</AccordionTrigger>
    <AccordionContent itemId="faq1">RAG stands for...</AccordionContent>
  </AccordionItem>
</Accordion>
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `UserProfile`, `ChatMessage` |
| Props | camelCase | `userName`, `isLoading` |
| Hooks | camelCase with `use` prefix | `useChat`, `useKnowledgeBase` |
| Constants | UPPER_SNAKE_CASE | `API_BASE_URL` |
| Types/Interfaces | PascalCase | `UserProps`, `ChatConfig` |
| Event handlers | `on` prefix + verb | `onClick`, `onSubmit` |

---

## 5. Vitest Testing (90%+ Coverage)

### Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],

    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/**/*.test.{ts,tsx}',
        'src/**/__mocks__/**',
        'src/**/types/**',
        'src/main.tsx',
        'src/App.tsx',
      ],
      thresholds: {
        lines: 90,
        functions: 90,
        branches: 85,
        statements: 90,
      },
    },

    clearMocks: true,
    mockReset: true,
    restoreMocks: true,
    pool: 'forks',
  },
});
```

### Setup File

```typescript
// src/test/setup.ts
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

afterEach(() => {
  cleanup();
});

// Mock browser APIs
global.matchMedia = vi.fn().mockImplementation((query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
}));

class MockIntersectionObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: MockIntersectionObserver,
});
```

### Component Testing Pattern

```tsx
// components/ui/Button/Button.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from './Button';

describe('Button', () => {
  it('renders with default props', () => {
    render(<Button>Click me</Button>);

    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('handles click events', async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(<Button onClick={handleClick}>Click me</Button>);

    await user.click(screen.getByRole('button'));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when loading', async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(<Button isLoading onClick={handleClick}>Loading</Button>);

    const button = screen.getByRole('button');
    expect(button).toBeDisabled();

    await user.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('applies variant styles correctly', () => {
    const { rerender } = render(<Button variant="primary">Primary</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-primary');

    rerender(<Button variant="danger">Danger</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-destructive');
  });

  it('has correct ARIA attributes', () => {
    render(<Button aria-label="Submit form">Submit</Button>);

    expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Submit form');
  });
});
```

### Custom Render with Providers

```tsx
// src/test/utils.tsx
import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
    },
  });

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  const queryClient = createTestQueryClient();

  return {
    ...render(ui, {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      ),
      ...options,
    }),
    queryClient,
  };
}

export * from '@testing-library/react';
export { renderWithProviders as render };
```

### MSW for API Mocking

```typescript
// src/test/mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/knowledge', () => {
    return HttpResponse.json([
      { id: '1', title: 'About Me', content: '...' },
      { id: '2', title: 'My Projects', content: '...' },
    ]);
  }),

  http.post('/api/chat', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: Date.now(),
      response: `Response to: ${body.message}`,
    });
  }),
];

// src/test/mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);

// src/test/setup.ts
import { beforeAll, afterAll, afterEach } from 'vitest';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

---

## 6. Preventing useEffect Usage

### useEffect Replacement Decision Matrix

| Scenario | Solution | Example |
|----------|----------|---------|
| Data fetching | Server Components / TanStack Query | `const { data } = useQuery({...})` |
| Derived state | Compute during render / useMemo | `const total = items.reduce(...)` |
| External store sync | useSyncExternalStore | `useOnlineStatus()` |
| Browser API subscription | useSyncExternalStore | `useLocalStorage()` |
| DOM measurements | useLayoutEffect (rare) | Tooltip positioning |
| Form submission | Event handlers | `onSubmit={handleSubmit}` |

### Examples

```tsx
// ❌ BAD: useEffect for derived state
function Cart({ items }) {
  const [total, setTotal] = useState(0);

  useEffect(() => {
    setTotal(items.reduce((acc, item) => acc + item.price, 0));
  }, [items]);

  return <div>Total: ${total}</div>;
}

// ✅ GOOD: Compute during render
function Cart({ items }) {
  const total = items.reduce((acc, item) => acc + item.price, 0);
  return <div>Total: ${total}</div>;
}

// ✅ BETTER: Extract to custom hook with memoization
function useCartSummary(items: CartItem[]) {
  return useMemo(() => {
    const total = items.reduce((acc, item) => acc + item.price * item.quantity, 0);
    const itemCount = items.reduce((acc, item) => acc + item.quantity, 0);
    return { total, itemCount, isFreeShipping: total > 50 };
  }, [items]);
}
```

```tsx
// ❌ BAD: useEffect for data fetching
function UserProfile({ userId }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetchUser(userId).then(setUser);
  }, [userId]);

  return <div>{user?.name}</div>;
}

// ✅ GOOD: Server Component (no effect needed!)
async function UserProfile({ userId }) {
  const user = await getUser(userId); // Server-side fetch
  return <div>{user.name}</div>;
}

// ✅ GOOD: TanStack Query for client-side
function UserProfile({ userId }) {
  const { data: user } = useQuery({
    queryKey: ['user', userId],
    queryFn: () => fetchUser(userId),
  });

  return <div>{user?.name}</div>;
}
```

```tsx
// ❌ BAD: useEffect for browser API
function OnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return <div>{isOnline ? 'Online' : 'Offline'}</div>;
}

// ✅ GOOD: useSyncExternalStore
function useOnlineStatus() {
  return useSyncExternalStore(
    (callback) => {
      window.addEventListener('online', callback);
      window.addEventListener('offline', callback);
      return () => {
        window.removeEventListener('online', callback);
        window.removeEventListener('offline', callback);
      };
    },
    () => navigator.onLine,
    () => true // Server snapshot
  );
}

function OnlineStatus() {
  const isOnline = useOnlineStatus();
  return <div>{isOnline ? 'Online' : 'Offline'}</div>;
}
```

---

## 7. React Compiler Configuration

### Installation

```bash
npm install -D babel-plugin-react-compiler@latest
```

### Next.js Configuration

```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactCompiler: true,
  // Or with options:
  // reactCompiler: {
  //   compilationMode: 'annotation',
  // },
};

module.exports = nextConfig;
```

### ESLint Configuration

```javascript
// eslint.config.js
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    plugins: { 'react-hooks': reactHooks },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
];
```

### Benefits

With React Compiler enabled, you can **remove manual memoization**:

```tsx
// BEFORE: Manual memoization required
const ExpensiveComponent = memo(function ExpensiveComponent({ data, onClick }) {
  const processed = useMemo(() => expensiveProcess(data), [data]);
  const handleClick = useCallback(() => onClick(processed), [onClick, processed]);

  return <div onClick={handleClick}>{processed}</div>;
});

// AFTER: Compiler handles memoization automatically
function ExpensiveComponent({ data, onClick }) {
  const processed = expensiveProcess(data); // Automatically memoized

  return <div onClick={() => onClick(processed)}>{processed}</div>;
}
```

### When to Keep Manual Memoization

```tsx
// Keep manual memoization for:
// 1. Effect dependencies that need stable references
function Component({ config }) {
  const stableConfig = useMemo(() => ({
    apiUrl: config.apiUrl,
    timeout: config.timeout
  }), [config.apiUrl, config.timeout]);

  useEffect(() => {
    setupService(stableConfig);
  }, [stableConfig]);
}

// 2. Cross-component memoization
const MemoizedChild = memo(Child);
```

---

## 8. Zod Validation Patterns

### Basic Schema Definition

```typescript
// schemas/user.ts
import { z } from 'zod';

export const userSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(2).max(100),
  email: z.string().email(),
  age: z.number().int().min(0).max(150).optional(),
  role: z.enum(['user', 'admin', 'moderator']),
  createdAt: z.date(),
});

export const createUserSchema = userSchema.omit({ id: true, createdAt: true });
export const updateUserSchema = createUserSchema.partial();

// Infer types
export type User = z.infer<typeof userSchema>;
export type CreateUserInput = z.infer<typeof createUserSchema>;
export type UpdateUserInput = z.infer<typeof updateUserSchema>;
```

### Form Validation with React Hook Form

```tsx
// components/ChatInput/ChatInput.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const chatMessageSchema = z.object({
  message: z.string().min(1, 'Message is required').max(1000, 'Message too long'),
  attachments: z.array(z.instanceof(File)).max(5, 'Max 5 attachments').optional(),
});

type ChatMessageForm = z.infer<typeof chatMessageSchema>;

export function ChatInput({ onSubmit }: { onSubmit: (data: ChatMessageForm) => void }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<ChatMessageForm>({
    resolver: zodResolver(chatMessageSchema),
    defaultValues: {
      message: '',
      attachments: [],
    },
  });

  const handleFormSubmit = async (data: ChatMessageForm) => {
    await onSubmit(data);
    reset();
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)}>
      <textarea
        {...register('message')}
        placeholder="Type your message..."
        rows={3}
      />
      {errors.message && <span>{errors.message.message}</span>}

      <button type="submit" disabled={isSubmitting}>
        Send
      </button>
    </form>
  );
}
```

### API Response Validation

```typescript
// lib/api-client.ts
import { z } from 'zod';

const apiResponseSchema = z.object({
  success: z.boolean(),
  data: z.unknown(),
  message: z.string().optional(),
});

export async function apiCall<T>(
  url: string,
  schema: z.ZodSchema<T>,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(url, options);
  const json = await response.json();

  // Validate response structure
  const responseResult = apiResponseSchema.safeParse(json);
  if (!responseResult.success) {
    throw new Error('Invalid API response structure');
  }

  if (!responseResult.data.success) {
    throw new Error(responseResult.data.message || 'API request failed');
  }

  // Validate data
  const dataResult = schema.safeParse(responseResult.data.data);
  if (!dataResult.success) {
    console.error('Data validation failed:', dataResult.error.issues);
    throw new Error('Invalid data from API');
  }

  return dataResult.data;
}

// Usage
const knowledgeItemSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  content: z.string(),
  tags: z.array(z.string()),
  createdAt: z.string().datetime(),
});

const knowledge = await apiCall(
  '/api/knowledge',
  z.array(knowledgeItemSchema)
);
```

### Environment Variable Validation

```typescript
// env.ts
import { z } from 'zod';

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']),
  NEXT_PUBLIC_API_URL: z.string().url(),
  DATABASE_URL: z.string().startsWith('postgresql://'),
  OPENAI_API_KEY: z.string().startsWith('sk-'),
});

export const env = envSchema.parse(process.env);
```

---

## 9. Style, Typography & Color Schema

### Color System (OKLCH Color Space)

```css
/* globals.css */
@import "tailwindcss";

@theme {
  /* Primary - Indigo */
  --color-primary-50: oklch(0.97 0.014 278);
  --color-primary-100: oklch(0.93 0.032 278);
  --color-primary-200: oklch(0.88 0.059 278);
  --color-primary-300: oklch(0.81 0.105 278);
  --color-primary-400: oklch(0.71 0.165 278);
  --color-primary-500: oklch(0.62 0.214 278);
  --color-primary-600: oklch(0.55 0.245 278);
  --color-primary-700: oklch(0.49 0.243 278);
  --color-primary-800: oklch(0.42 0.199 278);
  --color-primary-900: oklch(0.38 0.146 278);
  --color-primary-950: oklch(0.28 0.091 278);

  /* Semantic Colors */
  --color-success: oklch(0.72 0.219 150);
  --color-success-foreground: oklch(0.98 0.005 150);

  --color-warning: oklch(0.84 0.16 84);
  --color-warning-foreground: oklch(0.28 0.07 46);

  --color-error: oklch(0.58 0.253 18);
  --color-error-foreground: oklch(0.98 0.005 18);

  --color-info: oklch(0.72 0.14 250);
  --color-info-foreground: oklch(0.98 0.005 250);

  /* Neutral - Zinc */
  --color-gray-50: oklch(0.985 0 0);
  --color-gray-100: oklch(0.967 0.001 286);
  --color-gray-200: oklch(0.92 0.004 286);
  --color-gray-300: oklch(0.871 0.006 286);
  --color-gray-400: oklch(0.705 0.015 286);
  --color-gray-500: oklch(0.552 0.016 285);
  --color-gray-600: oklch(0.442 0.017 285);
  --color-gray-700: oklch(0.37 0.013 285);
  --color-gray-800: oklch(0.274 0.006 286);
  --color-gray-900: oklch(0.21 0.006 285);
  --color-gray-950: oklch(0.141 0.005 285);
}
```

### Typography System

```css
@theme {
  /* Fonts */
  --font-sans: Inter, ui-sans-serif, system-ui, sans-serif;
  --font-display: "Cal Sans", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  /* Fluid Type Scale */
  --text-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.8125rem);
  --text-sm: clamp(0.8125rem, 0.75rem + 0.3vw, 0.875rem);
  --text-base: clamp(0.9375rem, 0.875rem + 0.3vw, 1rem);
  --text-lg: clamp(1.0625rem, 0.95rem + 0.55vw, 1.125rem);
  --text-xl: clamp(1.125rem, 0.975rem + 0.75vw, 1.25rem);
  --text-2xl: clamp(1.25rem, 1rem + 1.25vw, 1.5rem);
  --text-3xl: clamp(1.5rem, 1.125rem + 1.875vw, 1.875rem);
  --text-4xl: clamp(1.75rem, 1.25rem + 2.5vw, 2.25rem);
  --text-5xl: clamp(2rem, 1.25rem + 3.75vw, 3rem);
}
```

### Dark Mode Implementation

```tsx
// providers/theme-provider.tsx
'use client';

import { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resolvedTheme: 'light' | 'dark';
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('system');
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    const root = window.document.documentElement;
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';

    const resolved = theme === 'system' ? systemTheme : theme;
    setResolvedTheme(resolved);

    root.classList.remove('light', 'dark');
    root.classList.add(resolved);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};
```

### Color Usage Guidelines

| Purpose | Light Mode | Dark Mode |
|---------|------------|-----------|
| Background | gray-50 / white | gray-950 / gray-900 |
| Surface | white / gray-50 | gray-900 / gray-800 |
| Text Primary | gray-900 | gray-50 |
| Text Secondary | gray-600 | gray-400 |
| Border | gray-200 | gray-800 |
| Primary | primary-600 | primary-500 |

---

## 10. Project Structure Summary

```
my-rag-app/
├── app/
│   ├── (marketing)/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── about/
│   ├── (app)/
│   │   ├── layout.tsx
│   │   ├── dashboard/
│   │   ├── chat/
│   │   └── settings/
│   ├── api/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── loading.tsx
│   ├── error.tsx
│   └── globals.css
├── components/
│   ├── ui/                    # shadcn/ui components
│   ├── forms/                 # Form-specific components
│   ├── layout/                # Layout components
│   └── providers/             # Context providers
├── features/
│   ├── chat/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── types/
│   └── knowledge-base/
├── hooks/                     # Global custom hooks
├── lib/
│   ├── utils.ts               # cn() and utilities
│   └── api-client.ts          # API client with Zod
├── schemas/                   # Zod schemas
├── types/                     # TypeScript types
├── test/
│   ├── setup.ts
│   ├── mocks/
│   └── utils.tsx
├── vitest.config.ts
├── next.config.js
├── tailwind.config.ts
└── package.json
```

---

## 11. Key Principles Summary

### Code Quality
- [ ] TypeScript strict mode enabled
- [ ] No `useEffect` for data fetching
- [ ] Server Components by default
- [ ] React Compiler enabled
- [ ] 90%+ test coverage
- [ ] Zod validation for all external data
- [ ] Accessible components (ARIA, keyboard navigation)

### Performance
- [ ] React Compiler for automatic memoization
- [ ] Streaming with Suspense boundaries
- [ ] Code splitting at route level
- [ ] Image optimization with next/image
- [ ] Font optimization with next/font

### Developer Experience
- [ ] CLAUDE.md for project context
- [ ] Feature-based organization
- [ ] Barrel exports for clean imports
- [ ] Storybook for component documentation
- [ ] ESLint + Prettier for code consistency

---

*This proposal was generated based on 2026 React best practices and modern tooling recommendations.*
