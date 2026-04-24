# Comprehensive Vitest Testing Guide
## Achieving 90%+ Code Coverage with Best Practices

---

## Table of Contents
1. [Vitest Configuration Best Practices](#1-vitest-configuration-best-practices)
2. [Testing React Components (RTL + Vitest)](#2-testing-react-components-rtl--vitest)
3. [Testing Server Components](#3-testing-server-components)
4. [Testing Hooks and Utilities](#4-testing-hooks-and-utilities)
5. [Mocking Strategies](#5-mocking-strategies)
6. [Coverage Configuration and Thresholds](#6-coverage-configuration-and-thresholds)
7. [Test Organization and Naming Conventions](#7-test-organization-and-naming-conventions)
8. [Integration Testing Patterns](#8-integration-testing-patterns)
9. [E2E Testing Considerations](#9-e2e-testing-considerations)
10. [Common Pitfalls and How to Avoid Them](#10-common-pitfalls-and-how-to-avoid-them)

---

## 1. Vitest Configuration Best Practices

### Recommended Configuration File

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    // Environment
    environment: 'jsdom', // or 'happy-dom', 'node'
    globals: true, // Enable global APIs (describe, test, expect)

    // File patterns
    include: ['**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/cypress/**',
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build}.config.*',
    ],

    // Coverage configuration
    coverage: {
      provider: 'v8', // 'v8' (faster) or 'istanbul' (more compatible)
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/**/*.test.{ts,tsx}',
        'src/**/__mocks__/**',
        'src/**/types/**',
        'src/**/constants/**',
        'src/main.tsx',
        'src/App.tsx', // Entry point, usually not tested
      ],
      thresholds: {
        lines: 90,
        functions: 90,
        branches: 85, // Slightly lower for complex conditionals
        statements: 90,
      },
    },

    // Performance and reliability
    pool: 'forks', // 'forks' (default, more stable), 'threads' (faster)
    poolOptions: {
      forks: {
        singleFork: false,
      },
    },

    // Timeouts
    testTimeout: 10000,
    hookTimeout: 10000,
    teardownTimeout: 5000,

    // Setup files
    setupFiles: ['./src/test/setup.ts'],

    // Mock behavior
    clearMocks: true,
    mockReset: true,
    restoreMocks: true,
    unstubGlobals: true,
    unstubEnvs: true,

    // Reporting
    reporters: ['verbose', 'html'],
    outputFile: {
      html: './test-report.html',
    },

    // UI mode
    ui: false, // Set to true for interactive UI

    // Retry flaky tests in CI
    retry: process.env.CI ? 2 : 0,

    // Parallel execution
    fileParallelism: true,
    maxWorkers: process.env.CI ? 4 : undefined,

    // TypeScript type checking (optional, slower)
    typecheck: {
      enabled: false,
      checker: 'tsc',
    },
  },
  // Resolve aliases
  resolve: {
    alias: {
      '@': '/src',
      '@components': '/src/components',
      '@hooks': '/src/hooks',
      '@utils': '/src/utils',
      '@test': '/src/test',
    },
  },
})
```

### Setup File Template

```typescript
// src/test/setup.ts
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Clean up after each test
afterEach(() => {
  cleanup()
})

// Global mocks
global.matchMedia =
  global.matchMedia ||
  vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))

// Mock IntersectionObserver
class MockIntersectionObserver {
  observe = vi.fn()
  disconnect = vi.fn()
  unobserve = vi.fn()
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
})

// Mock ResizeObserver
class MockResizeObserver {
  observe = vi.fn()
  disconnect = vi.fn()
  unobserve = vi.fn()
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: MockResizeObserver,
})

// Suppress console errors/warnings in tests (optional)
// vi.spyOn(console, 'error').mockImplementation(() => {})
// vi.spyOn(console, 'warn').mockImplementation(() => {})
```

---

## 2. Testing React Components (RTL + Vitest)

### Component Testing Best Practices

```typescript
// components/Button/Button.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from './Button'

// Use describe blocks to group related tests
describe('Button', () => {
  // Test rendering and basic functionality
  it('renders with default props', () => {
    render(<Button>Click me</Button>)

    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
  })

  // Test different variants/props
  it('renders with different variants', () => {
    const { rerender } = render(<Button variant="primary">Primary</Button>)
    expect(screen.getByRole('button')).toHaveClass('btn-primary')

    rerender(<Button variant="secondary">Secondary</Button>)
    expect(screen.getByRole('button')).toHaveClass('btn-secondary')
  })

  // Test user interactions
  it('handles click events', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()

    render(<Button onClick={handleClick}>Click me</Button>)

    await user.click(screen.getByRole('button'))

    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  // Test disabled state
  it('is disabled when disabled prop is true', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()

    render(<Button disabled onClick={handleClick}>Disabled</Button>)

    const button = screen.getByRole('button')
    expect(button).toBeDisabled()

    await user.click(button)
    expect(handleClick).not.toHaveBeenCalled()
  })

  // Test loading state
  it('shows loading spinner when loading', () => {
    render(<Button loading>Loading</Button>)

    expect(screen.getByRole('button')).toBeDisabled()
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
  })

  // Test accessibility
  it('has correct ARIA attributes', () => {
    render(<Button aria-label="Submit form">Submit</Button>)

    expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Submit form')
  })
})
```

### Testing Form Components

```typescript
// components/LoginForm/LoginForm.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginForm } from './LoginForm'

describe('LoginForm', () => {
  it('submits form with email and password', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()

    render(<LoginForm onSubmit={onSubmit} />)

    // Fill form fields
    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')

    // Submit form
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    // Assert submission
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        email: 'user@example.com',
        password: 'password123',
      })
    })
  })

  it('shows validation errors for empty fields', async () => {
    const user = userEvent.setup()

    render(<LoginForm onSubmit={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText(/email is required/i)).toBeInTheDocument()
    expect(await screen.findByText(/password is required/i)).toBeInTheDocument()
  })

  it('disables submit button while submitting', async () => {
    const onSubmit = vi.fn(() => new Promise((resolve) => setTimeout(resolve, 100)))
    const user = userEvent.setup()

    render(<LoginForm onSubmit={onSubmit} />)

    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(screen.getByRole('button')).toBeDisabled()
    expect(screen.getByText(/signing in/i)).toBeInTheDocument()
  })
})
```

### Testing Async Components

```typescript
// components/UserProfile/UserProfile.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { UserProfile } from './UserProfile'
import * as userApi from '@/api/users'

