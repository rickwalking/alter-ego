# Minimizing useEffect: A Comprehensive Guide to Modern React Patterns

## Table of Contents
1. [Why useEffect is Considered Harmful](#1-why-useeffect-is-considered-harmful)
2. [Server Components as useEffect Replacement](#2-server-components-as-useeffect-replacement)
3. [TanStack Query as Data Fetching Alternative](#3-tanstack-query-as-data-fetching-alternative)
4. [useLayoutEffect vs useEffect](#4-uselayouteffect-vs-useeffect)
5. [React 19 use() Hook and Suspense](#5-react-19-use-hook-and-suspense)
6. [Event Handlers Instead of Effects](#6-event-handlers-instead-of-effects)
7. [Derived State Patterns](#7-derived-state-patterns)
8. [useSyncExternalStore for External Data](#8-usesyncexternalstore-for-external-data)
9. [Refs for Imperative Operations](#9-refs-for-imperative-operations)
10. [Component Composition Over Effects](#10-component-composition-over-effects)

---

## 1. Why useEffect is Considered Harmful

### The Problems with useEffect

**1. Timing Issues and Race Conditions**
```jsx
// ❌ BEFORE: Race condition prone
function UserProfile({ userId }) {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    fetchUser(userId).then(data => setUser(data));
  }, [userId]);
  // What if userId changes before fetch completes?
  // Stale data might be set!
}
```

**2. Over-rendering**
```jsx
// ❌ BEFORE: Multiple unnecessary renders
function ProductList() {
  const [products, setProducts] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [search, setSearch] = useState('');
  
  useEffect(() => {
    fetchProducts().then(setProducts);
  }, []);
  
  useEffect(() => {
    setFiltered(products.filter(p => 
      p.name.includes(search)
    ));
  }, [products, search]);
  // Every keystroke triggers: render → effect → setState → re-render
}
```

**3. Dependency Array Hell**
```jsx
// ❌ BEFORE: Missing dependencies cause bugs, too many cause infinite loops
function Chat({ roomId }) {
  const [messages, setMessages] = useState([]);
  const [connection, setConnection] = useState(null);
  
  useEffect(() => {
    const conn = createConnection(roomId);
    conn.connect();
    setConnection(conn);
    
    return () => conn.disconnect();
  }, [roomId]); // What if createConnection depends on auth token?
}
```

**4. SSR/ hydration Mismatch**
```jsx
// ❌ BEFORE: Hydration issues
function Clock() {
  const [time, setTime] = useState(new Date());
  
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  
  // Server renders one time, client hydrates with different time
  return <div>{time.toLocaleTimeString()}</div>;
}
```

### Key Principles

1. **Effects run after render** - They can't prevent unnecessary renders
2. **Effects don't block painting** - Visual inconsistencies possible
3. **Cleanup is manual** - Easy to forget, causing memory leaks
4. **Dependencies are fragile** - Lint rules help but aren't perfect

---

## 2. Server Components as useEffect Replacement

### Data Fetching on the Server

```jsx
// ❌ BEFORE: Client-side data fetching with useEffect
'use client';

import { useEffect, useState } from 'react';

export function ProductPage({ productId }) {
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetch(`/api/products/${productId}`)
      .then(r => r.json())
      .then(data => {
        setProduct(data);
        setLoading(false);
      });
  }, [productId]);
  
  if (loading) return <Spinner />;
  
  return (
    <div>
      <h1>{product.name}</h1>
      <p>{product.description}</p>
    </div>
  );
}
```

```jsx
// ✅ AFTER: Server Component fetches data directly
// No 'use client' needed!

async function getProduct(id) {
  const res = await fetch(`https://api.example.com/products/${id}`, {
    next: { revalidate: 60 }
  });
  return res.json();
}

export default async function ProductPage({ params }) {
  const product = await getProduct(params.productId);
  // Data is available immediately, no loading states needed!
  
  return (
    <div>
      <h1>{product.name}</h1>
      <p>{product.description}</p>
      {/* Can pass data to Client Components if needed */}
      <AddToCartButton productId={product.id} />
    </div>
  );
}
```

### Parallel Data Fetching

```jsx
// ❌ BEFORE: Sequential fetches with useEffect
function Dashboard() {
  const [user, setUser] = useState(null);
  const [orders, setOrders] = useState([]);
  const [notifications, setNotifications] = useState([]);
  
  useEffect(() => {
    // These run sequentially! Slow!
    fetchUser().then(setUser);
    fetchOrders().then(setOrders);
    fetchNotifications().then(setNotifications);
  }, []);
}
```

```jsx
// ✅ AFTER: Parallel fetching in Server Component
async function getDashboardData() {
  // All fetch simultaneously!
  const [user, orders, notifications] = await Promise.all([
    fetchUser(),
    fetchOrders(),
    fetchNotifications()
  ]);
  
  return { user, orders, notifications };
}

export default async function Dashboard() {
  const { user, orders, notifications } = await getDashboardData();
  
  return (
    <div>
      <UserCard user={user} />
      <OrderList orders={orders} />
      <NotificationBell count={notifications.length} />
    </div>
  );
}
```

### Streaming with Suspense Boundaries

```jsx
// ✅ AFTER: Streaming with Suspense
import { Suspense } from 'react';

export default function ProductPage({ params }) {
  return (
    <div>
      {/* This renders immediately */}
      <ProductSkeleton />
      
      {/* These stream in as they're ready */}
      <Suspense fallback={<ReviewsSkeleton />}>
        <Reviews productId={params.id} />
      </Suspense>
      
      <Suspense fallback={<RelatedSkeleton />}>
        <RelatedProducts productId={params.id} />
      </Suspense>
    </div>
  );
}

async function Reviews({ productId }) {
  const reviews = await fetchReviews(productId);
  return <ReviewsList reviews={reviews} />;
}

async function RelatedProducts({ productId }) {
  const products = await fetchRelated(productId);
  return <ProductGrid products={products} />;
}
```

---

## 3. TanStack Query as Data Fetching Alternative

### Why TanStack Query is Superior

```jsx
// ❌ BEFORE: Manual fetching with useEffect
import { useEffect, useState } from 'react';

function UserList() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    let cancelled = false;
    
    async function fetchUsers() {
      setLoading(true);
      setError(null);
      
      try {
        const res = await fetch('/api/users');
        if (!res.ok) throw new Error('Failed to fetch');
        const data = await res.json();
        
        if (!cancelled) {
          setUsers(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    
    fetchUsers();
    
    return () => { cancelled = true; };
  }, []);
  
  if (loading) return <Spinner />;
  if (error) return <Error message={error} />;
  
  return (
    <ul>
      {users.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}
```

```jsx
// ✅ AFTER: TanStack Query handles everything
import { useQuery } from '@tanstack/react-query';

function UserList() {
  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: fetchUsers,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,   // 10 minutes (formerly cacheTime)
  });
  
  if (isLoading) return <Spinner />;
  if (error) return <Error message={error.message} />;
  
  return (
    <ul>
      {users.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}

async function fetchUsers() {
  const res = await fetch('/api/users');
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
}
```

### Caching and Background Updates

```jsx
// ❌ BEFORE: No caching, refetch on every mount
function ProductDetails({ productId }) {
  const [product, setProduct] = useState(null);
  
  useEffect(() => {
    fetchProduct(productId).then(setProduct);
  }, [productId]);
  // Every navigation refetches!
}
```

```jsx
// ✅ AFTER: Automatic caching and background updates
function ProductDetails({ productId }) {
  const { data: product, isFetching } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => fetchProduct(productId),
    // Automatic features:
    // - Caches by queryKey
    // - Background refetch on window focus
    // - Stale-while-revalidate pattern
    // - Automatic retry on error
    // - Deduplicates concurrent requests
  });
  
  return (
    <div className={isFetching ? 'opacity-50' : ''}>
      <h1>{product?.name}</h1>
    </div>
  );
}
```

### Mutations with Optimistic Updates

```jsx
// ❌ BEFORE: Manual optimistic updates with useEffect
function TodoList() {
  const [todos, setTodos] = useState([]);
  
  const addTodo = async (text) => {
    const tempId = Date.now();
    const optimisticTodo = { id: tempId, text, completed: false };
    
    // Optimistically add
    setTodos(prev => [...prev, optimisticTodo]);
    
    try {
      const saved = await fetch('/api/todos', {
        method: 'POST',
        body: JSON.stringify({ text })
      }).then(r => r.json());
      
      // Replace temp with real
      setTodos(prev => 
        prev.map(t => t.id === tempId ? saved : t)
      );
    } catch (err) {
      // Rollback on error
      setTodos(prev => prev.filter(t => t.id !== tempId));
    }
  };
}
```

```jsx
// ✅ AFTER: Declarative mutations with automatic rollback
import { useMutation, useQueryClient } from '@tanstack/react-query';

function TodoList() {
  const queryClient = useQueryClient();
  
  const addTodo = useMutation({
    mutationFn: (text) => 
      fetch('/api/todos', {
        method: 'POST',
        body: JSON.stringify({ text })
      }).then(r => r.json()),
    
    onMutate: async (text) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['todos'] });
      
      // Snapshot previous value
      const previousTodos = queryClient.getQueryData(['todos']);
      
      // Optimistically update
      queryClient.setQueryData(['todos'], old => [
        ...old,
        { id: Date.now(), text, completed: false }
      ]);
      
      return { previousTodos };
    },
    
    onError: (err, text, context) => {
      // Rollback on error
      queryClient.setQueryData(['todos'], context.previousTodos);
    },
    
    onSettled: () => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: ['todos'] });
    }
  });
  
  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      addTodo.mutate(e.target.text.value);
    }}>
      <input name="text" />
      <button disabled={addTodo.isPending}>Add</button>
    </form>
  );
}
```

### Infinite Queries

```jsx
// ❌ BEFORE: Complex infinite scroll with useEffect
function Feed() {
  const [posts, setPosts] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const loaderRef = useRef(null);
  
  useEffect(() => {
    if (!hasMore) return;
    
    fetchPosts(page).then(newPosts => {
      setPosts(prev => [...prev, ...newPosts]);
      setHasMore(newPosts.length === 10);
    });
  }, [page, hasMore]);
  
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting) {
          setPage(p => p + 1);
        }
      }
    );
    
    if (loaderRef.current) {
      observer.observe(loaderRef.current);
    }
    
    return () => observer.disconnect();
  }, []);
  
  return (
    <>
      {posts.map(post => <Post key={post.id} {...post} />)}
      {hasMore && <div ref={loaderRef}>Loading...</div>}
    </>
  );
}
```

```jsx
// ✅ AFTER: Declarative infinite queries
import { useInfiniteQuery } from '@tanstack/react-query';
import { useInView } from 'react-intersection-observer';

