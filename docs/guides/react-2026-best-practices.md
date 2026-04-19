# React Best Practices and Patterns for 2026

A comprehensive guide to modern React development covering React 19+, Server Components, SSR, Hooks, State Management, Performance, Architecture, and TypeScript.

---

## Table of Contents

1. [React 19+ Features and Patterns](#1-react-19-features-and-patterns)
2. [Server Components (RSC) Best Practices](#2-server-components-rsc-best-practices)
3. [Server-Side Rendering (SSR) Patterns](#3-server-side-rendering-ssr-patterns)
4. [React Hooks Best Practices](#4-react-hooks-best-practices)
5. [State Management with TanStack Query](#5-state-management-with-tanstack-query)
6. [Performance Optimization Techniques](#6-performance-optimization-techniques)
7. [Modern React Architecture Patterns](#7-modern-react-architecture-patterns)
8. [File Structure and Organization](#8-file-structure-and-organization)
9. [TypeScript Integration Best Practices](#9-typescript-integration-best-practices)

---

## 1. React 19+ Features and Patterns

### Actions and Async Transitions

React 19 introduces **Actions** - async functions that handle pending states, errors, forms, and optimistic updates automatically.

```tsx
// Before React 19 - Manual handling
function UpdateName({}) {
  const [name, setName] = useState("");
  const [error, setError] = useState(null);
  const [isPending, setIsPending] = useState(false);

  const handleSubmit = async () => {
    setIsPending(true);
    const error = await updateName(name);
    setIsPending(false);
    if (error) {
      setError(error);
      return;
    }
    redirect("/path");
  };
  // ...
}

// React 19 - Using useActionState
function ChangeName({ name, setName }) {
  const [error, submitAction, isPending] = useActionState(
    async (previousState, formData) => {
      const error = await updateName(formData.get("name"));
      if (error) {
        return error;
      }
      redirect("/path");
      return null;
    },
    null,
  );

  return (
    <form action={submitAction}>
      <input type="text" name="name" />
      <button type="submit" disabled={isPending}>Update</button>
      {error && <p>{error}</p>}
    </form>
  );
}
```

### New Hook: `useActionState`

```tsx
const [error, submitAction, isPending] = useActionState(
  async (previousState, newName) => {
    const error = await updateName(newName);
    if (error) {
      return error;
    }
    // handle success
    return null;
  },
  null, // initial state
);
```

### New Hook: `useOptimistic`

For optimistic UI updates:

```tsx
function ChangeName({currentName, onUpdateName}) {
  const [optimisticName, setOptimisticName] = useOptimistic(currentName);

  const submitAction = async formData => {
    const newName = formData.get("name");
    setOptimisticName(newName); // Immediate UI update
    const updatedName = await updateName(newName);
    onUpdateName(updatedName); // Update with server response
  };

  return (
    <form action={submitAction}>
      <p>Your name is: {optimisticName}</p>
      <input
        type="text"
        name="name"
        disabled={currentName !== optimisticName}
      />
    </form>
  );
}
```

### New API: `use`

Read resources (promises, context) in render:

```tsx
import {use} from 'react';

function Comments({commentsPromise}) {
  // `use` will suspend until the promise resolves
  const comments = use(commentsPromise);
  return comments.map(comment => <p key={comment.id}>{comment}</p>);
}

function Page({commentsPromise}) {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Comments commentsPromise={commentsPromise} />
    </Suspense>
  )
}
```

**Note:** `use` can be called conditionally (unlike hooks):

```tsx
function Heading({children}) {
  if (children == null) {
    return null;
  }
  // This works with `use` but not with `useContext`
  const theme = use(ThemeContext);
  return <h1 style={{color: theme.color}}>{children}</h1>;
}
```

### React 19 Ref Improvements

```tsx
// Ref as a prop (no forwardRef needed)
function MyInput({placeholder, ref}: {placeholder: string, ref: React.Ref<HTMLInputElement>}) {
  return <input placeholder={placeholder} ref={ref} />
}

// Ref cleanup functions
<input
  ref={(ref) => {
    // ref created
    return () => {
      // ref cleanup - called when element unmounts
    };
  }}
/>
```

### Context Provider Simplification

```tsx
// React 19 - Render Context as provider
const ThemeContext = createContext('');

function App({children}) {
  return (
    <ThemeContext value="dark">
      {children}
    </ThemeContext>
  );
}
```

### Document Metadata Support

```tsx
function BlogPost({post}) {
  return (
    <article>
      <h1>{post.title}</h1>
      {/* These are automatically hoisted to <head> */}
      <title>{post.title}</title>
      <meta name="author" content="Josh" />
      <link rel="author" href="https://twitter.com/joshcstory/" />
      <meta name="keywords" content={post.keywords} />
      <p>Eee equals em-see-squared...</p>
    </article>
  );
}
```

### Stylesheet Support

```tsx
function ComponentOne() {
  return (
    <Suspense fallback="loading...">
      <link rel="stylesheet" href="foo" precedence="default" />
      <link rel="stylesheet" href="bar" precedence="high" />
      <article class="foo-class bar-class">
        {/* Content won't show until stylesheets load */}
      </article>
    </Suspense>
  )
}
```

### Resource Preloading APIs

```tsx
import { prefetchDNS, preconnect, preload, preinit } from 'react-dom'

function MyComponent() {
  preinit('https://.../script.js', {as: 'script'}) // Load and execute eagerly
  preload('https://.../font.woff', { as: 'font' }) // Preload font
  preload('https://.../stylesheet.css', { as: 'style' }) // Preload stylesheet
  prefetchDNS('https://...') // When you may not request anything from this host
  preconnect('https://...') // When you will request something but aren't sure what
}
```

---

## 2. Server Components (RSC) Best Practices

### When to Use Server vs Client Components

| Use Server Components When | Use Client Components When |
|---------------------------|---------------------------|
| Fetching data from databases/APIs | State and event handlers (onClick, onChange) |
| Using API keys/secrets | Lifecycle logic (useEffect) |
| Reducing JavaScript bundle size | Browser-only APIs (localStorage, window) |
| Improving FCP and streaming | Custom hooks |
| Accessing backend resources directly | Client-side interactivity |

### Server Component Pattern

```tsx
// app/blog/page.tsx - Server Component by default
import LikeButton from '@/app/ui/like-button'
import { getPost } from '@/lib/data'

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const post = await getPost(id) // Fetch on server

  return (
    <div>
      <main>
        <h1>{post.title}</h1>
        <p>{post.content}</p>
        {/* Client Component for interactivity */}
        <LikeButton initialLikes={post.likes} postId={post.id} />
      </main>
    </div>
  )
}
```

### Client Component Pattern

```tsx
// app/ui/like-button.tsx - Client Component
'use client'

import { useState } from 'react'
import { likePost } from '@/lib/actions'

export default function LikeButton({ 
  initialLikes, 
  postId 
}: { 
  initialLikes: number
  postId: string 
}) {
  const [likes, setLikes] = useState(initialLikes)
  const [isPending, setIsPending] = useState(false)

  const handleLike = async () => {
    setIsPending(true)
    await likePost(postId)
    setLikes(prev => prev + 1)
    setIsPending(false)
  }

  return (
    <button onClick={handleLike} disabled={isPending}>
      👍 {likes}
    </button>
  )
}
```

### Interleaving Server and Client Components

Pass Server Components as props (children) to Client Components:

```tsx
// app/ui/modal.tsx - Client Component
'use client'

export default function Modal({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  
  return (
    <>
      <button onClick={() => setIsOpen(true)}>Open</button>
      {isOpen && <div className="modal">{children}</div>}
    </>
  )
}

// app/page.tsx - Server Component
import Modal from './ui/modal'
import Cart from './ui/cart' // Server Component

export default function Page() {
  return (
    <Modal>
      {/* Cart is rendered on server, Modal provides client interactivity */}
      <Cart />
    </Modal>
  )
}
```

### Context Providers Pattern

```tsx
// app/theme-provider.tsx - Client Component
'use client'

import { createContext, useContext } from 'react'

type Theme = 'light' | 'dark'
const ThemeContext = createContext<Theme>('light')

export function useTheme() {
  const theme = useContext(ThemeContext)
  if (!theme) throw new Error('useTheme must be used within ThemeProvider')
  return theme
}

export default function ThemeProvider({
  children,
  theme,
}: {
  children: React.ReactNode
  theme: Theme
}) {
  return (
    <ThemeContext.Provider value={theme}>
      {children}
    </ThemeContext.Provider>
  )
}

// app/layout.tsx - Server Component
import ThemeProvider from './theme-provider'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <body>
        {/* Render provider as deep as possible for better optimization */}
        <ThemeProvider theme="dark">{children}</ThemeProvider>
      </body>
    </html>
  )
}
```

### Third-Party Component Wrappers

```tsx
// app/ui/carousel.tsx - Wrapper for third-party component
'use client'

import { Carousel as ThirdPartyCarousel } from 'acme-carousel'

export default ThirdPartyCarousel

// app/page.tsx - Server Component
import Carousel from './ui/carousel'

export default function Page() {
  return (
    <div>
      <p>View pictures</p>
      <Carousel /> {/* Works because wrapper has 'use client' */}
    </div>
  )
}
```

### Server-Only Code Protection

```tsx
// lib/data.ts
import 'server-only' // Prevents import in Client Components

export async function getData() {
  const res = await fetch('https://external-service.com/data', {
    headers: {
      authorization: process.env.API_KEY, // Safe - never sent to client
    },
  })
  return res.json()
}
```

---

## 3. Server-Side Rendering (SSR) Patterns

### Streaming with Suspense

```tsx
// app/blog/page.tsx
import { Suspense } from 'react'
import BlogList from '@/components/BlogList'
import BlogListSkeleton from '@/components/BlogListSkeleton'

export default function BlogPage() {
  return (
    <div>
      {/* This content sent immediately */}
      <header>
        <h1>Welcome to the Blog</h1>
        <p>Read the latest posts below.</p>
      </header>
      <main>
        {/* Dynamic content streamed in */}
        <Suspense fallback={<BlogListSkeleton />}>
          <BlogList />
        </Suspense>
      </main>
    </div>
  )
}
```

### Parallel Data Fetching

```tsx
// app/artist/[username]/page.tsx
async function getArtist(username: string) {
  const res = await fetch(`https://api.example.com/artist/${username}`)
  return res.json()
}

async function getAlbums(username: string) {
  const res = await fetch(`https://api.example.com/artist/${username}/albums`)
  return res.json()
}

export default async function Page({
  params,
}: {
  params: Promise<{ username: string }>
}) {
  const { username } = await params

  // Initiate requests in parallel
  const artistData = getArtist(username)
  const albumsData = getAlbums(username)

  // Wait for both
  const [artist, albums] = await Promise.all([artistData, albumsData])

  return (
    <>
      <h1>{artist.name}</h1>
      <Albums list={albums} />
    </>
  )
}
```

### Sequential Data Fetching with Suspense

```tsx
// app/artist/[username]/page.tsx
export default async function Page({
  params,
}: {
  params: Promise<{ username: string }>
}) {
  const { username } = await params
  const artist = await getArtist(username)

  return (
    <>
      <h1>{artist.name}</h1>
      {/* Show fallback while playlists load */}
      <Suspense fallback={<div>Loading playlists...</div>}>
        <Playlists artistID={artist.id} />
      </Suspense>
    </>
  )
}

async function Playlists({ artistID }: { artistID: string }) {
  const playlists = await getArtistPlaylists(artistID)
  return (
    <ul>
      {playlists.map((playlist) => (
        <li key={playlist.id}>{playlist.name}</li>
      ))}
    </ul>
  )
}
```

### Sharing Data with React.cache

```tsx
// app/lib/user.ts
import { cache } from 'react'

export const getUser = cache(async () => {
  const res = await fetch('https://api.example.com/user')
  return res.json()
})

// app/layout.tsx - Pass promise to provider
import UserProvider from './user-provider'
import { getUser } from './lib/user'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const userPromise = getUser() // Don't await

  return (
    <html>
      <body>
        <UserProvider userPromise={userPromise}>{children}</UserProvider>
      </body>
    </html>
  )
}

// app/ui/profile.tsx - Client Component
'use client'
import { use, useContext } from 'react'
import { UserContext } from '../user-provider'

export function Profile() {
  const userPromise = useContext(UserContext)
  const user = use(userPromise!)
  return <p>Welcome, {user.name}</p>
}
```

---

## 4. React Hooks Best Practices

### Rules of Hooks (Still Critical in 2026)

1. **Only call hooks at the top level** - Never inside loops, conditions, or nested functions
2. **Only call hooks from React functions** - Components or custom hooks
3. **Use the exhaustive-deps ESLint rule** - Always properly declare dependencies

```tsx
// ❌ BAD: Hook inside condition
if (condition) {
  const [state, setState] = useState(0)
}

// ✅ GOOD: Condition inside hook
const [state, setState] = useState(condition ? 0 : 1)
```

### useState Best Practices

```tsx
// Use functional updates when new state depends on previous
const [count, setCount] = useState(0)
setCount(prev => prev + 1) // ✅ Good for async updates

// Lazy initialization for expensive computations
const [data, setData] = useState(() => {
  return expensiveComputation() // Only runs once
})

// Preserve referential stability with useCallback
const increment = useCallback(() => {
  setCount(c => c + 1)
}, []) // No dependencies needed with functional update
```

### useEffect Best Practices

```tsx
// ✅ Always clean up side effects
useEffect(() => {
  const connection = createConnection(serverUrl)
  connection.connect()
  
  return () => {
    connection.disconnect() // Cleanup
  }
}, [serverUrl])

// ✅ Separate concerns into multiple effects
useEffect(() => {
  // Handle authentication
}, [userId])

useEffect(() => {
  // Handle analytics
}, [page])

// ❌ Avoid missing dependencies
useEffect(() => {
  fetchData(userId) // ESLint: React Hook useEffect has missing dependency
}, []) // Missing userId!

// ✅ Proper dependency array
useEffect(() => {
  fetchData(userId)
}, [userId])
```

### Custom Hooks Pattern

```tsx
// hooks/useLocalStorage.ts
import { useState, useEffect, useCallback } from 'react'

export function useLocalStorage<T>(key: string, initialValue: T) {
  // Get stored value or use initial
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') return initialValue
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      console.error(error)
      return initialValue
    }
  })

  // Return a wrapped version of useState's setter
  const setValue = useCallback((value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value
      setStoredValue(valueToStore)
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore))
      }
    } catch (error) {
      console.error(error)
    }
  }, [key, storedValue])

  return [storedValue, setValue] as const
}