// Mock the API module
vi.mock('@/api/users', () => ({
  fetchUser: vi.fn(),
}))

describe('UserProfile', () => {
  it('renders loading state initially', () => {
    vi.mocked(userApi.fetchUser).mockReturnValue(new Promise(() => {}))

    render(<UserProfile userId="123" />)

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('renders user data after loading', async () => {
    vi.mocked(userApi.fetchUser).mockResolvedValue({
      id: '123',
      name: 'John Doe',
      email: 'john@example.com',
    })

    render(<UserProfile userId="123" />)

    expect(await screen.findByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('john@example.com')).toBeInTheDocument()
  })

  it('renders error state on failure', async () => {
    vi.mocked(userApi.fetchUser).mockRejectedValue(new Error('User not found'))

    render(<UserProfile userId="123" />)

    expect(await screen.findByText(/error loading user/i)).toBeInTheDocument()
  })
})
```

---

## 3. Testing Server Components

### Understanding Server Component Testing

**Important:** Async Server Components are relatively new to the React ecosystem, and Vitest currently has limited support for them.

```typescript
// app/components/ServerComponent.tsx
// Server Component - runs only on the server
export async function ServerUserList() {
  const users = await fetch('https://api.example.com/users').then((r) => r.json())

  return (
    <ul>
      {users.map((user) => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  )
}
```

### Testing Strategy for Server Components

```typescript
// Option 1: Extract data fetching to a separate function
types.ts
export interface User {
  id: string
  name: string
  email: string
}

// api/users.ts
export async function fetchUsers(): Promise<User[]> {
  const response = await fetch('https://api.example.com/users')
  if (!response.ok) throw new Error('Failed to fetch users')
  return response.json()
}

// components/UserList.tsx
import { fetchUsers } from '@/api/users'

export async function UserList() {
  const users = await fetchUsers()

  return (
    <ul>
      {users.map((user) => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  )
}

// Test the data fetching function
// api/users.test.ts
import { describe, it, expect, vi } from 'vitest'
import { fetchUsers } from './users'

describe('fetchUsers', () => {
  it('fetches users successfully', async () => {
    const mockUsers = [
      { id: '1', name: 'John', email: 'john@example.com' },
    ]

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockUsers),
    })

    const users = await fetchUsers()

    expect(users).toEqual(mockUsers)
    expect(fetch).toHaveBeenCalledWith('https://api.example.com/users')
  })

  it('throws error on failed fetch', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    })

    await expect(fetchUsers()).rejects.toThrow('Failed to fetch users')
  })
})

// Option 2: Test as a Client Component with mocked data
describe('UserList (as Client Component)', () => {
  it('renders users', async () => {
    const users = [
      { id: '1', name: 'John' },
      { id: '2', name: 'Jane' },
    ]

    const { container } = render(
      <ul>
        {users.map((user) => (
          <li key={user.id}>{user.name}</li>
        ))}
      </ul>
    )

    expect(container.querySelectorAll('li')).toHaveLength(2)
  })
})
```

### Recommendation for Server Components

```typescript
/**
 * RECOMMENDED APPROACH FOR SERVER COMPONENTS
 *
 * 1. Extract all data fetching logic into separate, testable functions
 * 2. Unit test those functions in isolation
 * 3. Use E2E tests (Playwright/Cypress) to test the full Server Component behavior
 * 4. For static Server Components, test the component as a Client Component with mocked data
 */

// E2E Test with Playwright
// tests/server-components.spec.ts
import { test, expect } from '@playwright/test'

test('Server Component renders fetched data', async ({ page }) => {
  // Mock API response at the network level
  await page.route('**/api/users', async (route) => {
    await route.fulfill({
      status: 200,
      body: JSON.stringify([
        { id: '1', name: 'John' },
        { id: '2', name: 'Jane' },
      ]),
    })
  })

  await page.goto('/users')

  await expect(page.locator('li')).toHaveCount(2)
  await expect(page.locator('text=John')).toBeVisible()
})
```

---

## 4. Testing Hooks and Utilities

### Testing Custom Hooks with renderHook

```typescript
// hooks/useCounter/useCounter.test.ts
import { describe, it, expect, act } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useCounter } from './useCounter'

describe('useCounter', () => {
  it('initializes with default value', () => {
    const { result } = renderHook(() => useCounter())

    expect(result.current.count).toBe(0)
  })

  it('initializes with custom value', () => {
    const { result } = renderHook(() => useCounter(10))

    expect(result.current.count).toBe(10)
  })

  it('increments count', () => {
    const { result } = renderHook(() => useCounter())

    act(() => {
      result.current.increment()
    })

    expect(result.current.count).toBe(1)
  })

  it('decrements count', () => {
    const { result } = renderHook(() => useCounter(5))

    act(() => {
      result.current.decrement()
    })

    expect(result.current.count).toBe(4)
  })

  it('respects min and max bounds', () => {
    const { result } = renderHook(() => useCounter({ min: 0, max: 5 }))

    // Try to decrement below min
    act(() => {
      result.current.decrement()
    })
    expect(result.current.count).toBe(0)

    // Increment to max
    act(() => {
      result.current.increment()
      result.current.increment()
      result.current.increment()
      result.current.increment()
      result.current.increment()
      result.current.increment() // Should be capped at 5
    })
    expect(result.current.count).toBe(5)
  })
})

// hooks/useCounter/useCounter.ts
import { useState, useCallback } from 'react'

interface UseCounterOptions {
  min?: number
  max?: number
}

export function useCounter(initialValue: number | UseCounterOptions = 0) {
  const isOptions = typeof initialValue === 'object'
  const [count, setCount] = useState(isOptions ? 0 : initialValue)

  const min = isOptions ? initialValue.min : undefined
  const max = isOptions ? initialValue.max : undefined

  const increment = useCallback(() => {
    setCount((c) => (max !== undefined ? Math.min(c + 1, max) : c + 1))
  }, [max])

  const decrement = useCallback(() => {
    setCount((c) => (min !== undefined ? Math.max(c - 1, min) : c - 1))
  }, [min])

  const reset = useCallback(() => {
    setCount(isOptions ? 0 : initialValue)
  }, [initialValue])

  return { count, increment, decrement, reset }
}
```

### Testing Async Hooks

```typescript
// hooks/useFetch/useFetch.test.ts
import { describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useFetch } from './useFetch'