function Feed() {
  const { ref, inView } = useInView();
  
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['posts'],
    queryFn: ({ pageParam = 1 }) => fetchPosts(pageParam),
    getNextPageParam: (lastPage, pages) => 
      lastPage.length === 10 ? pages.length + 1 : undefined,
    initialPageParam: 1,
  });
  
  useEffect(() => {
    if (inView && hasNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, fetchNextPage]);
  
  const posts = data?.pages.flat() ?? [];
  
  return (
    <>
      {posts.map(post => <Post key={post.id} {...post} />)}
      {hasNextPage && (
        <div ref={ref}>
          {isFetchingNextPage ? 'Loading more...' : 'Load more'}
        </div>
      )}
    </>
  );
}
```

---

## 4. useLayoutEffect vs useEffect

### When to Use Each

```jsx
// ❌ BEFORE: useEffect causing visual flicker
function Tooltip({ targetRef, children }) {
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const tooltipRef = useRef(null);
  
  useEffect(() => {
    // This runs AFTER paint - user sees tooltip jump!
    const targetRect = targetRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    
    setPosition({
      top: targetRect.bottom + 8,
      left: targetRect.left + (targetRect.width - tooltipRect.width) / 2
    });
  }, []);
  
  return (
    <div 
      ref={tooltipRef}
      style={{ position: 'absolute', ...position }}
    >
      {children}
    </div>
  );
}
```

```jsx
// ✅ AFTER: useLayoutEffect prevents flicker
import { useLayoutEffect } from 'react';