// Usage
function App() {
  const [name, setName] = useLocalStorage('name', '')
  return <input value={name} onChange={e => setName(e.target.value)} />
}
```

### useMemo and useCallback Guidelines

```tsx
// ✅ Memoize expensive calculations
const filteredItems = useMemo(() => {
  return items.filter(item => item.price > 100)
}, [items])

// ✅ Memoize callbacks passed to optimized children
const handleClick = useCallback(() => {
  onItemSelect(id)
}, [id, onItemSelect])

// ✅ Memoize objects/arrays passed as props
const config = useMemo(() => ({
  apiUrl: '/api',
  timeout: 5000
}), [])

// ❌ Don't memoize everything - adds overhead
const simpleValue = useMemo(() => a + b, [a, b]) // Simple math, no benefit
```

### useTransition for Non-Blocking Updates

```tsx
function TabContainer() {
  const [isPending, startTransition] = useTransition()
  const [tab, setTab] = useState('home')

  const selectTab = (nextTab: string) => {
    startTransition(() => {
      setTab(nextTab) // Non-blocking update
    })
  }

  return (
    <>
      {isPending && <Spinner />}
      <TabButton onClick={() => selectTab('home')}>Home</TabButton>
      <TabButton onClick={() => selectTab('posts')}>Posts</TabButton>
      {tab === 'home' && <HomeTab />}
      {tab === 'posts' && <PostsTab />}
    </>
  )
}
```

### useDeferredValue for Search/Filtering

```tsx
function SearchResults({ query }: { query: string }) {
  // Defer expensive re-render
  const deferredQuery = useDeferredValue(query, '') // initialValue option in React 19

  const results = useMemo(() => {
    return searchExpensive(deferredQuery)
  }, [deferredQuery])

  return (
    <>
      {/* Show stale results while computing new ones */}
      <div style={{ opacity: query !== deferredQuery ? 0.5 : 1 }}>
        {results.map(result => <Result key={result.id} {...result} />)}
      </div>
    </>
  )
}
```

---

## 5. State Management with TanStack Query

### Basic Setup

```tsx
// providers/query-provider.tsx
'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState } from 'react'

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5, // 5 minutes
        refetchOnWindowFocus: false,
        retry: 2,
      },
    },
  }))

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

