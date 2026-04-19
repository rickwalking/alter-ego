# RAG Frontend Implementation Plan

## Project Overview
Building a modern, SSR-enabled RAG (Retrieval-Augmented Generation) frontend about yourself using React 19, Next.js 15, Tailwind CSS v4, and TanStack Query v5.

**Last Updated**: April 2026

---

## Phase 0: Project Setup & Tooling (Day 1)

### 0.1 Initialize Project
- [ ] Create Next.js 15 project with App Router
- [ ] Configure TypeScript with strict mode
- [ ] Set up directory structure
- [ ] Initialize Git repository

**Command:**
```bash
npx create-next-app@latest my-rag-app --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --turbopack
```

**Deliverable**: Working Next.js dev server at `localhost:3000`

### 0.2 Configure Development Tools
- [ ] Install ESLint with React Compiler rules
- [ ] Install Prettier with Tailwind plugin
- [ ] Configure path aliases (`@/components`, `@/lib`, etc.)
- [ ] Set up Husky pre-commit hooks
- [ ] Create `.editorconfig`

**Deliverable**: Linting and formatting on save working

### 0.3 Install Core Dependencies (Updated April 2026)

```bash
# ============================================
# FRAMEWORK & CORE (Latest Stable)
# ============================================
# Next.js 15.x with React 19
npm install next@^15.3.0 react@^19.1.0 react-dom@^19.1.0

# TypeScript 5.8+ (latest)
npm install -D typescript@^5.8.3 @types/react@^19.1.2 @types/react-dom@^19.1.2 @types/node@^22.14.0

# ============================================
# UI & STYLING (Tailwind CSS v4)
# ============================================
# Tailwind CSS v4 (new engine)
npm install tailwindcss@^4.1.3 @tailwindcss/postcss@^4.1.3

# Component styling utilities
npm install class-variance-authority@^0.7.1
npm install clsx@^2.1.1
npm install tailwind-merge@^3.2.0

# Icons
npm install lucide-react@^0.488.0

# ============================================
# STATE MANAGEMENT (TanStack Query v5)
# ============================================
npm install @tanstack/react-query@^5.74.0
npm install @tanstack/react-query-devtools@^5.74.0
npm install @tanstack/react-query-nextjs-experimental@^5.74.0

# ============================================
# FORMS & VALIDATION (Latest)
# ============================================
npm install react-hook-form@^7.55.0
npm install @hookform/resolvers@^5.0.1
npm install zod@^3.24.3

# ============================================
# ANIMATION (Latest)
# ============================================
npm install framer-motion@^12.7.4

# ============================================
# DATE UTILITIES (Latest)
# ============================================
npm install date-fns@^4.1.0

# ============================================
# UI PRIMITIVES (Radix - Accessible)
# ============================================
npm install @radix-ui/react-dialog@^1.1.10
npm install @radix-ui/react-dropdown-menu@^2.1.10
npm install @radix-ui/react-select@^2.2.2
npm install @radix-ui/react-tabs@^1.1.7
npm install @radix-ui/react-tooltip@^1.2.3
npm install @radix-ui/react-popover@^1.1.10
npm install @radix-ui/react-slot@^1.2.0

# ============================================
# REACT COMPILER (Babel Plugin)
# ============================================
npm install -D babel-plugin-react-compiler@^19.0.0-beta-ebf51a3-20250411

# ============================================
# TESTING (Vitest 3.x + Testing Library)
# ============================================
npm install -D vitest@^3.1.1
npm install -D @vitest/ui@^3.1.1
npm install -D @testing-library/react@^16.3.0
npm install -D @testing-library/jest-dom@^6.6.3
npm install -D @testing-library/user-event@^14.6.1
npm install -D @testing-library/dom@^10.4.0
npm install -D jsdom@^26.0.0
npm install -D @vitejs/plugin-react@^4.4.0
npm install -D vite-tsconfig-paths@^5.1.4

# MSW v2 for API mocking
npm install -D msw@^2.7.4

# ============================================
# CODE QUALITY (Latest)
# ============================================
npm install -D eslint@^9.24.0
npm install -D eslint-config-next@^15.3.0
npm install -D eslint-plugin-react-hooks@^6.0.0
npm install -D prettier@^3.5.3
npm install -D prettier-plugin-tailwindcss@^0.6.11
npm install -D @types/eslint@^9.6.1

# ============================================
# DEVELOPMENT TOOLS
# ============================================
npm install -D husky@^9.1.7
npm install -D lint-staged@^15.5.1
npm install -D @commitlint/config-conventional@^19.8.0
npm install -D @commitlint/cli@^19.8.0

# ============================================
# PERFORMANCE & MONITORING (Optional)
# ============================================
npm install @vercel/analytics@^1.5.0
npm install @vercel/speed-insights@^1.2.0

# ============================================
# SERVER ACTIONS & BACKEND (Latest)
# ============================================
npm install server-only@^0.0.1
npm install client-only@^0.0.1
```