function Tooltip({ targetRef, children }) {
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const tooltipRef = useRef(null);
  
  useLayoutEffect(() => {
    // This runs BEFORE paint - positioning is correct immediately
    const targetRect = targetRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    
    setPosition({
      top: targetRect.bottom + 8,
      left: targetRect.left + (targetRect.width - tooltipRect.width) / 2
    });
  }, []);
  
  return (
    <div 
      ref={tooltipRef}
      style={{ position: 'absolute', ...position }}
    >
      {children}
    </div>
  );
}
```

### Better: Avoid Effect Altogether

```jsx
// ✅ BEST: CSS-based positioning, no effect needed
function Tooltip({ children }) {
  return (
    <div className="tooltip-container">
      {children}
      <div className="tooltip">
        Tooltip content
      </div>
    </div>
  );
}

// CSS handles positioning automatically
// .tooltip-container { position: relative; }
// .tooltip { 
//   position: absolute;
//   top: 100%;
//   left: 50%;
//   transform: translateX(-50%);
//   margin-top: 8px;
// }
```

### Comparison Table

| Aspect | useEffect | useLayoutEffect |
|--------|-----------|-----------------|
| Timing | After paint | Before paint (blocking) |
| Use case | Most side effects | DOM measurements/mutations |
| Performance | Non-blocking | Blocking - can hurt perf |
| SSR-safe | Yes | No (warns, falls back to useEffect) |

### Practical Guidelines

```jsx
// ✅ useEffect: Data fetching, subscriptions, event listeners
useEffect(() => {
  const ws = new WebSocket('wss://api.example.com');
  ws.onmessage = (e) => setData(JSON.parse(e.data));
  return () => ws.close();
}, []);

// ✅ useLayoutEffect: DOM measurements that affect visual output
useLayoutEffect(() => {
  const height = elementRef.current.getBoundingClientRect().height;
  setMeasuredHeight(height);
}, [content]);

// ✅ Neither: Animations should use CSS or requestAnimationFrame
// ❌ Don't use effects for animations
```

---

## 5. React 19 use() Hook and Suspense

### The use() Hook

```jsx
// ❌ BEFORE: useEffect with loading states
function Comments({ postId }) {
  const [comments, setComments] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    setIsLoading(true);
    fetchComments(postId)
      .then(data => {
        setComments(data);
        setIsLoading(false);
      });
  }, [postId]);
  
  if (isLoading) return <Spinner />;
  
  return (
    <ul>
      {comments.map(c => <li key={c.id}>{c.text}</li>)}
    </ul>
  );
}
```

```jsx
// ✅ AFTER: use() with Suspense
import { use, Suspense } from 'react';

function Comments({ postId }) {
  // use() can be called conditionally and inside loops!
  const comments = use(fetchComments(postId));
  
  return (
    <ul>
      {comments.map(c => <li key={c.id}>{c.text}</li>)}
    </ul>
  );
}

// Parent handles loading with Suspense
function Post({ postId }) {
  return (
    <article>
      <h1>My Post</h1>
      <Suspense fallback={<CommentsSkeleton />}>
        <Comments postId={postId} />
      </Suspense>
    </article>
  );
}
```

### Conditional Data Fetching

```jsx
// ❌ BEFORE: Complex conditional fetching with useEffect
function UserProfile({ userId, showDetails }) {
  const [user, setUser] = useState(null);
  const [details, setDetails] = useState(null);
  
  useEffect(() => {
    fetchUser(userId).then(setUser);
  }, [userId]);
  
  useEffect(() => {
    if (showDetails) {
      fetchUserDetails(userId).then(setDetails);
    }
  }, [userId, showDetails]);
  
  // ...
}
```

```jsx
// ✅ AFTER: Conditional fetching with use()
function UserProfile({ userId, showDetails }) {
  const user = use(fetchUser(userId));
  
  return (
    <div>
      <h1>{user.name}</h1>
      {showDetails && (
        <Suspense fallback={<DetailsSkeleton />}>
          <UserDetails userId={userId} />
        </Suspense>
      )}
    </div>
  );
}

function UserDetails({ userId }) {
  // Only fetches when component renders (showDetails is true)
  const details = use(fetchUserDetails(userId));
  return <div>{details.bio}</div>;
}
```

### Using Promises from Context

```jsx
// ✅ AFTER: Pass promises through context
import { createContext, use, Suspense, useState } from 'react';

const CommentsContext = createContext(null);