### Fetching Data

```tsx
// hooks/use-posts.ts
import { useQuery } from '@tanstack/react-query'

async function fetchPosts() {
  const res = await fetch('/api/posts')
  if (!res.ok) throw new Error('Failed to fetch posts')
  return res.json()
}

export function usePosts() {
  return useQuery({
    queryKey: ['posts'],
    queryFn: fetchPosts,
  })
}

// Usage in component
function PostsList() {
  const { data: posts, isPending, error } = usePosts()

  if (isPending) return <LoadingSpinner />
  if (error) return <ErrorMessage error={error} />

  return (
    <ul>
      {posts.map(post => (
        <li key={post.id}>{post.title}</li>
      ))}
    </ul>
  )
}
```

### Mutations with Optimistic Updates

```tsx
// hooks/use-create-post.ts
import { useMutation, useQueryClient } from '@tanstack/react-query'

export function useCreatePost() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (newPost: { title: string; content: string }) => {
      const res = await fetch('/api/posts', {
        method: 'POST',
        body: JSON.stringify(newPost),
      })
      if (!res.ok) throw new Error('Failed to create post')
      return res.json()
    },
    // Optimistic update
    onMutate: async (newPost) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['posts'] })

      // Snapshot previous value
      const previousPosts = queryClient.getQueryData(['posts'])

      // Optimistically update
      queryClient.setQueryData(['posts'], (old: any) => [
        { ...newPost, id: Date.now(), isOptimistic: true },
        ...old,
  ])

      // Return context for rollback
      return { previousPosts }
    },
    onError: (err, newPost, context) => {
      // Rollback on error
      queryClient.setQueryData(['posts'], context?.previousPosts)
    },
    onSettled: () => {
      // Refetch to sync with server
      queryClient.invalidateQueries({ queryKey: ['posts'] })
    },
  })
}

// Usage
function CreatePostForm() {
  const { mutate, isPending } = useCreatePost()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate({ title: 'New Post', content: 'Content here' })
  }

  return (
    <form onSubmit={handleSubmit}>
      <button type="submit" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create Post'}
      </button>
    </form>
  )
}
```