describe('useFetch', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('fetches data successfully', async () => {
    const mockData = { id: 1, name: 'Test' }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const { result } = renderHook(() => useFetch('/api/data'))

    // Initial state
    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()

    // Wait for data
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toEqual(mockData)
    expect(result.current.error).toBeNull()
  })

  it('handles fetch error', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    })

    const { result } = renderHook(() => useFetch('/api/data'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeTruthy()
  })
})
```

### Testing Utility Functions

```typescript
// utils/formatDate/formatDate.test.ts
import { describe, it, expect } from 'vitest'
import { formatDate, formatRelativeTime } from './formatDate'

describe('formatDate', () => {
  it('formats date with default format', () => {
    const date = new Date('2024-01-15')
    expect(formatDate(date)).toBe('Jan 15, 2024')
  })

  it('formats date with custom format', () => {
    const date = new Date('2024-01-15')
    expect(formatDate(date, 'YYYY-MM-DD')).toBe('2024-01-15')
  })

  it('handles string date input', () => {
    expect(formatDate('2024-01-15')).toBe('Jan 15, 2024')
  })

  it('handles timestamp input', () => {
    const timestamp = new Date('2024-01-15').getTime()
    expect(formatDate(timestamp)).toBe('Jan 15, 2024')
  })

  it('returns empty string for invalid date', () => {
    expect(formatDate('invalid')).toBe('')
    expect(formatDate(null as any)).toBe('')
    expect(formatDate(undefined as any)).toBe('')
  })
})

describe('formatRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-01-15T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('formats seconds ago', () => {
    const date = new Date('2024-01-15T11:59:30Z')
    expect(formatRelativeTime(date)).toBe('30 seconds ago')
  })

  it('formats minutes ago', () => {
    const date = new Date('2024-01-15T11:55:00Z')
    expect(formatRelativeTime(date)).toBe('5 minutes ago')
  })

  it('formats hours ago', () => {
    const date = new Date('2024-01-15T10:00:00Z')
    expect(formatRelativeTime(date)).toBe('2 hours ago')
  })

  it('formats days ago', () => {
    const date = new Date('2024-01-13T12:00:00Z')
    expect(formatRelativeTime(date)).toBe('2 days ago')
  })

  it('returns formatted date for older dates', () => {
    const date = new Date('2023-12-01T12:00:00Z')
    expect(formatRelativeTime(date)).toBe('Dec 1, 2023')
  })
})
```

---

## 5. Mocking Strategies

### Mocking Functions

```typescript
// Function mocking patterns
import { vi, describe, it, expect } from 'vitest'

// 1. Simple function mock
const mockFn = vi.fn()
mockFn('arg1', 'arg2')
expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2')

// 2. Mock with return value
const mockWithReturn = vi.fn().mockReturnValue('result')
expect(mockWithReturn()).toBe('result')

// 3. Mock with implementation
const mockWithImpl = vi.fn((a: number, b: number) => a + b)
expect(mockWithImpl(2, 3)).toBe(5)

// 4. Mock with different return values per call
const mockSequence = vi.fn()
mockSequence
  .mockReturnValueOnce('first')
  .mockReturnValueOnce('second')
  .mockReturnValue('default')

expect(mockSequence()).toBe('first')
expect(mockSequence()).toBe('second')
expect(mockSequence()).toBe('default')
expect(mockSequence()).toBe('default')

// 5. Mock with async return
const mockAsync = vi.fn().mockResolvedValue({ data: [] })
const mockAsyncReject = vi.fn().mockRejectedValue(new Error('Failed'))
```

### Mocking Modules

```typescript
// Mocking entire modules
import { vi, describe, it, expect } from 'vitest'
import { getUserData } from './userService'

// Mock the entire module
vi.mock('./api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

// Mock with partial implementation
vi.mock('./utils', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./utils')>()
  return {
    ...actual,
    // Override specific exports
    expensiveComputation: vi.fn().mockReturnValue(42),
  }
})

// Auto-mock (spy on all exports without replacing)
vi.mock('./logger', { spy: true })

// Using mocked import
import { apiClient } from './api/client'
import * as logger from './logger'

describe('userService', () => {
  it('fetches user data', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { id: 1, name: 'John' },
    })

    const user = await getUserData(1)

    expect(user).toEqual({ id: 1, name: 'John' })
    expect(apiClient.get).toHaveBeenCalledWith('/users/1')
    expect(logger.info).toHaveBeenCalledWith('Fetching user 1')
  })
})
```

### Mocking Browser APIs

```typescript
// Mocking window, document, and browser APIs
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'

describe('browser API mocks', () => {
  // LocalStorage mock
  describe('localStorage', () => {
    const localStorageMock = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    }

    beforeEach(() => {
      Object.defineProperty(window, 'localStorage', {
        value: localStorageMock,
        writable: true,
      })
    })

    it('stores and retrieves data', () => {
      const { getItem, setItem } = window.localStorage

      setItem('key', 'value')
      expect(setItem).toHaveBeenCalledWith('key', 'value')
    })
  })

  // Fetch mock
  describe('fetch API', () => {
    beforeEach(() => {
      global.fetch = vi.fn()
    })

    afterEach(() => {
      vi.restoreAllMocks()
    })

    it('mocks successful response', async () => {
      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: 'test' }),
      } as Response)

      const response = await fetch('/api/data')
      const data = await response.json()

      expect(data).toEqual({ data: 'test' })
    })

    it('mocks error response', async () => {
      vi.mocked(global.fetch).mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      } as Response)

      const response = await fetch('/api/data')

      expect(response.ok).toBe(false)
    })
  })

  // MatchMedia mock
  describe('matchMedia', () => {
    beforeEach(() => {
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }))
    })

    it('checks media query', () => {
      const mql = window.matchMedia('(min-width: 768px)')
      expect(mql.matches).toBe(false)
    })
  })

  // IntersectionObserver mock
  describe('IntersectionObserver', () => {
    let observerCallback: IntersectionObserverCallback

    beforeEach(() => {
      global.IntersectionObserver = vi.fn((callback) => {
        observerCallback = callback
        return {
          observe: vi.fn(),
          unobserve: vi.fn(),
          disconnect: vi.fn(),
          takeRecords: vi.fn(),
          root: null,
          rootMargin: '',
          thresholds: [],
        }
      }) as unknown as typeof IntersectionObserver
    })

    it('triggers intersection callback', () => {
      const element = document.createElement('div')
      const observer = new IntersectionObserver(() => {})
      observer.observe(element)

      // Simulate intersection
      observerCallback(
        [{ isIntersecting: true, target: element } as IntersectionObserverEntry],
        observer
      )

      expect(observer.observe).toHaveBeenCalledWith(element)
    })
  })

  // Timer mocks
  describe('timers', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('controls time', () => {
      const callback = vi.fn()

      setTimeout(callback, 1000)
      expect(callback).not.toHaveBeenCalled()

      vi.advanceTimersByTime(1000)
      expect(callback).toHaveBeenCalled()
    })

    it('controls system time', () => {
      const mockDate = new Date('2024-01-15')
      vi.setSystemTime(mockDate)

      expect(new Date()).toEqual(mockDate)
    })
  })
})
```

### Mocking React Context

```typescript
// Mocking React Context providers
import { vi, describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AuthContext } from '@/contexts/AuthContext'
import { UserProfile } from './UserProfile'