function CommentsProvider({ children }) {
  // Create promise once, not on every render
  const [commentsPromise] = useState(() => fetchComments());
  
  return (
    <CommentsContext.Provider value={commentsPromise}>
      {children}
    </CommentsContext.Provider>
  );
}

function CommentList() {
  // use() unwraps the promise from context
  const commentsPromise = use(CommentsContext);
  const comments = use(commentsPromise);
  
  return (
    <ul>
      {comments.map(c => <li key={c.id}>{c.text}</li>)}
    </ul>
  );
}
```

### Error Boundaries with use()

```jsx
// ✅ AFTER: Errors caught by Error Boundary
import { ErrorBoundary } from 'react-error-boundary';

function App() {
  return (
    <ErrorBoundary fallback={<ErrorFallback />}>
      <Suspense fallback={<Spinner />}>
        <UserProfile userId={123} />
      </Suspense>
    </ErrorBoundary>
  );
}

function UserProfile({ userId }) {
  // If fetchUser throws, ErrorBoundary catches it
  const user = use(fetchUser(userId));
  return <h1>{user.name}</h1>;
}
```

---

## 6. Event Handlers Instead of Effects

### Form Submission

```jsx
// ❌ BEFORE: useEffect for form submission
function ContactForm() {
  const [formData, setFormData] = useState({ name: '', email: '' });
  const [shouldSubmit, setShouldSubmit] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  useEffect(() => {
    if (!shouldSubmit) return;
    
    setIsSubmitting(true);
    fetch('/api/contact', {
      method: 'POST',
      body: JSON.stringify(formData)
    }).then(() => {
      setIsSubmitting(false);
      setShouldSubmit(false);
    });
  }, [shouldSubmit, formData]);
  
  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      setShouldSubmit(true);
    }}>
      {/* ... */}
    </form>
  );
}
```

```jsx
// ✅ AFTER: Direct event handler
function ContactForm() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    const formData = new FormData(e.target);
    await fetch('/api/contact', {
      method: 'POST',
      body: JSON.stringify(Object.fromEntries(formData))
    });
    
    setIsSubmitting(false);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input name="name" required />
      <input name="email" type="email" required />
      <button disabled={isSubmitting}>
        {isSubmitting ? 'Sending...' : 'Send'}
      </button>
    </form>
  );
}
```

### Search Input

```jsx
// ❌ BEFORE: Effect with debounce
function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  
  useEffect(() => {
    if (!query) {
      setResults([]);
      return;
    }
    
    const timer = setTimeout(() => {
      searchAPI(query).then(setResults);
    }, 300);
    
    return () => clearTimeout(timer);
  }, [query]);
  
  return (
    <div>
      <input 
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <ul>{results.map(r => <li key={r.id}>{r.name}</li>)}</ul>
    </div>
  );
}
```

```jsx
// ✅ AFTER: Event handler with transition
import { useTransition } from 'react';
import { useDeferredValue } from 'react';

function Search() {
  const [query, setQuery] = useState('');
  const [isPending, startTransition] = useTransition();
  const deferredQuery = useDeferredValue(query);
  
  // Results component uses deferredQuery for non-blocking updates
  return (
    <div>
      <input 
        value={query}
        onChange={(e) => {
          // Update immediately for responsive input
          setQuery(e.target.value);
          // Search results update in transition
          startTransition(() => {
            // Trigger search
          });
        }}
      />
      {isPending && <Spinner />}
      <SearchResults query={deferredQuery} />
    </div>
  );
}

function SearchResults({ query }) {
  const { data: results } = useQuery({
    queryKey: ['search', query],
    queryFn: () => searchAPI(query),
    enabled: query.length > 0,
  });
  
  return (
    <ul>
      {results?.map(r => <li key={r.id}>{r.name}</li>)}
    </ul>
  );
}
```

### URL State Management

```jsx
// ❌ BEFORE: Syncing URL with useEffect
function FilterableList() {
  const [filters, setFilters] = useState({ category: '', sort: '' });
  const router = useRouter();
  
  useEffect(() => {
    // Sync filters to URL
    const params = new URLSearchParams();
    if (filters.category) params.set('category', filters.category);
    if (filters.sort) params.set('sort', filters.sort);
    
    router.replace(`?${params.toString()}`);
  }, [filters, router]);
  
  useEffect(() => {
    // Sync URL to filters on mount
    const params = new URLSearchParams(window.location.search);
    setFilters({
      category: params.get('category') || '',
      sort: params.get('sort') || ''
    });
  }, []);
  
  // ...
}
```

```jsx
// ✅ AFTER: Event-driven URL updates
import { useSearchParams } from 'next/navigation';

function FilterableList() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const category = searchParams.get('category') || '';
  const sort = searchParams.get('sort') || '';
  
  const updateFilter = (key, value) => {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.replace(`?${params.toString()}`);
  };
  
  return (
    <div>
      <select 
        value={category}
        onChange={(e) => updateFilter('category', e.target.value)}
      >
        <option value="">All Categories</option>
        <option value="electronics">Electronics</option>
      </select>
      
      <ProductList category={category} sort={sort} />
    </div>
  );
}
```

---

## 7. Derived State Patterns

### Computed Values Without Effects

```jsx
// ❌ BEFORE: Redundant state with useEffect
function Cart({ items }) {
  const [total, setTotal] = useState(0);
  const [itemCount, setItemCount] = useState(0);
  const [isFreeShipping, setIsFreeShipping] = useState(false);
  
  useEffect(() => {
    const sum = items.reduce((acc, item) => 
      acc + item.price * item.quantity, 0
    );
    setTotal(sum);
    
    const count = items.reduce((acc, item) => 
      acc + item.quantity, 0
    );
    setItemCount(count);
    
    setIsFreeShipping(sum > 50);
  }, [items]);
  
  return (
    <div>
      <p>Items: {itemCount}</p>
      <p>Total: ${total.toFixed(2)}</p>
      {isFreeShipping && <p>Free Shipping!</p>}
    </div>
  );
}
```

```jsx
// ✅ AFTER: Compute during render
function Cart({ items }) {
  // Compute directly - React will re-run when items change
  const total = items.reduce(
    (acc, item) => acc + item.price * item.quantity, 
    0
  );
  
  const itemCount = items.reduce(
    (acc, item) => acc + item.quantity, 
    0
  );
  
  const isFreeShipping = total > 50;
  
  return (
    <div>
      <p>Items: {itemCount}</p>
      <p>Total: ${total.toFixed(2)}</p>
      {isFreeShipping && <p>Free Shipping!</p>}
    </div>
  );
}