### Infinite Queries for Pagination

```tsx
// hooks/use-infinite-posts.ts
import { useInfiniteQuery } from '@tanstack/react-query'

export function useInfinitePosts() {
  return useInfiniteQuery({
    queryKey: ['posts', 'infinite'],
    queryFn: async ({ pageParam = 1 }) => {
      const res = await fetch(`/api/posts?page=${pageParam}`)
      return res.json()
    },
    getNextPageParam: (lastPage, allPages) => {
      return lastPage.hasMore ? allPages.length + 1 : undefined
    },
    initialPageParam: 1,
  })
}

// Usage
function InfinitePostList() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfinitePosts()

  const posts = data?.pages.flatMap(page => page.posts) ?? []

  return (
    <>
      {posts.map(post => <PostCard key={post.id} post={post} />)}
      <button
        onClick={() => fetchNextPage()}
        disabled={!hasNextPage || isFetchingNextPage}
      >
        {isFetchingNextPage ? 'Loading...' : 'Load More'}
      </button>
    </>
  )
}
```

### Prefetching Data

```tsx
// Prefetch on hover
function PostLink({ post }: { post: Post }) {
  const queryClient = useQueryClient()

  return (
    <Link
      href={`/posts/${post.id}`}
      onMouseEnter={() => {
        queryClient.prefetchQuery({
          queryKey: ['posts', post.id],
          queryFn: () => fetchPost(post.id),
          staleTime: 1000 * 60, // 1 minute
        })
      }}
    >
      {post.title}
    </Link>
  )
}

// Prefetch in route handlers (Server Components)
// app/posts/page.tsx
export default async function PostsPage() {
  const queryClient = new QueryClient()
  
  await queryClient.prefetchQuery({
    queryKey: ['posts'],
    queryFn: fetchPosts,
  })

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <PostsList />
    </HydrationBoundary>
  )
}
```