// Helper to render with context
const renderWithAuth = (ui: React.ReactNode, authValue: any) => {
  return render(
    <AuthContext.Provider value={authValue}>
      {ui}
    </AuthContext.Provider>
  )
}

describe('UserProfile with AuthContext', () => {
  it('renders user info when authenticated', () => {
    const authValue = {
      user: { id: '1', name: 'John', email: 'john@example.com' },
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
    }

    renderWithAuth(<UserProfile />, authValue)

    expect(screen.getByText('John')).toBeInTheDocument()
    expect(screen.getByText('john@example.com')).toBeInTheDocument()
  })

  it('renders login prompt when not authenticated', () => {
    const authValue = {
      user: null,
      isAuthenticated: false,
      login: vi.fn(),
      logout: vi.fn(),
    }

    renderWithAuth(<UserProfile />, authValue)

    expect(screen.getByText(/please log in/i)).toBeInTheDocument()
  })
})
```

### MSW (Mock Service Worker) for API Mocking

```typescript
// test/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  // User API handlers
  http.get('/api/users', () => {
    return HttpResponse.json([
      { id: '1', name: 'John Doe', email: 'john@example.com' },
      { id: '2', name: 'Jane Smith', email: 'jane@example.com' },
    ])
  }),

  http.get('/api/users/:id', ({ params }) => {
    const { id } = params
    return HttpResponse.json({
      id,
      name: 'John Doe',
      email: 'john@example.com',
    })
  }),

  http.post('/api/users', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json(
      { id: '3', ...body },
      { status: 201 }
    )
  }),

  // Error simulation
  http.get('/api/error', () => {
    return HttpResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    )
  }),
]

// test/mocks/server.ts
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)

// test/setup.ts
import { beforeAll, afterAll, afterEach } from 'vitest'
import { server } from './mocks/server'

// Start server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

// Reset handlers after each test
afterEach(() => server.resetHandlers())

// Close server after all tests
afterAll(() => server.close())

// Override handlers in specific tests
describe('User API with MSW', () => {
  it('fetches users list', async () => {
    const response = await fetch('/api/users')
    const users = await response.json()

    expect(users).toHaveLength(2)
    expect(users[0].name).toBe('John Doe')
  })

  it('handles error state', async () => {
    // Override handler for this test
    server.use(
      http.get('/api/users', () => {
        return HttpResponse.json(
          { error: 'Database error' },
          { status: 500 }
        )
      })
    )

    const response = await fetch('/api/users')

    expect(response.ok).toBe(false)
    expect(response.status).toBe(500)
  })
})
```

---

## 6. Coverage Configuration and Thresholds

### Coverage Setup

```typescript
// vitest.config.ts - Coverage section
export default defineConfig({
  test: {
    coverage: {
      // Provider selection
      provider: 'v8', // 'v8' is faster, 'istanbul' is more compatible

      // Reporters
      reporter: [
        ['text', { skipFull: true }], // Console output, skip 100% files
        ['text-summary'], // Summary table
        'json', // JSON report
        'html', // HTML report
        'lcov', // LCOV for CI integration
      ],

      // Output directory
      reportsDirectory: './coverage',

      // Include/exclude patterns
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        // Config files
        '**/*.config.{ts,js}',

        // Type definitions
        '**/*.d.ts',

        // Test files
        '**/*.test.{ts,tsx}',
        '**/*.spec.{ts,tsx}',
        '**/__tests__/**',
        '**/__mocks__/**',

        // Entry points
        'src/main.tsx',
        'src/App.tsx',

        // Types and constants (pure data)
        'src/types/**',
        'src/constants/**',

        // Generated files
        'src/generated/**',

        // Stories (if using Storybook)
        '**/*.stories.{ts,tsx}',
      ],

      // Coverage thresholds
      thresholds: {
        lines: 90,
        functions: 90,
        branches: 85, // Lower threshold for complex conditionals
        statements: 90,

        // Per-file thresholds (optional)
        // autoUpdate: true, // Update thresholds based on current coverage
      },

      // Watermarks for HTML report
      watermarks: {
        lines: [80, 95],
        functions: [80, 95],
        branches: [80, 95],
        statements: [80, 95],
      },

      // Additional options
      clean: true, // Clean output directory before running
      cleanOnRerun: true,
      reportOnFailure: true, // Generate report even if tests fail
      allowExternal: false,
    },
  },
})
```

### Coverage Scripts

```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest run --coverage",
    "test:coverage:ui": "vitest --ui --coverage",
    "coverage:report": "open coverage/index.html"
  }
}
```

### Ignoring Code from Coverage

```typescript
// Using comments to ignore code from coverage

// Ignore specific line
const result = someComplexOperation() /* v8 ignore next -- @preserve */

// Ignore multiple lines
/* v8 ignore start -- @preserve */
function debugOnlyFunction() {
  console.log('Debug info')
  return process.env.DEBUG ? extraData : null
}
/* v8 ignore stop -- @preserve */

// Ignore specific branch
if (process.env.NODE_ENV === 'development') {
  /* v8 ignore next -- @preserve */
  console.warn('Development mode warning')
}