// ✅ BETTER: Extract to custom hook for reusability
function useCartSummary(items) {
  return useMemo(() => {
    const total = items.reduce(
      (acc, item) => acc + item.price * item.quantity, 
      0
    );
    const itemCount = items.reduce(
      (acc, item) => acc + item.quantity, 
      0
    );
    
    return {
      total,
      itemCount,
      isFreeShipping: total > 50,
      formattedTotal: `$${total.toFixed(2)}`
    };
  }, [items]);
}

function Cart({ items }) {
  const { total, itemCount, isFreeShipping, formattedTotal } = 
    useCartSummary(items);
  
  return (
    <div>
      <p>Items: {itemCount}</p>
      <p>Total: {formattedTotal}</p>
      {isFreeShipping && <p>Free Shipping!</p>}
    </div>
  );
}
```

### Filtering and Sorting

```jsx
// ❌ BEFORE: useEffect for filtering
function ProductList({ products, searchTerm, sortBy }) {
  const [filtered, setFiltered] = useState(products);
  
  useEffect(() => {
    let result = [...products];
    
    if (searchTerm) {
      result = result.filter(p => 
        p.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    if (sortBy === 'price') {
      result.sort((a, b) => a.price - b.price);
    } else if (sortBy === 'name') {
      result.sort((a, b) => a.name.localeCompare(b.name));
    }
    
    setFiltered(result);
  }, [products, searchTerm, sortBy]);
  
  return (
    <ul>
      {filtered.map(p => <ProductCard key={p.id} {...p} />)}
    </ul>
  );
}
```

```jsx
// ✅ AFTER: Derive during render
function ProductList({ products, searchTerm, sortBy }) {
  const filtered = useMemo(() => {
    let result = products;
    
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(p => 
        p.name.toLowerCase().includes(term)
      );
    }
    
    if (sortBy === 'price') {
      result = [...result].sort((a, b) => a.price - b.price);
    } else if (sortBy === 'name') {
      result = [...result].sort((a, b) => a.name.localeCompare(b.name));
    }
    
    return result;
  }, [products, searchTerm, sortBy]);
  
  return (
    <ul>
      {filtered.map(p => <ProductCard key={p.id} {...p} />)}
    </ul>
  );
}

// ✅ EVEN BETTER: Separate pure functions
type Product = { id: number; name: string; price: number };
type SortOption = 'price' | 'name' | null;

function filterProducts(products: Product[], searchTerm: string): Product[] {
  if (!searchTerm) return products;
  const term = searchTerm.toLowerCase();
  return products.filter(p => p.name.toLowerCase().includes(term));
}

function sortProducts(products: Product[], sortBy: SortOption): Product[] {
  if (!sortBy) return products;
  
  const sorted = [...products];
  if (sortBy === 'price') {
    sorted.sort((a, b) => a.price - b.price);
  } else if (sortBy === 'name') {
    sorted.sort((a, b) => a.name.localeCompare(b.name));
  }
  return sorted;
}

function useProductFilter(products, searchTerm, sortBy) {
  return useMemo(() => {
    const filtered = filterProducts(products, searchTerm);
    return sortProducts(filtered, sortBy);
  }, [products, searchTerm, sortBy]);
}
```

### State Normalization

```jsx
// ❌ BEFORE: Derived state with useEffect
function MessageList({ messages }) {
  const [groupedMessages, setGroupedMessages] = useState({});
  
  useEffect(() => {
    const grouped = messages.reduce((acc, msg) => {
      const date = formatDate(msg.timestamp);
      if (!acc[date]) acc[date] = [];
      acc[date].push(msg);
      return acc;
    }, {});
    
    setGroupedMessages(grouped);
  }, [messages]);
  
  return (
    <div>
      {Object.entries(groupedMessages).map(([date, msgs]) => (
        <MessageGroup key={date} date={date} messages={msgs} />
      ))}
    </div>
  );
}
```

```jsx
// ✅ AFTER: Compute with useMemo
function MessageList({ messages }) {
  const groupedMessages = useMemo(() => {
    return messages.reduce((acc, msg) => {
      const date = formatDate(msg.timestamp);
      if (!acc[date]) acc[date] = [];
      acc[date].push(msg);
      return acc;
    }, {});
  }, [messages]);
  
  return (
    <div>
      {Object.entries(groupedMessages).map(([date, msgs]) => (
        <MessageGroup key={date} date={date} messages={msgs} />
      ))}
    </div>
  );
}
```

---

## 8. useSyncExternalStore for External Data

### Browser APIs

```jsx
// ❌ BEFORE: Manual subscription with useEffect
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
```

```jsx
// ✅ AFTER: useSyncExternalStore
import { useSyncExternalStore } from 'react';

function subscribe(callback) {
  window.addEventListener('online', callback);
  window.addEventListener('offline', callback);
  
  return () => {
    window.removeEventListener('online', callback);
    window.removeEventListener('offline', callback);
  };
}

function getSnapshot() {
  return navigator.onLine;
}

function getServerSnapshot() {
  return true; // Default for SSR
}

function useOnlineStatus() {
  return useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot
  );
}