### 0.4 Configure Tailwind CSS v4 (Latest Syntax)

Create `app/globals.css`:
```css
@import "tailwindcss";

@theme {
  /* Font families */
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
  
  /* Primary colors - Indigo */
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
  
  /* Semantic colors */
  --color-success: oklch(0.72 0.219 150);
  --color-warning: oklch(0.84 0.16 84);
  --color-error: oklch(0.58 0.253 18);
  --color-info: oklch(0.72 0.14 250);
  
  /* Animation */
  --animate-fade-in: fade-in 0.2s ease-out;
  --animate-slide-up: slide-up 0.3s ease-out;
  
  @keyframes fade-in {
    0% { opacity: 0; }
    100% { opacity: 1; }
  }
  
  @keyframes slide-up {
    0% { opacity: 0; transform: translateY(10px); }
    100% { opacity: 1; transform: translateY(0); }
  }
}

@custom-variant dark (&:where(.dark, .dark *));
```

**Deliverable**: Tailwind classes working with custom theme

### 0.5 Configure Testing Infrastructure (Vitest 3.x)

Create `vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: ['babel-plugin-react-compiler'],
      },
    }),
    tsconfigPaths(),
  ],
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

**Deliverable**: `npm test` runs successfully with coverage report

### 0.6 Configure Next.js with React Compiler

Create `next.config.ts`:
```typescript
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactCompiler: true,
  experimental: {
    // Enable React 19 features
    reactCompiler: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },
};

export default nextConfig;
```

### 0.7 Create Documentation Files
- [ ] Create `CLAUDE.md` with project context
- [ ] Create `AGENTS.md` with general guidelines
- [ ] Document component standards
- [ ] Create API integration guide

**Deliverable**: Documentation files in project root

---

## Phase 1: Core UI Components & Design System (Days 2-3)

### 1.1 Set Up Theme Provider (Next.js 15 compatible)

Create `components/providers/theme-provider.tsx`:
```typescript
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
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const root = window.document.documentElement;
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
    
    const resolved = theme === 'system' ? systemTheme : theme;
    setResolvedTheme(resolved);
    
    root.classList.remove('light', 'dark');
    root.classList.add(resolved);
  }, [theme]);

  // Prevent hydration mismatch
  if (!mounted) {
    return <>{children}</>;
  }

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

**Deliverable**: Theme switching works across the app

### 1.2 Create Base UI Components
Build these components using React 19 + Tailwind v4:

#### Layout Components
- [ ] `Container` - Responsive width wrapper
- [ ] `Stack` - Vertical spacing component  
- [ ] `Grid` - CSS Grid wrapper
- [ ] `Flex` - Flexbox wrapper

#### Typography Components
- [ ] `Heading` - H1-H6 with consistent styling
- [ ] `Text` - Body text with size/weight variants
- [ ] `Label` - Form labels

#### Interactive Components (with Radix primitives)
- [ ] `Button` - Using CVA for variants
- [ ] `Input` - Text input with states
- [ ] `Textarea` - Multi-line input
- [ ] `Select` - Using Radix Select
- [ ] `Checkbox` - Boolean input
- [ ] `Switch` - Toggle input