// Ignore else branch
if (condition) {
  doSomething()
} else {
  /* v8 ignore next -- @preserve */
  handleEdgeCase() // Hard to test
}

// Ignore entire file (place at top)
/* v8 ignore file -- @preserve */

// For Istanbul (alternative provider)
/* istanbul ignore next -- @preserve */
function untestableCode() {
  // ...
}
```

### Coverage Best Practices

```typescript
/**
 * COVERAGE BEST PRACTICES
 *
 * 1. Set realistic thresholds:
 *    - 90% for lines/functions/statements
 *    - 85% for branches (complex conditionals are harder to fully cover)
 *
 * 2. Exclude appropriate files:
 *    - Entry points (main.tsx, App.tsx)
 *    - Type definitions
 *    - Generated code
 *    - Configuration files
 *
 * 3. Use v8 provider for speed, istanbul for compatibility
 *
 * 4. Review uncovered code regularly:
 *    - Some code legitimately can't/shouldn't be tested
 *    - Use ignore hints with explanatory comments
 *    - Don't game the system to hit thresholds
 *
 * 5. Focus on meaningful coverage:
 *    - Test critical business logic thoroughly
 *    - Test edge cases and error paths
 *    - Don't just test for coverage's sake
 */
```

---

## 7. Test Organization and Naming Conventions

### File Structure

```
src/
├── components/
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.module.css
│   │   ├── Button.test.tsx        # Co-located test
│   │   └── index.ts
│   └── Card/
│       ├── Card.tsx
│       └── Card.test.tsx
├── hooks/
│   ├── useAuth/
│   │   ├── useAuth.ts
│   │   └── useAuth.test.ts
│   └── useFetch/
│       ├── useFetch.ts
│       └── useFetch.test.ts
├── utils/
│   ├── formatDate.ts
│   ├── formatDate.test.ts
│   └── validation.test.ts         # Multiple tests in one file
└── test/
    ├── setup.ts                   # Global test setup
    ├── mocks/
    │   ├── handlers.ts            # MSW handlers
    │   └── server.ts              # MSW server setup
    ├── utils/
    │   └── renderWithProviders.tsx # Custom render helpers
    └── fixtures/
        └── users.ts               # Test data
```

### Test Naming Conventions

```typescript
// File naming
// - ComponentName.test.tsx for components
// - hookName.test.ts for hooks
// - functionName.test.ts for utilities
// - featureName.test.ts for integration tests

// Test structure naming
describe('ComponentName', () => {
  describe('rendering', () => {
    it('renders with default props', () => {})
    it('renders with custom props', () => {})
    it('renders nothing when condition is false', () => {})
  })

  describe('interactions', () => {
    it('calls onClick when clicked', () => {})
    it('disables button when loading', () => {})
  })

  describe('accessibility', () => {
    it('has correct ARIA attributes', () => {})
    it('supports keyboard navigation', () => {})
  })
})

// Test description patterns
// ❌ Bad - too vague
it('works', () => {})
it('handles click', () => {})
it('test 1', () => {})

// ✅ Good - descriptive
it('displays user name when provided', () => {})
it('calls onSubmit with form data when submitted', () => {})
it('shows error message when API returns 500', () => {})
it('disables submit button while form is submitting', () => {})

// Use 'should' or present tense for clarity
it('should validate email format', () => {})
it('validates email format', () => {})
```

### Custom Render Utilities

```typescript
// test/utils/renderWithProviders.tsx
import { ReactElement, ReactNode } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/contexts/AuthContext'
import { ThemeProvider } from '@/contexts/ThemeContext'

// Create test query client
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
        gcTime: Infinity,
      },
    },
  })

// All providers wrapper
interface AllProvidersProps {
  children: ReactNode
  initialAuthState?: any
}

function AllProviders({ children, initialAuthState }: AllProvidersProps) {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider initialState={initialAuthState}>
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}

// Custom render function
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialAuthState?: any
}

export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {}
) {
  const { initialAuthState, ...renderOptions } = options

  return {
    ...render(ui, {
      wrapper: (props) => (
        <AllProviders {...props} initialAuthState={initialAuthState} />
      ),
      ...renderOptions,
    }),
    queryClient: createTestQueryClient(),
  }
}

// Re-export everything from testing-library
export * from '@testing-library/react'
export { renderWithProviders as render }
```

### Test Data Fixtures

```typescript
// test/fixtures/users.ts
import { User } from '@/types'

export const mockUser: User = {
  id: '1',
  name: 'John Doe',
  email: 'john@example.com',
  avatar: 'https://example.com/avatar.jpg',
  role: 'user',
  createdAt: '2024-01-01T00:00:00Z',
}

export const mockAdmin: User = {
  id: '2',
  name: 'Admin User',
  email: 'admin@example.com',
  avatar: null,
  role: 'admin',
  createdAt: '2024-01-01T00:00:00Z',
}

export const mockUsers: User[] = [
  mockUser,
  mockAdmin,
  {
    id: '3',
    name: 'Jane Smith',
    email: 'jane@example.com',
    avatar: null,
    role: 'user',
    createdAt: '2024-01-15T00:00:00Z',
  },
]

// Factory function for creating variations
export function createUser(overrides: Partial<User> = {}): User {
  return {
    id: String(Math.random()),
    name: 'Test User',
    email: 'test@example.com',
    avatar: null,
    role: 'user',
    createdAt: new Date().toISOString(),
    ...overrides,
  }
}

// Usage in tests
import { mockUser, createUser } from '@/test/fixtures/users'

const userWithName = createUser({ name: 'Custom Name' })
```

---

## 8. Integration Testing Patterns

### Component Integration Tests

```typescript
// features/ShoppingCart/ShoppingCart.integration.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ShoppingCart } from './ShoppingCart'
import { ProductList } from './ProductList'
import { CartSummary } from './CartSummary'