function OnlineStatus() {
  const isOnline = useOnlineStatus();
  return <div>{isOnline ? 'Online' : 'Offline'}</div>;
}
```

### Local Storage

```jsx
// ❌ BEFORE: useEffect for localStorage sync
function useLocalStorage(key, initialValue) {
  const [value, setValue] = useState(initialValue);
  
  useEffect(() => {
    const stored = localStorage.getItem(key);
    if (stored) {
      setValue(JSON.parse(stored));
    }
  }, [key]);
  
  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);
  
  useEffect(() => {
    const handleStorage = (e) => {
      if (e.key === key) {
        setValue(JSON.parse(e.newValue));
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [key]);
  
  return [value, setValue];
}
```

```jsx
// ✅ AFTER: useSyncExternalStore with localStorage
function subscribe(key, callback) {
  const handler = (e) => {
    if (e.key === key) callback();
  };
  window.addEventListener('storage', handler);
  return () => window.removeEventListener('storage', handler);
}

function getSnapshot(key) {
  const item = localStorage.getItem(key);
  return item ? JSON.parse(item) : null;
}

function useLocalStorage(key, initialValue) {
  const getServerSnapshot = () => initialValue;
  
  const value = useSyncExternalStore(
    (callback) => subscribe(key, callback),
    () => getSnapshot(key) ?? initialValue,
    getServerSnapshot
  );
  
  const setValue = useCallback((newValue) => {
    const valueToStore = newValue instanceof Function 
      ? newValue(value) 
      : newValue;
    localStorage.setItem(key, JSON.stringify(valueToStore));
    // Dispatch storage event for same-tab updates
    window.dispatchEvent(new StorageEvent('storage', {
      key,
      newValue: JSON.stringify(valueToStore)
    }));
  }, [key, value]);
  
  return [value, setValue];
}

// Usage
function ThemeToggle() {
  const [theme, setTheme] = useLocalStorage('theme', 'light');
  
  return (
    <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
      {theme}
    </button>
  );
}
```

### Custom External Store

```jsx
// ✅ Store implementation
class Store {
  constructor(initialState) {
    this.state = initialState;
    this.listeners = new Set();
  }
  
  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
  
  getState() {
    return this.state;
  }
  
  setState(updater) {
    this.state = updater instanceof Function 
      ? updater(this.state) 
      : { ...this.state, ...updater };
    this.listeners.forEach(l => l());
  }
}

const globalStore = new Store({ count: 0, user: null });

// ✅ React hook using useSyncExternalStore
function useStore(store, selector = (state) => state) {
  return useSyncExternalStore(
    (callback) => store.subscribe(callback),
    () => selector(store.getState()),
    () => selector(store.getState())
  );
}

// ✅ Usage in components
function Counter() {
  const count = useStore(globalStore, (state) => state.count);
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => 
        globalStore.setState((s) => ({ count: s.count + 1 }))
      }>
        Increment
      </button>
    </div>
  );
}