---

## 6. Performance Optimization Techniques

### React Compiler (Automatic Memoization)

The React Compiler automatically memoizes components and values:

```bash
# Install
npm install babel-plugin-react-compiler

# Configure (vite.config.ts)
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: [
          ['babel-plugin-react-compiler', { target: '19' }]
        ]
      }
    })
  ]
})
```

### Code Splitting and Lazy Loading

```tsx
// Route-based code splitting
import { lazy, Suspense } from 'react'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Settings = lazy(() => import('./pages/Settings'))

function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Suspense>
  )
}

// Component-based code splitting
const HeavyChart = lazy(() => import('./components/HeavyChart'))

function Analytics() {
  const [showChart, setShowChart] = useState(false)
  
  return (
    <div>
      <button onClick={() => setShowChart(true)}>Show Chart</button>
      {showChart && (
        <Suspense fallback={<ChartSkeleton />}>
          <HeavyChart />
        </Suspense>
      )}
    </div>
  )
}
```

### Virtualization for Long Lists

```tsx
import { useVirtualizer } from '@tanstack/react-virtual'

function VirtualizedList({ items }: { items: Item[] }) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50, // Estimated row height
  })

  return (
    <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            {items[virtualItem.index].name}
          </div>
        ))}
      </div>
    </div>
  )
}
```

### Image Optimization

```tsx
// Using Next.js Image component
import Image from 'next/image'

function Avatar({ src, alt }: { src: string; alt: string }) {
  return (
    <Image
      src={src}
      alt={alt}
      width={100}
      height={100}
      priority={true} // For LCP images
      placeholder="blur"
      blurDataURL="data:image/jpeg;base64,..."
    />
  )
}

// Responsive images
function ResponsiveImage({ src, alt }: { src: string; alt: string }) {
  return (
    <Image
      src={src}
      alt={alt}
      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
      fill
      className="object-cover"
    />
  )
}
```

### Memoization Strategy

```tsx
// 1. Memoize expensive components
const ExpensiveComponent = memo(function ExpensiveComponent({ data }) {
  // Heavy rendering logic
  return <div>{/* ... */}</div>
})

// 2. Use production comparison function if needed
const MemoizedItem = memo(Item, (prev, next) => {
  return prev.id === next.id && prev.updatedAt === next.updatedAt
})

// 3. Memoize context value
function AppProvider({ children }) {
  const [user, setUser] = useState(null)
  
  const value = useMemo(() => ({
    user,
    setUser,
    login: (data) => setUser(data),
    logout: () => setUser(null),
  }), [user])

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  )
}
```

### Web Workers for Heavy Computation

```tsx
// hooks/use-web-worker.ts
import { useEffect, useRef, useCallback } from 'react'

export function useWebWorker<T, R>(workerScript: string) {
  const workerRef = useRef<Worker | null>(null)

  useEffect(() => {
    workerRef.current = new Worker(workerScript)
    return () => workerRef.current?.terminate()
  }, [workerScript])

  const postMessage = useCallback((data: T): Promise<R> => {
    return new Promise((resolve, reject) => {
      if (!workerRef.current) return reject('Worker not initialized')
      
      const handleMessage = (e: MessageEvent) => {
        resolve(e.data)
        workerRef.current?.removeEventListener('message', handleMessage)
      }
      
      workerRef.current.addEventListener('message', handleMessage)
      workerRef.current.postMessage(data)
    })
  }, [])

  return { postMessage }
}

// Usage
function DataProcessor() {
  const { postMessage } = useWebWorker('/workers/data-processor.js')

  const processData = async (data: LargeDataSet) => {
    const result = await postMessage(data)
    setProcessedData(result)
  }

  return <button onClick={() => processData(rawData)}>Process</button>
}
```

---

## 7. Modern React Architecture Patterns

### Feature-Based Folder Structure