#### Feedback Components
- [ ] `Badge` - Status indicators
- [ ] `Alert` - Warning/error/info messages
- [ ] `Skeleton` - Loading placeholders
- [ ] `Spinner` - Loading indicator
- [ ] `Tooltip` - Using Radix Tooltip

#### Overlay Components (Radix-based)
- [ ] `Dialog` - Using Radix Dialog
- [ ] `Sheet` - Side panel
- [ ] `DropdownMenu` - Using Radix DropdownMenu
- [ ] `Popover` - Using Radix Popover

**Deliverable**: Storybook or demo page showing all components

### 1.3 Create Utility Functions
- [ ] `cn()` - Class name merging with tailwind-merge
- [ ] `formatDate()` - Date formatting with date-fns
- [ ] `truncate()` - Text truncation
- [ ] `debounce()` - Function debouncing
- [ ] `throttle()` - Function throttling

### 1.4 Add Unit Tests for Components
- [ ] Test all UI components (90%+ coverage)
- [ ] Test utility functions
- [ ] Test theme provider

**Deliverable**: All tests passing with coverage report

---

## Phase 2: Chat Interface & Messages (Days 4-5)

### 2.1 Create Chat Layout (Next.js 15 App Router)

Create `app/chat/layout.tsx`:
```typescript
export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen">
      <aside className="w-64 border-r">
        {/* Conversation sidebar */}
      </aside>
      <main className="flex-1 flex flex-col">
        {children}
      </main>
    </div>
  );
}
```

Create `app/chat/page.tsx`:
```typescript
import { ChatInterface } from '@/features/chat/components/chat-interface';

export default function ChatPage() {
  return <ChatInterface />;
}
```

**Deliverable**: Visual chat interface structure

### 2.2 Build Message Components (React 19 features)
- [ ] `Message` component with user vs AI styling
- [ ] `MessageList` with virtualization (@tanstack/react-virtual v3)
- [ ] `MessageInput` with auto-resize
- [ ] `MessageBubble` with markdown support (react-markdown v10)
- [ ] `TypingIndicator` for AI responses
- [ ] `MessageTimestamp` component
- [ ] `MessageActions` (copy, edit, delete)

### 2.3 Implement Chat State Management (TanStack Query v5)
- [ ] Create chat hooks:
  - `useChat()` - Main chat state
  - `useMessages()` - Message list
  - `useSendMessage()` - Send mutation
- [ ] Implement optimistic updates
- [ ] Add message history management

### 2.4 Add Chat Features
- [ ] Message sending with React 19 `useActionState`
- [ ] Message editing
- [ ] Message deletion
- [ ] Copy to clipboard
- [ ] File attachments (react-dropzone v14)

### 2.5 Chat Interface Testing
- [ ] Unit tests for message components
- [ ] Integration tests for chat flow
- [ ] Test message input validation

**Deliverable**: Fully functional chat interface (UI only)

---

## Phase 3: Knowledge Base Management (Days 6-7)

### 3.1 Knowledge Base Layout
- [ ] Create knowledge base dashboard
- [ ] Design document list view
- [ ] Create document detail view
- [ ] Add search/filter interface

### 3.2 Document Components
- [ ] `DocumentCard` - Preview card for documents
- [ ] `DocumentList` - Grid/list view toggle
- [ ] `DocumentUploader` - File upload with react-dropzone
- [ ] `DocumentViewer` - Document content viewer
- [ ] `DocumentEditor` - Inline editing
- [ ] `TagManager` - Tagging system

### 3.3 Knowledge Base Features
- [ ] Document CRUD operations (UI)
- [ ] File upload with progress
- [ ] Document categorization
- [ ] Tag management
- [ ] Search functionality

### 3.4 Knowledge Base Testing
- [ ] Unit tests for document components
- [ ] Test upload functionality
- [ ] Test search/filter logic

**Deliverable**: Knowledge base management UI complete

---