describe('ShoppingCart Integration', () => {
  const mockProducts = [
    { id: '1', name: 'Laptop', price: 999, stock: 5 },
    { id: '2', name: 'Mouse', price: 29, stock: 10 },
  ]

  it('adds products to cart and updates summary', async () => {
    const user = userEvent.setup()

    render(
      <ShoppingCart>
        <ProductList products={mockProducts} />
        <CartSummary />
      </ShoppingCart>
    )

    // Add items to cart
    await user.click(screen.getByRole('button', { name: /add laptop/i }))
    await user.click(screen.getByRole('button', { name: /add mouse/i }))
    await user.click(screen.getByRole('button', { name: /add mouse/i }))

    // Verify cart summary updated
    expect(screen.getByText(/total: \$1,057/i)).toBeInTheDocument()
    expect(screen.getByText(/3 items/i)).toBeInTheDocument()
  })

  it('persists cart state across component interactions', async () => {
    const user = userEvent.setup()

    const { rerender } = render(
      <ShoppingCart>
        <ProductList products={mockProducts} />
      </ShoppingCart>
    )

    // Add item
    await user.click(screen.getByRole('button', { name: /add laptop/i }))

    // Re-render with different child (simulating navigation)
    rerender(
      <ShoppingCart>
        <CartSummary />
      </ShoppingCart>
    )

    // Cart state should persist
    expect(screen.getByText(/laptop/i)).toBeInTheDocument()
    expect(screen.getByText(/\$999/i)).toBeInTheDocument()
  })
})
```

### Feature Integration Tests

```typescript
// features/Authentication/auth.integration.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthProvider } from './AuthProvider'
import { LoginForm } from './LoginForm'
import { UserProfile } from './UserProfile'
import { ProtectedRoute } from './ProtectedRoute'

describe('Authentication Flow', () => {
  it('complete login flow', async () => {
    const user = userEvent.setup()

    render(
      <AuthProvider>
        <LoginForm />
        <ProtectedRoute>
          <UserProfile />
        </ProtectedRoute>
      </AuthProvider>
    )

    // Initial state - login form visible
    expect(screen.getByRole('form')).toBeInTheDocument()
    expect(screen.queryByText(/welcome/i)).not.toBeInTheDocument()

    // Enter credentials
    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /login/i }))

    // After successful login - profile visible
    await waitFor(() => {
      expect(screen.getByText(/welcome, user/i)).toBeInTheDocument()
    })

    expect(screen.queryByRole('form')).not.toBeInTheDocument()
  })

  it('handles login error and recovery', async () => {
    const user = userEvent.setup()

    render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>
    )

    // Failed login attempt
    await user.type(screen.getByLabelText(/email/i), 'wrong@example.com')
    await user.type(screen.getByLabelText(/password/i), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: /login/i }))

    // Error message displayed
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })

    // Can retry
    await user.clear(screen.getByLabelText(/email/i))
    await user.type(screen.getByLabelText(/email/i), 'correct@example.com')
    await user.click(screen.getByRole('button', { name: /login/i }))

    // Error cleared on new attempt
    await waitFor(() => {
      expect(screen.queryByText(/invalid credentials/i)).not.toBeInTheDocument()
    })
  })
})
```

### API Integration with MSW

```typescript
// features/Users/users.integration.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { UserList } from './UserList'
import { UserDetails } from './UserDetails'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('User Management Integration', () => {
  it('fetches and displays users, then shows details on selection', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()

    render(
      <Wrapper>
        <UserList />
        <UserDetails />
      </Wrapper>
    )

    // Loading state
    expect(screen.getByText(/loading users/i)).toBeInTheDocument()

    // Users loaded
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    expect(screen.getByText('Jane Smith')).toBeInTheDocument()

    // Select user to view details
    await user.click(screen.getByText('John Doe'))

    // Details loading
    expect(screen.getByText(/loading details/i)).toBeInTheDocument()

    // Details displayed
    await waitFor(() => {
      expect(screen.getByText(/john@example.com/i)).toBeInTheDocument()
    })

    expect(screen.getByText(/admin/i)).toBeInTheDocument()
  })

  it('handles user creation flow', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()

    // Track POST request
    let createdUser: any = null
    server.use(
      http.post('/api/users', async ({ request }) => {
        createdUser = await request.json()
        return HttpResponse.json({ id: '3', ...createdUser }, { status: 201 })
      })
    )

    render(
      <Wrapper>
        <UserList />
        <CreateUserForm />
      </Wrapper>
    )

    // Fill form
    await user.type(screen.getByLabelText(/name/i), 'New User')
    await user.type(screen.getByLabelText(/email/i), 'new@example.com')
    await user.click(screen.getByRole('button', { name: /create user/i }))

    // Verify API called with correct data
    await waitFor(() => {
      expect(createdUser).toEqual({
        name: 'New User',
        email: 'new@example.com',
      })
    })

    // New user appears in list
    await waitFor(() => {
      expect(screen.getByText('New User')).toBeInTheDocument()
    })
  })
})
```

---

## 9. E2E Testing Considerations

### When to Use E2E vs Unit/Integration Tests

```typescript
/**
 * TESTING PYRAMID
 *
 * E2E Tests (10%)
 * - Critical user journeys
 * - Cross-page workflows
 * - Payment flows
 * - Authentication flows
 * - Complex multi-step processes
 *
 * Integration Tests (30%)
 * - Component interactions
 * - Feature workflows
 * - API integration
 * - State management
 *
 * Unit Tests (60%)
 * - Individual functions
 * - Component rendering
 * - Utility functions
 * - Hooks
 * - Edge cases
 */
```

### E2E with Playwright (Recommended)

```typescript
// e2e/auth.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Authentication E2E', () => {
  test('user can sign up and log in', async ({ page }) => {
    // Sign up
    await page.goto('/signup')
    await page.fill('[name="email"]', 'newuser@example.com')
    await page.fill('[name="password"]', 'SecurePass123!')
    await page.fill('[name="confirmPassword"]', 'SecurePass123!')
    await page.click('button[type="submit"]')

    // Verify redirect to dashboard
    await expect(page).toHaveURL('/dashboard')
    await expect(page.locator('text=Welcome')).toBeVisible()

    // Log out
    await page.click('text=Logout')
    await expect(page).toHaveURL('/login')

    // Log back in
    await page.fill('[name="email"]', 'newuser@example.com')
    await page.fill('[name="password"]', 'SecurePass123!')
    await page.click('button[type="submit"]')

    await expect(page).toHaveURL('/dashboard')
  })

  test('protected routes redirect unauthenticated users', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL('/login?redirect=/dashboard')
  })
})