```
app/
├── features/
│   ├── auth/
│   │   ├── api/
│   │   │   ├── login.ts
│   │   │   └── register.ts
│   │   ├── components/
│   │   │   ├── LoginForm.tsx
│   │   │   └── RegisterForm.tsx
│   │   ├── hooks/
│   │   │   ├── use-auth.ts
│   │   │   └── use-login.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   └── utils/
│   │       └── validation.ts
│   ├── posts/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── types/
│   └── users/
│       ├── api/
│       ├── components/
│       ├── hooks/
│       └── types/
├── shared/
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   └── Modal.tsx
│   │   └── layout/
│   │       ├── Header.tsx
│   │       └── Footer.tsx
│   ├── hooks/
│   ├── lib/
│   │   ├── utils.ts
│   │   └── constants.ts
│   └── types/
└── providers/
    ├── query-provider.tsx
    └── theme-provider.tsx
```

### Compound Component Pattern

```tsx
// components/accordion.tsx
import { createContext, useContext, useState } from 'react'

const AccordionContext = createContext<{
  openItem: string | null
  setOpenItem: (item: string | null) => void
} | null>(null)

function Accordion({ children }: { children: React.ReactNode }) {
  const [openItem, setOpenItem] = useState<string | null>(null)
  
  return (
    <AccordionContext value={{ openItem, setOpenItem }}>
      <div className="accordion">{children}</div>
    </AccordionContext>
  )
}

function Item({ 
  id, 
  children 
}: { 
  id: string
  children: React.ReactNode 
}) {
  return <div className="accordion-item">{children}</div>
}

function Trigger({ 
  itemId, 
  children 
}: { 
  itemId: string
  children: React.ReactNode 
}) {
  const context = useContext(AccordionContext)
  if (!context) throw new Error('Trigger must be used within Accordion')
  
  const { openItem, setOpenItem } = context
  const isOpen = openItem === itemId

  return (
    <button 
      className="accordion-trigger"
      onClick={() => setOpenItem(isOpen ? null : itemId)}
    >
      {children}
      <span>{isOpen ? '−' : '+'}</span>
    </button>
  )
}

function Content({ 
  itemId, 
  children 
}: { 
  itemId: string
  children: React.ReactNode 
}) {
  const context = useContext(AccordionContext)
  if (!context) throw new Error('Content must be used within Accordion')
  
  const { openItem } = context
  if (openItem !== itemId) return null

  return <div className="accordion-content">{children}</div>
}

Accordion.Item = Item
Accordion.Trigger = Trigger
Accordion.Content = Content

export { Accordion }

// Usage
function FAQ() {
  return (
    <Accordion>
      <Accordion.Item id="q1">
        <Accordion.Trigger itemId="q1">What is React?</Accordion.Trigger>
        <Accordion.Content itemId="q1">React is a library...</Accordion.Content>
      </Accordion.Item>
      <Accordion.Item id="q2">
        <Accordion.Trigger itemId="q2">What are hooks?</Accordion.Trigger>
        <Accordion.Content itemId="q2">Hooks are functions...</Accordion.Content>
      </Accordion.Item>
    </Accordion>
  )
}
```

### Render Props Pattern

```tsx
// components/data-fetcher.tsx
type DataFetcherProps<T> = {
  url: string
  children: (data: T, isLoading: boolean, error: Error | null) => React.ReactNode
}

function DataFetcher<T>({ url, children }: DataFetcherProps<T>) {
  const [data, setData] = useState<T | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    fetch(url)
      .then(res => res.json())
      .then(setData)
      .catch(setError)
      .finally(() => setIsLoading(false))
  }, [url])

  return <>{children(data as T, isLoading, error)}</>
}

// Usage
function UserProfile({ userId }: { userId: string }) {
  return (
    <DataFetcher url={`/api/users/${userId}`}>
      {(user, isLoading, error) => {
        if (isLoading) return <Spinner />
        if (error) return <ErrorMessage error={error} />
        return (
          <div>
            <h1>{user.name}</h1>
            <p>{user.email}</p>
          </div>
        )
      }}
    </DataFetcher>
  )
}
```

### Container/Presentational Pattern

```tsx
// containers/user-profile-container.tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import { UserProfileView } from './user-profile-view'

export function UserProfileContainer({ userId }: { userId: string }) {
  const { data: user, isLoading, error } = useQuery({
    queryKey: ['users', userId],
    queryFn: () => fetchUser(userId),
  })

  return (
    <UserProfileView 
      user={user} 
      isLoading={isLoading} 
      error={error} 
    />
  )
}

// components/user-profile-view.tsx
interface UserProfileViewProps {
  user?: User
  isLoading: boolean
  error: Error | null
}

export function UserProfileView({ user, isLoading, error }: UserProfileViewProps) {
  if (isLoading) return <Skeleton />
  if (error) return <ErrorState error={error} />
  if (!user) return null

  return (
    <div className="user-profile">
      <Avatar src={user.avatar} name={user.name} />
      <h1>{user.name}</h1>
      <p>{user.bio}</p>
    </div>
  )
}
```

### Higher-Order Component (HOC) Pattern

```tsx
// hocs/with-auth.tsx
import { redirect } from 'next/navigation'
import { useSession } from '@/lib/auth'

export function withAuth<P extends object>(
  Component: React.ComponentType<P>
) {
  return function WithAuthComponent(props: P) {
    const session = useSession()

    if (!session) {
      redirect('/login')
    }

    return <Component {...props} user={session.user} />
  }
}

// Usage
function Dashboard({ user }: { user: User }) {
  return <div>Welcome, {user.name}!</div>
}

export default withAuth(Dashboard)
```