## Phase 4: Backend Integration (Days 8-10)

### 4.1 Set Up API Client

Create `lib/api-client.ts`:
```typescript
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
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  
  const json = await response.json();
  const result = apiResponseSchema.safeParse(json);
  
  if (!result.success || !result.data.success) {
    throw new Error(result.data?.message || 'API request failed');
  }
  
  const dataResult = schema.safeParse(result.data.data);
  if (!dataResult.success) {
    throw new Error('Invalid data from API');
  }
  
  return dataResult.data;
}
```

### 4.2 Configure TanStack Query v5

Create `components/providers/query-provider.tsx`:
```typescript
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState } from 'react';

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5, // 5 minutes
        refetchOnWindowFocus: false,
        retry: 2,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

### 4.3 Implement Chat API Integration
- [ ] Create chat API hooks:
  - `useSendMessage()`
  - `useGetMessages()`
  - `useStreamResponse()` (for Server-Sent Events)
- [ ] Implement SSE streaming
- [ ] Add optimistic updates with TanStack Query
- [ ] Handle loading and error states

**Deliverable**: Real chat functionality working

### 4.4 Implement Knowledge Base API Integration
- [ ] Create document API hooks
- [ ] Implement file upload with progress
- [ ] Add document search API
- [ ] Connect UI to real data

### 4.5 API Integration Testing
- [ ] Mock API responses with MSW v2
- [ ] Test API hooks
- [ ] Test error handling

**Deliverable**: Full backend integration complete

---

## Phase 5: Testing & Quality Assurance (Days 11-12)

### 5.1 Unit Testing (Vitest 3.x)
- [ ] Achieve 90%+ line coverage
- [ ] Test all components
- [ ] Test all hooks
- [ ] Test all utility functions
- [ ] Test Zod schemas

### 5.2 Integration Testing
- [ ] Test chat flow end-to-end
- [ ] Test knowledge base workflows
- [ ] Test search functionality
- [ ] Test file upload flow

### 5.3 E2E Testing (Playwright 1.51)
- [ ] Set up Playwright v1.51.x
- [ ] Write E2E tests for critical paths
- [ ] Test responsive design

```bash
npm install -D @playwright/test@^1.51.1
npx playwright install
```

### 5.4 Accessibility Audit
- [ ] Run axe-core audit
- [ ] Test keyboard navigation
- [ ] Verify ARIA labels
- [ ] Test screen reader compatibility

**Deliverable**: All tests passing, accessibility compliant

---

## Phase 6: Performance Optimization (Day 13)

### 6.1 Enable React Compiler
- [ ] Configure Next.js 15 with React Compiler (already done in Phase 0)
- [ ] Verify automatic memoization
- [ ] Remove manual memoization where appropriate

### 6.2 Optimize Loading Performance
- [ ] Implement route-based code splitting
- [ ] Lazy load heavy components with `React.lazy()`
- [ ] Optimize images with `next/image`
- [ ] Add `loading.tsx` for all routes
- [ ] Use `next/font` for font optimization

### 6.3 Optimize Runtime Performance
- [ ] Virtualize long lists (@tanstack/react-virtual v3)
- [ ] Debounce search inputs
- [ ] Implement intersection observer
- [ ] Use `useDeferredValue` for search

### 6.4 SEO & Meta Tags
- [ ] Add metadata to all pages
- [ ] Create sitemap.ts (Next.js 15 native)
- [ ] Add robots.ts (Next.js 15 native)
- [ ] Implement Open Graph tags

**Deliverable**: Lighthouse score 90+ in all categories

---

## Phase 7: Deployment & Documentation (Day 14)

### 7.1 Production Build
- [ ] Configure production environment variables
- [ ] Optimize build output
- [ ] Run production build locally

```bash
npm run build
npm start
```

### 7.2 Deployment Setup
- [ ] Deploy to Vercel (recommended for Next.js 15)
- [ ] Configure deployment pipeline
- [ ] Set up environment variables
- [ ] Configure custom domain

### 7.3 Monitoring & Analytics
- [ ] Add Vercel Analytics
- [ ] Add Vercel Speed Insights
- [ ] Set up error tracking (optional: Sentry v9)

### 7.4 Final Documentation
- [ ] Write README with setup instructions
- [ ] Document API endpoints
- [ ] Create component documentation
- [ ] Write deployment guide

### 7.5 Project Handoff
- [ ] Final code review
- [ ] Clean up unused code
- [ ] Remove console.logs
- [ ] Verify all tests pass
- [ ] Tag release version

**Deliverable**: Production-ready application deployed

---

## Implementation Timeline

| Phase | Days | Focus Area | Key Dependencies |
|-------|------|------------|------------------|
| Phase 0 | 1 | Project setup | Next.js 15, React 19, Tailwind v4 |
| Phase 1 | 2-3 | UI components | Radix UI, CVA, Tailwind v4 |
| Phase 2 | 4-5 | Chat interface | TanStack Query v5, React 19 hooks |
| Phase 3 | 6-7 | Knowledge base | File upload, forms |
| Phase 4 | 8-10 | Backend integration | API client, Zod |
| Phase 5 | 11-12 | Testing | Vitest 3.x, MSW v2, Playwright |
| Phase 6 | 13 | Performance | React Compiler, Next.js optimizations |
| Phase 7 | 14 | Deployment | Vercel, monitoring |

**Total Duration**: 2 weeks (14 days)

---

## Package Versions Summary (April 2026)

| Category | Package | Version |
|----------|---------|---------|
| Framework | next | ^15.3.0 |
| Framework | react | ^19.1.0 |
| Framework | react-dom | ^19.1.0 |
| Language | typescript | ^5.8.3 |
| Styling | tailwindcss | ^4.1.3 |
| Styling | @tailwindcss/postcss | ^4.1.3 |
| UI | class-variance-authority | ^0.7.1 |
| UI | lucide-react | ^0.488.0 |
| State | @tanstack/react-query | ^5.74.0 |
| Forms | react-hook-form | ^7.55.0 |
| Forms | @hookform/resolvers | ^5.0.1 |
| Validation | zod | ^3.24.3 |
| Animation | framer-motion | ^12.7.4 |
| Date | date-fns | ^4.1.0 |
| Primitives | @radix-ui/* | ^1.x |
| Testing | vitest | ^3.1.1 |
| Testing | @testing-library/react | ^16.3.0 |
| Testing | msw | ^2.7.4 |
| Testing | playwright | ^1.51.1 |
| Compiler | babel-plugin-react-compiler | ^19.0.0-beta |
| Quality | eslint | ^9.24.0 |
| Quality | prettier | ^3.5.3 |

---

## Key Changes from Previous Versions

### React 19 (vs 18)
- **New hooks**: `useActionState`, `useOptimistic`, `use()`
- **Ref as prop**: No more `forwardRef` needed
- **Ref cleanup**: Functions can be returned from ref callbacks
- **Context**: Context can be rendered as provider directly
- **Document metadata**: Native `<title>`, `<meta>` support

### Next.js 15 (vs 14)
- **Turbopack**: Fast dev server (now stable)
- **React Compiler**: Automatic memoization
- **Server Actions**: Enhanced caching and revalidation
- **Partial Prerendering**: Static + dynamic in same route
- **Metadata API**: Simplified metadata handling

### Tailwind CSS v4 (vs v3)
- **New engine**: Faster compilation
- **@theme directive**: Native CSS-based configuration
- **OKLCH colors**: Perceptually uniform color space
- **No config file**: Configuration in CSS

### TanStack Query v5 (vs v4)
- **Simplified API**: Cleaner hook interfaces
- **Better TypeScript**: Improved type inference
- **Streaming**: Better support for React 19 Suspense

---

## Next Steps

1. ✅ Review this plan with updated dependencies
2. Run `npx create-next-app@latest` to start
3. Install all dependencies from Phase 0.3
4. Begin with Phase 0 implementation

Ready to start building? 🚀