// e2e/checkout.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Checkout Flow', () => {
  test('complete purchase flow', async ({ page }) => {
    // Add items to cart
    await page.goto('/products')
    await page.click('[data-testid="add-to-cart"]:first-child')
    await page.click('[data-testid="add-to-cart"]:nth-child(2)')

    // Go to cart
    await page.click('[data-testid="cart-link"]')
    await expect(page.locator('[data-testid="cart-count"]')).toHaveText('2')

    // Proceed to checkout
    await page.click('text=Checkout')

    // Fill shipping info
    await page.fill('[name="address"]', '123 Test St')
    await page.fill('[name="city"]', 'Test City')
    await page.fill('[name="zip"]', '12345')
    await page.click('text=Continue to Payment')

    // Fill payment info (use test card)
    await page.fill('[name="cardNumber"]', '4242424242424242')
    await page.fill('[name="expiry"]', '12/25')
    await page.fill('[name="cvc"]', '123')
    await page.click('text=Complete Purchase')

    // Verify success
    await expect(page.locator('text=Order Confirmed')).toBeVisible()
    await expect(page.locator('[data-testid="order-number"]')).toBeVisible()
  })
})

// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    // Mobile
    { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
    { name: 'Mobile Safari', use: { ...devices['iPhone 12'] } },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
```

### E2E Vitest Browser Mode

```typescript
// Component E2E with Vitest Browser Mode
// vitest.config.ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    browser: {
      enabled: true,
      provider: 'playwright', // or 'webdriverio'
      instances: [
        { browser: 'chromium' },
        { browser: 'firefox' },
        { browser: 'webkit' },
      ],
    },
  },
})

// Component test with real browser
// components/Button/Button.e2e.test.tsx
import { describe, it, expect } from 'vitest'
import { page } from '@vitest/browser/context'
import { render } from 'vitest-browser-react'
import { Button } from './Button'

describe('Button in real browser', () => {
  it('renders and handles clicks', async () => {
    const onClick = vi.fn()

    render(<Button onClick={onClick}>Click me</Button>)

    // Get element using page API
    const button = page.getByRole('button', { name: /click me/i })

    // Assertions
    await expect.element(button).toBeVisible()
    await expect.element(button).toBeEnabled()

    // Interaction
    await button.click()

    expect(onClick).toHaveBeenCalled()
  })

  it('has correct styles', async () => {
    render(<Button variant="primary">Styled</Button>)

    const button = page.getByRole('button')

    // Check computed styles
    const styles = await button.evaluate((el) => {
      const computed = window.getComputedStyle(el)
      return {
        backgroundColor: computed.backgroundColor,
        color: computed.color,
      }
    })

    expect(styles.backgroundColor).toBe('rgb(0, 123, 255)')
  })
})
```

---

## 10. Common Pitfalls and How to Avoid Them

### Common Mistakes

```typescript
// ❌ PITFALL 1: Testing implementation details
// Don't test state, test behavior
it('sets isOpen to true when clicked', () => {
  const { result } = renderHook(() => useModal())
  act(() => {
    result.current.open()
  })
  expect(result.current.isOpen).toBe(true) // Testing state
})

// ✅ BETTER: Test the outcome
it('displays modal content when triggered', async () => {
  const user = userEvent.setup()
  render(<Modal trigger={<button>Open</button>} content={<p>Content</p>} />)

  await user.click(screen.getByRole('button', { name: /open/i }))
  expect(screen.getByText('Content')).toBeVisible()
})

// ❌ PITFALL 2: Using query* for existence checks
it('shows error', () => {
  render(<Form />)
  expect(screen.queryByText(/error/i)).toBeInTheDocument() // May pass silently if not found
})

// ✅ BETTER: Use get* for existence, query* only for non-existence
it('shows error', () => {
  render(<Form />)
  expect(screen.getByText(/error/i)).toBeInTheDocument() // Will fail with helpful message
})

it('does not show error initially', () => {
  render(<Form />)
  expect(screen.queryByText(/error/i)).not.toBeInTheDocument()
})

// ❌ PITFALL 3: Using wrong queries
it('finds button', () => {
  render(<button className="btn-primary">Click</button>)
  expect(screen.getByTestId('submit-btn')).toBeInTheDocument() // Requires data-testid
})

// ✅ BETTER: Query by role (accessibility)
it('finds button', () => {
  render(<button className="btn-primary">Click</button>)
  expect(screen.getByRole('button', { name: /click/i })).toBeInTheDocument()
})

// ❌ PITFALL 4: Using fireEvent instead of userEvent
it('submits form', () => {
  render(<Form />)
  fireEvent.change(screen.getByLabelText(/email/i), {
    target: { value: 'test@example.com' },
  })
  fireEvent.click(screen.getByRole('button'))
})

// ✅ BETTER: Use userEvent for realistic interactions
it('submits form', async () => {
  const user = userEvent.setup()
  render(<Form />)

  await user.type(screen.getByLabelText(/email/i), 'test@example.com')
  await user.click(screen.getByRole('button'))
})

// ❌ PITFALL 5: Not awaiting async operations
it('loads data', () => {
  render(<UserList />)
  expect(screen.getByText('John')).toBeInTheDocument() // Element not yet rendered
})

// ✅ BETTER: Use find* or waitFor for async operations
it('loads data', async () => {
  render(<UserList />)
  expect(await screen.findByText('John')).toBeInTheDocument()
})

// ❌ PITFALL 6: Testing multiple things in one test
it('handles all form operations', async () => {
  render(<Form />)
  // Tests validation, submission, error handling, success...
  // 50 lines of test code
})

// ✅ BETTER: One behavior per test
describe('Form', () => {
  it('validates empty fields', async () => {})
  it('validates email format', async () => {})
  it('submits with valid data', async () => {})
  it('shows error on server failure', async () => {})
  it('resets after successful submission', async () => {})
})

// ❌ PITFALL 7: Not cleaning up mocks
it('test 1', () => {
  const fn = vi.fn().mockReturnValue('value')
  // ...test
})

it('test 2', () => {
  // fn from test 1 might still be in scope or affect this test
})

// ✅ BETTER: Use beforeEach to reset, or inline mocks
beforeEach(() => {
  vi.clearAllMocks()
})

// Or use the config option:
// vitest.config.ts: { test: { mockReset: true } }

// ❌ PITFALL 8: Testing coverage instead of behavior
// Writing tests just to hit coverage thresholds without meaningful assertions