---

## 8. File Structure and Organization

### Next.js App Router Structure (2026 Recommended)

```
my-app/
├── app/                          # Next.js App Router
│   ├── (marketing)/              # Route group (no URL segment)
│   │   ├── layout.tsx            # Marketing layout
│   │   ├── page.tsx              # Landing page
│   │   ├── about/
│   │   │   └── page.tsx
│   │   └── pricing/
│   │       └── page.tsx
│   ├── (dashboard)/              # Dashboard route group
│   │   ├── layout.tsx            # Dashboard layout
│   │   ├── dashboard/
│   │   │   ├── page.tsx
│   │   │   ├── loading.tsx       # Suspense fallback
│   │   │   └── error.tsx         # Error boundary
│   │   ├── settings/
│   │   │   ├── page.tsx
│   │   │   ├── loading.tsx
│   │   │   └── error.tsx
│   │   └── profile/
│   │       └── page.tsx
│   ├── api/                      # API routes
│   │   ├── auth/
│   │   │   └── [...nextauth]/
│   │   │       └── route.ts
│   │   └── webhooks/
│   │       └── stripe/
│   │           └── route.ts
│   ├── layout.tsx                # Root layout
│   ├── page.tsx                  # Root page
│   ├── loading.tsx               # Root loading state
│   ├── error.tsx                 # Root error boundary
│   ├── not-found.tsx             # 404 page
│   ├── globals.css
│   └── robots.ts
├── components/
│   ├── ui/                       # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   └── card.tsx
│   ├── forms/                    # Form components
│   │   ├── login-form.tsx
│   │   └── signup-form.tsx
│   └── providers/                # Context providers
│       ├── query-provider.tsx
│       └── theme-provider.tsx
├── hooks/                        # Custom hooks
│   ├── use-local-storage.ts
│   └── use-media-query.ts
├── lib/                          # Utilities
│   ├── utils.ts                  # cn() and helpers
│   ├── db.ts                     # Database client
│   └── api.ts                    # API helpers
├── types/                        # TypeScript types
│   ├── index.ts
│   ├── user.ts
│   └── api.ts
├── config/                       # Configuration
│   ├── site.ts
│   └── constants.ts
├── public/                       # Static assets
│   ├── images/
│   └── fonts/
├── styles/                       # Additional styles
│   └── globals.css
├── tests/                        # Test files
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── middleware.ts                 # Next.js middleware
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### Component File Structure

```tsx
// Component file template
import { useState } from 'react' // React imports
import { cn } from '@/lib/utils' // Utility imports
import { Button } from '@/components/ui/button' // Component imports
import { useAuth } from '@/hooks/use-auth' // Hook imports
import type { User } from '@/types' // Type imports

// Types
interface UserCardProps {
  user: User
  onEdit?: (user: User) => void
  className?: string
}

// Component
export function UserCard({ user, onEdit, className }: UserCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const { isAuthenticated } = useAuth()

  return (
    <div className={cn('rounded-lg border', className)}>
      {/* Component JSX */}
    </div>
  )
}

// Default export (when needed)
export default UserCard
```

### Barrel Exports

```ts
// components/ui/index.ts
export { Button } from './button'
export { Input } from './input'
export { Card, CardHeader, CardContent, CardFooter } from './card'
export { Dialog, DialogContent, DialogHeader, DialogTitle } from './dialog'

// Usage
import { Button, Input, Card } from '@/components/ui'
```

---

## 9. TypeScript Integration Best Practices

### tsconfig.json Recommended Settings

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "ES2022"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### Component Props Typing

```tsx
// Use interfaces for object types
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
  onClick?: () => void
  disabled?: boolean
  className?: string
}

// Use type for unions
type Status = 'idle' | 'loading' | 'success' | 'error'

// Use satisfies for config objects
const config = {
  apiUrl: '/api',
  timeout: 5000,
} satisfies Record<string, string | number>

// Component with typed props
export function Button({ 
  variant = 'primary',
  size = 'md',
  children,
  onClick,
  disabled,
  className,
}: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  )
}
```

### Hooks Typing

```tsx
// useState with explicit types
const [user, setUser] = useState<User | null>(null)
const [count, setCount] = useState<number>(0)

// useReducer with typed actions
type CounterAction =
  | { type: 'increment' }
  | { type: 'decrement' }
  | { type: 'set'; value: number }
  | { type: 'reset' }

interface CounterState {
  count: number
}

function counterReducer(state: CounterState, action: CounterAction): CounterState {
  switch (action.type) {
    case 'increment':
      return { count: state.count + 1 }
    case 'decrement':
      return { count: state.count - 1 }
    case 'set':
      return { count: action.value }
    case 'reset':
      return { count: 0 }
    default:
      return state
  }
}

const [state, dispatch] = useReducer(counterReducer, { count: 0 })

// useRef for DOM elements
const inputRef = useRef<HTMLInputElement>(null)