function UserProfile() {
  const user = useStore(globalStore, (state) => state.user);
  
  if (!user) return <LoginPrompt />;
  
  return <div>Welcome, {user.name}</div>;
}
```

---

## 9. Refs for Imperative Operations

### Focus Management

```jsx
// ❌ BEFORE: useEffect for focus
function SearchInput({ autoFocus }) {
  const inputRef = useRef(null);
  
  useEffect(() => {
    if (autoFocus) {
      inputRef.current?.focus();
    }
  }, [autoFocus]);
  
  return <input ref={inputRef} type="search" />;
}
```

```jsx
// ✅ AFTER: Use callback ref for conditional focus
function SearchInput({ autoFocus }) {
  const inputRef = useRef(null);
  
  const setRef = useCallback((element) => {
    inputRef.current = element;
    if (element && autoFocus) {
      element.focus();
    }
  }, [autoFocus]);
  
  return <input ref={setRef} type="search" />;
}
```

### Scroll Position

```jsx
// ❌ BEFORE: useEffect for scroll restoration
function ChatContainer({ messages }) {
  const containerRef = useRef(null);
  const [shouldScrollToBottom, setShouldScrollToBottom] = useState(true);
  
  useEffect(() => {
    if (shouldScrollToBottom && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages, shouldScrollToBottom]);
  
  const handleScroll = () => {
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setShouldScrollToBottom(isAtBottom);
  };
  
  return (
    <div ref={containerRef} onScroll={handleScroll}>
      {messages.map(m => <Message key={m.id} {...m} />)}
    </div>
  );
}
```

```jsx
// ✅ AFTER: Direct ref manipulation in event handlers
function ChatContainer({ messages }) {
  const containerRef = useRef(null);
  const shouldScrollRef = useRef(true);
  
  // Store scroll decision in ref (doesn't trigger re-render)
  const handleScroll = () => {
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    shouldScrollRef.current = scrollHeight - scrollTop - clientHeight < 50;
  };
  
  // Use layout effect only for the actual DOM manipulation
  useLayoutEffect(() => {
    if (shouldScrollRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  });
  
  return (
    <div ref={containerRef} onScroll={handleScroll}>
      {messages.map(m => <Message key={m.id} {...m} />)}
    </div>
  );
}
```

### Animation Control

```jsx
// ❌ BEFORE: useEffect driving animations
function FadeIn({ children, delay = 0 }) {
  const [opacity, setOpacity] = useState(0);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setOpacity(1);
    }, delay);
    
    return () => clearTimeout(timer);
  }, [delay]);
  
  return (
    <div style={{ 
      opacity, 
      transition: 'opacity 300ms ease' 
    }}>
      {children}
    </div>
  );
}
```

```jsx
// ✅ AFTER: CSS animations, no JavaScript needed
function FadeIn({ children, delay = 0 }) {
  return (
    <div 
      className="fade-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

// CSS:
// @keyframes fadeIn {
//   from { opacity: 0; }
//   to { opacity: 1; }
// }
// .fade-in {
//   animation: fadeIn 300ms ease forwards;
//   opacity: 0;
// }
```

### Third-Party Library Integration

```jsx
// ❌ BEFORE: useEffect for chart initialization
function Chart({ data }) {
  const containerRef = useRef(null);
  const [chart, setChart] = useState(null);
  
  useEffect(() => {
    if (!containerRef.current) return;
    
    const c = new ChartLibrary(containerRef.current, {
      type: 'line',
      data: { datasets: [{ data }] }
    });
    
    setChart(c);
    
    return () => c.destroy();
  }, []);
  
  useEffect(() => {
    if (chart) {
      chart.data.datasets[0].data = data;
      chart.update();
    }
  }, [data, chart]);
  
  return <div ref={containerRef} />;
}
```

```jsx
// ✅ AFTER: Ref-based approach with proper cleanup
function Chart({ data }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  
  useEffect(() => {
    if (!containerRef.current) return;
    
    // Initialize once
    chartRef.current = new ChartLibrary(containerRef.current, {
      type: 'line',
      data: { datasets: [{ data }] }
    });
    
    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, []); // Empty deps - initialize once
  
  // Update data via ref (no state needed)
  if (chartRef.current) {
    chartRef.current.data.datasets[0].data = data;
    chartRef.current.update('none'); // 'none' for performance
  }
  
  return <div ref={containerRef} />;
}

// ✅ EVEN BETTER: Extract to reusable hook
function useChart(containerRef, config) {
  const chartRef = useRef(null);
  
  useEffect(() => {
    if (!containerRef.current) return;
    
    chartRef.current = new ChartLibrary(containerRef.current, config);
    
    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, []);
  
  return chartRef;
}
```

---

## 10. Component Composition Over Effects

### Conditional Rendering Without State

```jsx
// ❌ BEFORE: useEffect for conditional visibility
function Tabs({ tabs }) {
  const [activeTab, setActiveTab] = useState(0);
  const [visibleContent, setVisibleContent] = useState(null);
  
  useEffect(() => {
    setVisibleContent(tabs[activeTab].content);
  }, [activeTab, tabs]);
  
  return (
    <div>
      <div className="tab-list">
        {tabs.map((tab, i) => (
          <button 
            key={tab.id}
            onClick={() => setActiveTab(i)}
            className={i === activeTab ? 'active' : ''}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="tab-content">{visibleContent}</div>
    </div>
  );
}
```

```jsx
// ✅ AFTER: Direct rendering based on state
function Tabs({ tabs }) {
  const [activeTab, setActiveTab] = useState(0);
  
  const ActiveComponent = tabs[activeTab].component;
  
  return (
    <div>
      <div className="tab-list">
        {tabs.map((tab, i) => (
          <button 
            key={tab.id}
            onClick={() => setActiveTab(i)}
            className={i === activeTab ? 'active' : ''}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="tab-content">
        <ActiveComponent />
      </div>
    </div>
  );
}

// Usage
<Tabs tabs={[
  { id: 'general', label: 'General', component: GeneralSettings },
  { id: 'security', label: 'Security', component: SecuritySettings },
]} />
```

### Modal/Dialog State

```jsx
// ❌ BEFORE: useEffect for modal body scroll lock
function Modal({ isOpen, onClose, children }) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);
  
  if (!isOpen) return null;
  
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  );
}
```

```jsx
// ✅ AFTER: Portal with CSS-based scroll lock
import { createPortal } from 'react-dom';

// CSS-only solution for scroll lock
// body:has(.modal-open) { overflow: hidden; }

function Modal({ isOpen, onClose, children }) {
  if (!isOpen) return null;
  
  return createPortal(
    <div className="modal-overlay modal-open" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>,
    document.body
  );
}
```

### Lazy Loading with Suspense

```jsx
// ❌ BEFORE: Manual lazy loading with useEffect
function LazyImage({ src, alt }) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [shouldLoad, setShouldLoad] = useState(false);
  const imgRef = useRef(null);
  
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShouldLoad(true);
          observer.disconnect();
        }
      },
      { rootMargin: '100px' }
    );
    
    if (imgRef.current) {
      observer.observe(imgRef.current);
    }
    
    return () => observer.disconnect();
  }, []);
  
  useEffect(() => {
    if (!shouldLoad) return;
    
    const img = new Image();
    img.src = src;
    img.onload = () => setIsLoaded(true);
  }, [shouldLoad, src]);
  
  return (
    <div ref={imgRef} className="image-container">
      {isLoaded ? (
        <img src={src} alt={alt} />
      ) : (
        <div className="placeholder" />
      )}
    </div>
  );
}
```

```jsx
// ✅ AFTER: Native loading="lazy" or library
function LazyImage({ src, alt }) {
  return (
    <img 
      src={src} 
      alt={alt} 
      loading="lazy"
      decoding="async"
    />
  );
}

// ✅ Or use a dedicated library
import { LazyLoadImage } from 'react-lazy-load-image-component';

function ProductImage({ src, alt }) {
  return (
    <LazyLoadImage
      src={src}
      alt={alt}
      effect="blur"
      threshold={100}
    />
  );
}
```

### State Lifting and Props Drilling Solution

```jsx
// ❌ BEFORE: Syncing sibling components with useEffect
function Parent() {
  const [count, setCount] = useState(0);
  const [siblingCount, setSiblingCount] = useState(0);
  
  // Trying to sync siblings - code smell!
  useEffect(() => {
    setSiblingCount(count * 2);
  }, [count]);
  
  return (
    <div>
      <Counter count={count} setCount={setCount} />
      <Display count={siblingCount} />
    </div>
  );
}
```

```jsx
// ✅ AFTER: Lift derived value, not state
function Parent() {
  const [count, setCount] = useState(0);
  const doubled = count * 2; // Derive, don't sync
  
  return (
    <div>
      <Counter count={count} setCount={setCount} />
      <Display count={doubled} />
    </div>
  );
}

// ✅ Or use composition pattern
function CounterProvider({ children }) {
  const [count, setCount] = useState(0);
  
  return (
    <CounterContext.Provider value={{ count, setCount }}>
      {children}
    </CounterContext.Provider>
  );
}

function CounterDisplay() {
  const { count } = useContext(CounterContext);
  return <div>Count: {count}</div>;
}

function CounterButton() {
  const { setCount } = useContext(CounterContext);
  return <button onClick={() => setCount(c => c + 1)}>+</button>;
}
```

### Render Props Pattern

```jsx
// ✅ BEFORE: Effect-driven data flow
function DataFetcher({ url, render }) {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    fetch(url).then(r => r.json()).then(setData);
  }, [url]);
  
  return render(data);
}
```

```jsx
// ✅ AFTER: Modern composition with children as function
import { useSuspenseQuery } from '@tanstack/react-query';