// ✅ BETTER: Focus on testing behavior and edge cases
// Coverage will follow naturally from thorough testing
```

### Flaky Tests Prevention

```typescript
/**
 * FLAKY TEST PREVENTION STRATEGIES
 */

// 1. Avoid relying on timing
describe('Flaky Prevention', () => {
  // ❌ Bad: relies on setTimeout
  it('shows notification', async () => {
    render(<Notification />)
    await new Promise((r) => setTimeout(r, 100)) // Flaky!
    expect(screen.getByText('Success')).toBeInTheDocument()
  })

  // ✅ Better: wait for specific condition
  it('shows notification', async () => {
    render(<Notification />)
    await waitFor(() => {
      expect(screen.getByText('Success')).toBeInTheDocument()
    })
  })

  // 2. Control timers
  it('auto-hides after 5 seconds', async () => {
    vi.useFakeTimers()
    render(<Notification />)

    expect(screen.getByText('Success')).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(5000)
    })

    expect(screen.queryByText('Success')).not.toBeInTheDocument()
    vi.useRealTimers()
  })

  // 3. Use unique data in tests
  it('creates user', async () => {
    const uniqueEmail = `test-${Date.now()}@example.com` // Unique per run
    // ...test
  })

  // 4. Isolate tests - don't share state
  // ❌ Bad: shared state
  let sharedValue = 0

  it('increments', () => {
    sharedValue++
    expect(sharedValue).toBe(1)
  })

  it('increments again', () => {
    sharedValue++ // Depends on order!
    expect(sharedValue).toBe(2) // May fail if tests run in parallel
  })

  // ✅ Better: isolated state
  it('increments', () => {
    const value = 0
    const result = increment(value)
    expect(result).toBe(1)
  })
})
```

### Performance Best Practices

```typescript
// vitest.config.ts - Performance optimizations
export default defineConfig({
  test: {
    // Use forks for stability, threads for speed
    pool: 'forks',

    // Limit parallel tests in CI
    maxWorkers: process.env.CI ? 4 : undefined,
    minWorkers: 1,

    // Cache results
    cache: {
      dir: './node_modules/.vitest',
    },

    // Isolate tests (set to false for faster execution if tests are independent)
    isolate: true,

    // Disable type checking during tests (run separately)
    typecheck: {
      enabled: false,
    },
  },
})

// Test-level optimizations
describe('Performance', () => {
  // Share setup across tests
  const setup = () => {
    // Expensive operation
    return createLargeDataSet()
  }

  // ❌ Bad: setup in each test
  it('test 1', () => {
    const data = setup()
    // ...
  })

  it('test 2', () => {
    const data = setup() // Repeated!
    // ...
  })

  // ✅ Better: use beforeAll for expensive setup
  let sharedData: any

  beforeAll(() => {
    sharedData = setup()
  })

  it('test 1', () => {
    // Use sharedData
  })

  it('test 2', () => {
    // Use sharedData
  })

  // Or use test.extend for fixtures
})
```

### Debugging Tests

```typescript
/**
 * DEBUGGING TECHNIQUES
 */

// 1. Use screen.debug() to see rendered output
it('debug example', () => {
  render(<Component />)
  screen.debug() // Prints DOM to console
  screen.debug(screen.getByRole('form')) // Print specific element
})

// 2. Use logRoles for accessibility info
import { logRoles } from '@testing-library/dom'

it('debug roles', () => {
  const { container } = render(<Component />)
  logRoles(container)
})

// 3. Slow down tests to see what's happening
it('slow motion', async () => {
  const user = userEvent.setup({ delay: 100 }) // Add delay between actions
  render(<Form />)
  await user.type(screen.getByLabelText(/email/i), 'test@example.com')
})

// 4. Use Vitest UI
// npm run test:ui

// 5. Check for act() warnings
// These indicate state updates not wrapped in act()

// 6. Use expect.extend for better error messages
expect.extend({
  toBeWithinRange(received, floor, ceiling) {
    const pass = received >= floor && received <= ceiling
    if (pass) {
      return {
        message: () => `expected ${received} not to be within range ${floor} - ${ceiling}`,
        pass: true,
      }
    } else {
      return {
        message: () => `expected ${received} to be within range ${floor} - ${ceiling}`,
        pass: false,
      }
    }
  },
})
```

---

## Quick Reference Checklist

### Before Writing Tests
- [ ] Test behavior, not implementation
- [ ] Use semantic queries (getByRole > getByTestId)
- [ ] Test accessibility
- [ ] Test error states
- [ ] Test loading states

### During Testing
- [ ] Use userEvent over fireEvent
- [ ] Use find* for async operations
- [ ] Use query* only for non-existence checks
- [ ] One behavior per test
- [ ] Use screen for queries

### Coverage Goals
- [ ] 90%+ lines/statements/functions
- [ ] 85%+ branches
- [ ] Exclude appropriate files
- [ ] Meaningful coverage, not just numbers

### Performance
- [ ] Use pool: 'forks' for stability
- [ ] Mock slow dependencies
- [ ] Share expensive setup with beforeAll
- [ ] Disable type checking during tests

### Organization
- [ ] Co-locate tests with source
- [ ] Use describe blocks for grouping
- [ ] Descriptive test names
- [ ] Custom render for common providers

---

## Package Installation Summary

```bash
# Core testing
npm install -D vitest @vitejs/plugin-react

# React Testing Library
npm install -D @testing-library/react @testing-library/dom @testing-library/jest-dom @testing-library/user-event

# Environment
npm install -D jsdom # or happy-dom

# Coverage
npm install -D @vitest/coverage-v8 # or @vitest/coverage-istanbul

# MSW for API mocking
npm install -D msw

# Utilities
npm install -D vite-tsconfig-paths

# E2E (optional)
npm install -D @playwright/test

# Browser mode (optional)
npm install -D vitest-browser-react playwright
```

---

## Additional Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Library Queries](https://testing-library.com/docs/queries/about)
- [MSW Documentation](https://mswjs.io/)
- [Playwright](https://playwright.dev/)
- [Kent C. Dodds - Common Mistakes](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

---

*This guide provides a comprehensive foundation for achieving 90%+ code coverage with Vitest. Remember: coverage is a metric, not a goal. Focus on testing behavior and user interactions for truly reliable tests.*