// useRef for mutable values
const timerRef = useRef<number | null>(null)

// useCallback with typed parameters
const handleChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
  setValue(event.target.value)
}, [])

// useMemo with return type
const sortedItems = useMemo<Item[]>(() => {
  return [...items].sort((a, b) => a.order - b.order)
}, [items])
```

### Generic Components

```tsx
// Generic list component
interface ListProps<T> {
  items: T[]
  renderItem: (item: T) => React.ReactNode
  keyExtractor: (item: T) => string | number
}

export function List<T>({ items, renderItem, keyExtractor }: ListProps<T>) {
  return (
    <ul>
      {items.map(item => (
        <li key={keyExtractor(item)}>{renderItem(item)}</li>
      ))}
    </ul>
  )
}

// Usage
interface User {
  id: string
  name: string
}

function UserList({ users }: { users: User[] }) {
  return (
    <List
      items={users}
      renderItem={user => <span>{user.name}</span>}
      keyExtractor={user => user.id}
    />
  )
}
```

### API Types

```ts
// types/api.ts
export interface ApiResponse<T> {
  data: T
  success: boolean
  message?: string
}

export interface ApiError {
  message: string
  code: string
  details?: Record<string, string[]>
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  perPage: number
  totalPages: number
}

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

// Usage
async function fetchUsers(): Promise<ApiResponse<User[]>> {
  const res = await fetch('/api/users')
  if (!res.ok) {
    const error: ApiError = await res.json()
    throw new Error(error.message)
  }
  return res.json()
}
```

### Utility Types

```ts
// types/utils.ts
export type Nullable<T> = T | null
export type Optional<T> = T | undefined
export type Maybe<T> = T | null | undefined

// Make specific properties optional
export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>

// Make specific properties required
export type RequiredBy<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>

// Deep partial for nested objects
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

// Usage
type User = {
  id: string
  name: string
  email: string
  profile: {
    bio: string
    avatar: string
  }
}

type CreateUserInput = PartialBy<User, 'id'>
// { name: string; email: string; profile: {...}; id?: string }
```

### Context Typing

```tsx
// types/theme.ts
export type Theme = 'light' | 'dark' | 'system'

export interface ThemeContextType {
  theme: Theme
  setTheme: (theme: Theme) => void
  resolvedTheme: 'light' | 'dark'
}

// context/theme-context.tsx
import { createContext, useContext } from 'react'
import type { ThemeContextType } from '@/types/theme'

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Implementation...
  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}
```

### Zod for Runtime Validation

```ts
// schemas/user.ts
import { z } from 'zod'

export const userSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(2).max(100),
  email: z.string().email(),
  age: z.number().int().min(0).max(150).optional(),
  role: z.enum(['user', 'admin', 'moderator']),
  createdAt: z.date(),
})

export const createUserSchema = userSchema.omit({ id: true, createdAt: true })
export const updateUserSchema = createUserSchema.partial()

// Infer TypeScript types from Zod schemas
export type User = z.infer<typeof userSchema>
export type CreateUserInput = z.infer<typeof createUserSchema>
export type UpdateUserInput = z.infer<typeof updateUserSchema>

// Usage
function createUser(data: unknown): User {
  const validated = createUserSchema.parse(data)
  // validated is now typed as CreateUserInput
  return {
    ...validated,
    id: crypto.randomUUID(),
    createdAt: new Date(),
  }
}
```

---

## Quick Reference: 2026 React Checklist

### ✅ Do's

- [ ] Use Server Components by default, add `'use client'` only when needed
- [ ] Use React 19's Actions for form submissions and mutations
- [ ] Use `useOptimistic` for optimistic UI updates
- [ ] Implement proper error boundaries with `error.tsx` files
- [ ] Use Suspense boundaries for streaming
- [ ] Use TanStack Query for server state management
- [ ] Use `React.cache` for request-scoped data sharing
- [ ] Use TypeScript strict mode
- [ ] Implement proper loading states with `loading.tsx`
- [ ] Use the `use` API for promise consumption
- [ ] Memoize expensive calculations with `useMemo`
- [ ] Use `useCallback` for stable function references
- [ ] Implement proper cleanup in `useEffect`
- [ ] Use `server-only` and `client-only` packages
- [ ] Implement proper accessibility (ARIA, keyboard navigation)

### ❌ Don'ts

- [ ] Don't fetch data in `useEffect` in Server Components
- [ ] Don't use Context in Server Components
- [ ] Don't forget dependency arrays in hooks
- [ ] Don't over-memoize simple values
- [ ] Don't mix server and client logic without proper boundaries
- [ ] Don't expose sensitive data in Client Components
- [ ] Don't ignore TypeScript errors
- [ ] Don't create promises in render (for `use` API)
- [ ] Don't use `any` type excessively

---

## Additional Resources

- [React Official Documentation](https://react.dev)
- [Next.js Documentation](https://nextjs.org/docs)
- [TanStack Query Documentation](https://tanstack.com/query/latest)
- [TypeScript Documentation](https://www.typescriptlang.org/docs)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)

---

*Last Updated: April 2026*