function DataProvider({ queryKey, queryFn, children }) {
  const { data } = useSuspenseQuery({ queryKey, queryFn });
  return children(data);
}

// Usage
function UserProfile({ userId }) {
  return (
    <DataProvider
      queryKey={['user', userId]}
      queryFn={() => fetchUser(userId)}
    >
      {(user) => (
        <div>
          <h1>{user.name}</h1>
          <p>{user.email}</p>
        </div>
      )}
    </DataProvider>
  );
}
```

### Compound Components

```jsx
// ✅ AFTER: Compound component pattern
const SelectContext = createContext(null);

function Select({ children, value, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <SelectContext.Provider value={{ value, onChange, isOpen, setIsOpen }}>
      <div className="select">{children}</div>
    </SelectContext.Provider>
  );
}

function SelectTrigger({ children }) {
  const { isOpen, setIsOpen, value } = useContext(SelectContext);
  
  return (
    <button onClick={() => setIsOpen(!isOpen)}>
      {children || value}
    </button>
  );
}

function SelectContent({ children }) {
  const { isOpen } = useContext(SelectContext);
  
  if (!isOpen) return null;
  
  return <div className="select-content">{children}</div>;
}

function SelectItem({ value, children }) {
  const { value: selectedValue, onChange, setIsOpen } = useContext(SelectContext);
  
  return (
    <div 
      className={value === selectedValue ? 'selected' : ''}
      onClick={() => {
        onChange(value);
        setIsOpen(false);
      }}
    >
      {children}
    </div>
  );
}

Select.Trigger = SelectTrigger;
Select.Content = SelectContent;
Select.Item = SelectItem;

// Usage
function App() {
  const [value, setValue] = useState('');
  
  return (
    <Select value={value} onChange={setValue}>
      <Select.Trigger>Select an option</Select.Trigger>
      <Select.Content>
        <Select.Item value="a">Option A</Select.Item>
        <Select.Item value="b">Option B</Select.Item>
      </Select.Content>
    </Select>
  );
}
```

---

## Quick Reference: When to Use What

| Scenario | Solution | Avoid |
|----------|----------|-------|
| Data Fetching | TanStack Query, Server Components, use() hook | useEffect + fetch |
| Derived State | Compute during render, useMemo | useEffect + setState |
| External Store | useSyncExternalStore | useEffect + manual sync |
| DOM Measurements | useLayoutEffect (sparingly) | useEffect |
| Browser APIs | useSyncExternalStore | useEffect + manual events |
| Animations | CSS, requestAnimationFrame | useEffect + state |
| Form Submission | Event handlers | useEffect + flags |
| Focus/Scroll | Refs + event handlers | useEffect |
| Subscriptions | useSyncExternalStore | useEffect |
| State Syncing | Lift state up | useEffect + setState |

---

## Summary

### Key Takeaways

1. **Prefer Server Components** - Fetch data on the server when possible
2. **Use TanStack Query** - For client-side data fetching
3. **Derive, don't sync** - Compute values during render instead of syncing state
4. **Event handlers over effects** - Handle user interactions directly
5. **useSyncExternalStore** - For external state synchronization
6. **React 19 use()** - For declarative async data in components
7. **Refs for imperative ops** - DOM manipulation without re-renders
8. **Composition patterns** - Lift state, use context, compound components

### Migration Strategy

1. Audit your useEffect usage - categorize by purpose
2. Start with data fetching - migrate to TanStack Query or Server Components
3. Identify derived state - remove redundant setState calls
4. Replace manual subscriptions - use useSyncExternalStore
5. Review effects on user events - move to event handlers
6. Test thoroughly - ensure no regressions in behavior

Remember: Not all useEffect usage is bad! Use it for:
- Synchronizing with external systems
- Managing non-React subscriptions
- One-time initializations that don't affect render

But for most common patterns, there are better alternatives available in modern React.
