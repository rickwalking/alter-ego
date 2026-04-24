# React Components Best Practices Guide 2026

A comprehensive guide to creating modern React components with the latest patterns, techniques, and standards.

---

## Table of Contents

1. [Component Composition Patterns](#1-component-composition-patterns)
2. [Compound Components vs Regular Components](#2-compound-components-vs-regular-components)
3. [Controlled vs Uncontrolled Components](#3-controlled-vs-uncontrolled-components)
4. [Props Design and Interface Definition](#4-props-design-and-interface-definition)
5. [Server Components vs Client Components](#5-server-components-vs-client-components)
6. [Component Folder Structure and Organization](#6-component-folder-structure-and-organization)
7. [Naming Conventions](#7-naming-conventions)
8. [Accessibility (a11y) Best Practices](#8-accessibility-a11y-best-practices)
9. [Documentation Patterns](#9-documentation-patterns)
10. [Ref Forwarding and Component Polymorphism](#10-ref-forwarding-and-component-polymorphism)

---

## 1. Component Composition Patterns

Composition is the foundation of React. It enables building complex UIs from simple, reusable pieces.

### 1.1 The Children Prop Pattern

The most basic composition pattern uses the `children` prop to create wrapper components:

```tsx
// Card.tsx
interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <div className={`rounded-lg border bg-white p-4 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

// Usage
<Card>
  <h2>Title</h2>
  <p>Content goes here</p>
</Card>
```

### 1.2 Slots Pattern (Named Children)

For more complex layouts, use named slots instead of a single children prop:

```tsx
// Layout.tsx
interface LayoutProps {
  header: React.ReactNode;
  sidebar: React.ReactNode;
  main: React.ReactNode;
  footer?: React.ReactNode;
}

export function Layout({ header, sidebar, main, footer }: LayoutProps) {
  return (
    <div className="flex flex-col min-h-screen">
      <header className="h-16 border-b">{header}</header>
      <div className="flex flex-1">
        <aside className="w-64 border-r">{sidebar}</aside>
        <main className="flex-1 p-6">{main}</main>
      </div>
      {footer && <footer className="border-t">{footer}</footer>}
    </div>
  );
}

// Usage
<Layout
  header={<Navigation />}
  sidebar={<Menu />}
  main={<Content />}
  footer={<Footer />}
/>
```

### 1.3 Render Props Pattern

Use render props for components that need to share logic while giving consumers control over rendering:

```tsx
// DataFetcher.tsx
interface DataFetcherProps<T> {
  url: string;
  render: (data: T | null, isLoading: boolean, error: Error | null) => React.ReactNode;
}

export function DataFetcher<T>({ url, render }: DataFetcherProps<T>) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    fetch(url)
      .then(res => res.json())
      .then(setData)
      .catch(setError)
      .finally(() => setIsLoading(false));
  }, [url]);

  return <>{render(data, isLoading, error)}</>;
}

// Usage
<DataFetcher<User>
  url="/api/user"
  render={(user, isLoading, error) => {
    if (isLoading) return <Spinner />;
    if (error) return <Error message={error.message} />;
    return <UserProfile user={user} />;
  }}
/>
```

### 1.4 Higher-Order Components (HOCs)

While less common now with hooks, HOCs are still useful for cross-cutting concerns:

```tsx
// withAuth.tsx
function withAuth<P extends object>(
  WrappedComponent: ComponentType<P>
): ComponentType<P> {
  return function WithAuthComponent(props: P) {
    const { user, isLoading } = useAuth();

    if (isLoading) return <LoadingScreen />;
    if (!user) return <LoginRedirect />;

    return <WrappedComponent {...props} user={user} />;
  };
}

// Usage
const ProtectedDashboard = withAuth(Dashboard);
```

### 1.5 Container/Presentational Pattern

Separate data fetching (containers) from UI rendering (presentational):

```tsx
// UserListContainer.tsx - Handles data
export function UserListContainer() {
  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: fetchUsers
  });

  if (isLoading) return <UserListSkeleton />;

  return <UserList users={users} />;
}

// UserList.tsx - Pure UI
interface UserListProps {
  users: User[];
}

export function UserList({ users }: UserListProps) {
  return (
    <ul className="space-y-2">
      {users.map(user => (
        <UserListItem key={user.id} user={user} />
      ))}
    </ul>
  );
}
```

---

## 2. Compound Components vs Regular Components

### 2.1 What Are Compound Components?

Compound components are components that work together to form a complete UI. They share implicit state and communicate through a parent component. Think of `<select>` and `<option>` in HTML.

### 2.2 Creating Compound Components with Context

```tsx
// Tabs.tsx
import { createContext, useContext, useState, useMemo } from 'react';

interface TabsContextValue {
  activeTab: string;
  setActiveTab: (id: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabs() {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error('Tabs subcomponents must be used within <Tabs>');
  }
  return context;
}

// Root Component
interface TabsProps {
  children: React.ReactNode;
  defaultTab?: string;
}

export function Tabs({ children, defaultTab }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || '');

  const value = useMemo(() => ({ activeTab, setActiveTab }), [activeTab]);

  return (
    <TabsContext.Provider value={value}>
      <div className="tabs">{children}</div>
    </TabsContext.Provider>
  );
}

// Tab List
interface TabListProps {
  children: React.ReactNode;
}

export function TabList({ children }: TabListProps) {
  return <div className="flex border-b" role="tablist">{children}</div>;
}

// Individual Tab
interface TabProps {
  id: string;
  children: React.ReactNode;
  disabled?: boolean;
}

export function Tab({ id, children, disabled }: TabProps) {
  const { activeTab, setActiveTab } = useTabs();
  const isActive = activeTab === id;

  return (
    <button
      role="tab"
      aria-selected={isActive}
      disabled={disabled}
      onClick={() => setActiveTab(id)}
      className={`px-4 py-2 ${isActive ? 'border-b-2 border-blue-500' : ''}`}
    >
      {children}
    </button>
  );
}

// Tab Panel
interface TabPanelProps {
  id: string;
  children: React.ReactNode;
}

export function TabPanel({ id, children }: TabPanelProps) {
  const { activeTab } = useTabs();

  if (activeTab !== id) return null;

  return (
    <div role="tabpanel" className="p-4">
      {children}
    </div>
  );
}
```

### 2.3 Usage Example

```tsx
<Tabs defaultTab="overview">
  <TabList>
    <Tab id="overview">Overview</Tab>
    <Tab id="details">Details</Tab>
    <Tab id="settings">Settings</Tab>
  </TabList>

  <TabPanel id="overview">
    <h2>Overview Content</h2>
  </TabPanel>

  <TabPanel id="details">
    <h2>Details Content</h2>
  </TabPanel>

  <TabPanel id="settings">
    <h2>Settings Content</h2>
  </TabPanel>
</Tabs>
```

### 2.4 When to Use Compound Components vs Regular Components

| Use Compound Components When | Use Regular Components When |
|------------------------------|----------------------------|
| Components naturally work together | Components are independent |
| Need to share implicit state | State can be passed via props |
| Want flexible composition | Simple, single-purpose component |
| Building complex UI patterns (tabs, menus, etc.) | Building simple UI elements |

---

## 3. Controlled vs Uncontrolled Components

### 3.1 Uncontrolled Components

Uncontrolled components manage their own state internally:

```tsx
// UncontrolledInput.tsx
import { useRef } from 'react';

interface UncontrolledInputProps {
  defaultValue?: string;
  onSubmit?: (value: string) => void;
}

export function UncontrolledInput({ defaultValue, onSubmit }: UncontrolledInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    if (inputRef.current && onSubmit) {
      onSubmit(inputRef.current.value);
    }
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="text"
        defaultValue={defaultValue}
        className="border rounded px-3 py-2"
      />
      <button onClick={handleSubmit}>Submit</button>
    </div>
  );
}
```

### 3.2 Controlled Components

Controlled components receive their state and change handlers from parent:

```tsx
// ControlledInput.tsx
interface ControlledInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function ControlledInput({ value, onChange, placeholder }: ControlledInputProps) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="border rounded px-3 py-2"
    />
  );
}

// Usage
function Form() {
  const [name, setName] = useState('');

  return <ControlledInput value={name} onChange={setName} />;
}
```

### 3.3 Hybrid Approach with useControllableState

Create components that work both ways:

```tsx
// useControllableState.ts
import { useState, useCallback } from 'react';

interface UseControllableStateProps<T> {
  value?: T;
  defaultValue?: T;
  onChange?: (value: T) => void;
}

export function useControllableState<T>({
  value,
  defaultValue,
  onChange
}: UseControllableStateProps<T>): [T, (value: T) => void] {
  const [internalValue, setInternalValue] = useState(defaultValue as T);

  const isControlled = value !== undefined;
  const currentValue = isControlled ? value : internalValue;

  const setValue = useCallback((newValue: T) => {
    if (!isControlled) {
      setInternalValue(newValue);
    }
    onChange?.(newValue);
  }, [isControlled, onChange]);

  return [currentValue, setValue];
}
```

```tsx
// Toggle.tsx
interface ToggleProps {
  checked?: boolean;
  defaultChecked?: boolean;
  onChange?: (checked: boolean) => void;
}

export function Toggle({ checked, defaultChecked, onChange }: ToggleProps) {
  const [isOn, setIsOn] = useControllableState({
    value: checked,
    defaultValue: defaultChecked ?? false,
    onChange
  });

  return (
    <button
      role="switch"
      aria-checked={isOn}
      onClick={() => setIsOn(!isOn)}
      className={`w-12 h-6 rounded-full transition-colors ${
        isOn ? 'bg-blue-500' : 'bg-gray-300'
      }`}
    >
      <span className={`block w-5 h-5 bg-white rounded-full transition-transform ${
        isOn ? 'translate-x-6' : 'translate-x-1'
      }`} />
    </button>
  );
}
```

### 3.4 Decision Matrix

| Use Uncontrolled When | Use Controlled When |
|----------------------|---------------------|
| Simple forms | Complex form validation |
| File inputs | Need to programmatically change values |
| Integrating non-React code | Multiple inputs need to stay in sync |
| Don't need real-time access to value | Need to conditionally disable submit |
| Performance is critical (large lists) | Need to transform input on change |

---

## 4. Props Design and Interface Definition

### 4.1 TypeScript Interface Best Practices

```tsx
// Button.types.ts
import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style variant */
  variant?: ButtonVariant;
  /** Size of the button */
  size?: ButtonSize;
  /** Show loading spinner */
  isLoading?: boolean;
  /** Icon to display before text */
  leftIcon?: ReactNode;
  /** Icon to display after text */
  rightIcon?: ReactNode;
  /** Full width button */
  isFullWidth?: boolean;
}
```

### 4.2 Component Implementation

```tsx
// Button.tsx
import { forwardRef } from 'react';
import type { ButtonProps } from './Button.types';

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      isFullWidth = false,
      disabled,
      className,
      ...props
    },
    ref
  ) => {
    const baseStyles = 'inline-flex items-center justify-center font-medium rounded transition-colors';

    const variantStyles = {
      primary: 'bg-blue-600 text-white hover:bg-blue-700',
      secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
      ghost: 'bg-transparent text-gray-700 hover:bg-gray-100',
      danger: 'bg-red-600 text-white hover:bg-red-700'
    };

    const sizeStyles = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-6 py-3 text-lg'
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`
          ${baseStyles}
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${isFullWidth ? 'w-full' : ''}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          ${className || ''}
        `}
        {...props}
      >
        {isLoading && <Spinner className="mr-2" />}
        {!isLoading && leftIcon && <span className="mr-2">{leftIcon}</span>}
        {children}
        {!isLoading && rightIcon && <span className="ml-2">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
```

### 4.3 Props Spreading and Destructuring

```tsx
// Good: Explicit props with spread for HTML attributes
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function Input({ label, error, className, ...inputProps }: InputProps) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium">{label}</label>
      <input
        className={`border rounded px-3 py-2 ${error ? 'border-red-500' : ''} ${className}`}
        {...inputProps}
      />
      {error && <p className="text-red-500 text-sm">{error}</p>}
    </div>
  );
}
```

### 4.4 Discriminated Unions for Complex Props

```tsx
// Alert.tsx
type AlertVariant = 'info' | 'success' | 'warning' | 'error';

interface BaseAlertProps {
  title?: string;
  children: ReactNode;
}

type DismissibleAlertProps = BaseAlertProps & {
  isDismissible: true;
  onDismiss: () => void;
};

type NonDismissibleAlertProps = BaseAlertProps & {
  isDismissible?: false;
  onDismiss?: never;
};

export type AlertProps = DismissibleAlertProps | NonDismissibleAlertProps;

export function Alert(props: AlertProps) {
  const { title, children, isDismissible } = props;

  return (
    <div className="alert">
      {title && <h4>{title}</h4>}
      <div>{children}</div>
      {isDismissible && (
        <button onClick={props.onDismiss}>Dismiss</button>
      )}
    </div>
  );
}
```

### 4.5 Default Props Pattern

```tsx
// With destructuring defaults (Recommended for 2026)
interface BadgeProps {
  count?: number;
  max?: number;
  variant?: 'default' | 'dot';
}

export function Badge({
  count = 0,
  max = 99,
  variant = 'default'
}: BadgeProps) {
  const displayCount = count > max ? `${max}+` : count;

  return (
    <span className="badge">
      {variant === 'dot' ? <span className="dot" /> : displayCount}
    </span>
  );
}
```

---

## 5. Server Components vs Client Components

### 5.1 When to Use Each

**Server Components (Default in Next.js App Router):**
- Fetching data from databases or APIs
- Accessing backend resources directly
- Keeping sensitive information on the server
- Reducing client-side JavaScript bundle size

**Client Components ("use client"):**
- Using browser APIs (localStorage, navigator, window)
- Handling user interactions (onClick, onChange, onSubmit)
- Using React hooks (useState, useEffect, useContext)
- Using lifecycle methods

### 5.2 Server Component Example

```tsx
// UserProfile.server.tsx (or just .tsx in Next.js App Router)
import { db } from '@/lib/db';

// This runs only on the server!
export default async function UserProfile({ userId }: { userId: string }) {
  // Direct database access - no API layer needed
  const user = await db.users.findUnique({
    where: { id: userId }
  });

  if (!user) return <div>User not found</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">{user.name}</h1>
      <p className="text-gray-600">{user.email}</p>
      {/* Server Components can render Client Components */}
      <FollowButton userId={user.id} initialIsFollowing={user.isFollowing} />
    </div>
  );
}
```

### 5.3 Client Component Example

```tsx
// FollowButton.client.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface FollowButtonProps {
  userId: string;
  initialIsFollowing: boolean;
}

export function FollowButton({ userId, initialIsFollowing }: FollowButtonProps) {
  const [isFollowing, setIsFollowing] = useState(initialIsFollowing);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleClick = async () => {
    setIsLoading(true);
    try {
      await fetch(`/api/users/${userId}/follow`, {
        method: isFollowing ? 'DELETE' : 'POST'
      });
      setIsFollowing(!isFollowing);
      router.refresh(); // Refresh server components
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={isLoading}
      className={`px-4 py-2 rounded ${
        isFollowing
          ? 'bg-gray-200 text-gray-800'
          : 'bg-blue-600 text-white'
      }`}
    >
      {isLoading ? 'Loading...' : isFollowing ? 'Unfollow' : 'Follow'}
    </button>
  );
}
```

### 5.4 Composition Pattern

The recommended pattern is to keep Client Components as small as possible and compose them within Server Components:

```tsx
// Page.tsx (Server Component)
import { db } from '@/lib/db';
import { UserCard } from './UserCard';
import { LikeButton } from './LikeButton';

export default async function Page() {
  const users = await db.users.findMany();

  return (
    <div className="grid gap-4">
      {users.map(user => (
        <UserCard key={user.id} user={user}>
          {/* Pass Server Component output as children to Client Component */}
          <LikeButton postId={user.id} initialLikes={user.likes} />
        </UserCard>
      ))}
    </div>
  );
}
```

```tsx
// LikeButton.tsx (Client Component)
'use client';

import { useState } from 'react';

interface LikeButtonProps {
  postId: string;
  initialLikes: number;
  children?: React.ReactNode;
}

export function LikeButton({ postId, initialLikes, children }: LikeButtonProps) {
  const [likes, setLikes] = useState(initialLikes);

  const handleLike = async () => {
    await fetch(`/api/posts/${postId}/like`, { method: 'POST' });
    setLikes(prev => prev + 1);
  };

  return (
    <div>
      <button onClick={handleLike}>❤️ {likes}</button>
      {children}
    </div>
  );
}
```

---

## 6. Component Folder Structure and Organization

### 6.1 Recommended Project Structure (2026)

```
app/
├── components/
│   ├── ui/                    # Generic reusable UI components
│   │   ├── button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.types.ts
│   │   │   ├── Button.test.tsx
│   │   │   └── index.ts
│   │   ├── input/
│   │   ├── select/
│   │   └── index.ts           # Re-exports all UI components
│   ├── forms/                 # Form-specific components
│   │   ├── FormField/
│   │   ├── FormError/
│   │   └── index.ts
│   ├── layout/                # Layout components
│   │   ├── Header/
│   │   ├── Sidebar/
│   │   └── index.ts
│   └── providers/             # Context providers
│       ├── ThemeProvider/
│       └── index.ts
├── features/                  # Feature-based components
│   ├── auth/
│   │   ├── components/
│   │   │   ├── LoginForm/
│   │   │   └── SignupForm/
│   │   ├── hooks/
│   │   │   └── useAuth.ts
│   │   ├── types/
│   │   └── utils/
│   └── dashboard/
│       └── components/
├── hooks/                     # Global hooks
│   ├── useLocalStorage.ts
│   └── useMediaQuery.ts
├── lib/                       # Utilities and configurations
│   ├── utils/
│   ├── db.ts
│   └── api.ts
└── types/                     # Global TypeScript types
    └── index.ts
```

### 6.2 Component File Structure (Co-location)

```
Button/
├── index.ts              # Public API: export { Button } from './Button'
├── Button.tsx            # Main component
├── Button.types.ts       # TypeScript interfaces/types
├── Button.test.tsx       # Unit tests
├── Button.stories.tsx    # Storybook stories
├── Button.module.css     # Scoped styles (or use Tailwind in component)
└── hooks/
│   └── useButtonState.ts # Component-specific hooks
```

### 6.3 Barrel Exports (index.ts)

```ts
// components/ui/button/index.ts
export { Button } from './Button';
export type { ButtonProps, ButtonVariant, ButtonSize } from './Button.types';

// components/ui/index.ts
export * from './button';
export * from './input';
export * from './select';
// ...

// Usage in other files
import { Button, Input } from '@/components/ui';
```

### 6.4 Feature-Based Organization

```
features/
├── auth/
│   ├── index.ts
│   ├── components/
│   │   ├── LoginForm/
│   │   └── SignupForm/
│   ├── hooks/
│   │   ├── useAuth.ts
││   │   └── useLogin.ts
│   ├── services/
│   │   └── authApi.ts
│   ├── types/
│   │   └── auth.types.ts
│   └── utils/
│       └── authUtils.ts
└── posts/
    ├── index.ts
    ├── components/
    │   ├── PostList/
    │   ├── PostCard/
    │   └── PostEditor/
    ├── hooks/
    │   └── usePosts.ts
    └── services/
        └── postsApi.ts
```

---

## 7. Naming Conventions

### 7.1 Component Names

```tsx
// ✅ Use PascalCase for component names
function UserProfile() { }
function NavBar() { }
function ButtonGroup() { }

// ❌ Don't use camelCase or snake_case
function userProfile() { }  // Wrong
function user_profile() { } // Wrong
```

### 7.2 File Names

```
// ✅ Component files match component name
UserProfile.tsx
NavBar.tsx
ButtonGroup.tsx

// ✅ For compound components, use directory
components/
└── Tabs/
    ├── index.ts
    ├── Tabs.tsx
    ├── Tabs.types.ts
    ├── TabList.tsx
    ├── Tab.tsx
    └── TabPanel.tsx
```

### 7.3 Props Naming

```tsx
// ✅ Use camelCase for props
interface Props {
  userName: string;
  isActive: boolean;
  onClick: () => void;
  onUserUpdate: (user: User) => void;
}

// ✅ Boolean props: use 'is', 'has', 'can', 'should' prefix
isLoading
hasError
canEdit
shouldShow

// ✅ Event handlers: use 'on' prefix + verb
onClick
onSubmit
onUserCreate
onInputChange

// ✅ Callback props passed to children: use 'render' prefix
renderItem
renderHeader
renderEmptyState
```

### 7.4 Hook Naming

```tsx
// ✅ Custom hooks start with 'use'
function useAuth() { }
function useLocalStorage<T>() { }
function useMediaQuery() { }

// ✅ Derived state hooks
function useFilteredUsers(users: User[], filter: string) { }
function useSortedData<T>(data: T[], sortKey: keyof T) { }
```

### 7.5 Type Naming

```ts
// ✅ Interfaces use PascalCase
interface UserProfileProps { }
interface ButtonConfig { }

// ✅ Type aliases for unions
type ButtonVariant = 'primary' | 'secondary';
type Status = 'idle' | 'loading' | 'success' | 'error';

// ✅ Generic type parameters
interface ContainerProps<T> {
  items: T[];
  renderItem: (item: T) => ReactNode;
}
```

### 7.6 Constants and Enums

```ts
// ✅ Constants use UPPER_SNAKE_CASE
const API_BASE_URL = 'https://api.example.com';
const MAX_RETRY_COUNT = 3;

// ✅ Enum names are PascalCase, members are PascalCase
enum ButtonVariant {
  Primary = 'primary',
  Secondary = 'secondary',
  Ghost = 'ghost'
}
```

---

## 8. Accessibility (a11y) Best Practices

### 8.1 Semantic HTML

```tsx
// ❌ Avoid div soup
<div className="button" onClick={handleClick}>Click me</div>

// ✅ Use semantic elements
<button onClick={handleClick}>Click me</button>

// ✅ Proper heading hierarchy
<article>
  <h2>Article Title</h2>
  <h3>Section 1</h3>
  <h3>Section 2</h3>
</article>
```

### 8.2 ARIA Attributes

```tsx
// ✅ Accessible Modal
function Modal({ isOpen, onClose, title, children }: ModalProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-hidden={!isOpen}
      className={isOpen ? 'block' : 'hidden'}
    >
      <h2 id="modal-title">{title}</h2>
      {children}
      <button onClick={onClose} aria-label="Close modal">×</button>
    </div>
  );
}

// ✅ Accessible Tabs
function Tabs({ children }) {
  return (
    <div role="tablist" aria-label="Sample Tabs">
      {children}
    </div>
  );
}

function Tab({ isActive, children }) {
  return (
    <button
      role="tab"
      aria-selected={isActive}
      tabIndex={isActive ? 0 : -1}
    >
      {children}
    </button>
  );
}
```

### 8.3 Keyboard Navigation

```tsx
// ✅ Keyboard accessible dropdown
function Dropdown({ items }) {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const handleKeyDown = (e: KeyboardEvent) => {
    switch (e.key) {
      case 'Escape':
        setIsOpen(false);
        buttonRef.current?.focus();
        break;
      case 'ArrowDown':
        e.preventDefault();
        setFocusedIndex(i => Math.min(i + 1, items.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setFocusedIndex(i => Math.max(i - 1, 0));
        break;
      case 'Enter':
      case ' ':
        if (focusedIndex >= 0) {
          handleSelect(items[focusedIndex]);
        }
        break;
    }
  };

  return (
    <div onKeyDown={handleKeyDown}>
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        Select an option
      </button>
      {isOpen && (
        <ul role="listbox" aria-label="Options">
          {items.map((item, index) => (
            <li
              key={item.id}
              role="option"
              aria-selected={index === focusedIndex}
              tabIndex={-1}
            >
              {item.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

### 8.4 Focus Management

```tsx
// ✅ Focus trap for modals
function useFocusTrap(isActive: boolean, containerRef: RefObject<HTMLElement>) {
  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    const container = containerRef.current;
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    };

    container.addEventListener('keydown', handleTabKey);
    firstElement?.focus();

    return () => container.removeEventListener('keydown', handleTabKey);
  }, [isActive, containerRef]);
}
```

### 8.5 Screen Reader Support

```tsx
// ✅ Use useId for unique IDs (React 18+)
import { useId } from 'react';

function FormField({ label, error, children }) {
  const id = useId();
  const errorId = `${id}-error`;

  return (
    <div>
      <label htmlFor={id}>{label}</label>
      {children({ id, 'aria-describedby': error ? errorId : undefined })}
      {error && (
        <span id={errorId} role="alert" className="text-red-500">
          {error}
        </span>
      )}
    </div>
  );
}

// ✅ Live regions for dynamic content
function Notification({ message }) {
  return (
    <div aria-live="polite" aria-atomic="true" className="sr-only">
      {message}
    </div>
  );
}

// ✅ Visually hidden helper
function VisuallyHidden({ children }) {
  return (
    <span className="absolute w-px h-px p-0 -m-px overflow-hidden whitespace-nowrap border-0">
      {children}
    </span>
  );
}
```

### 8.6 Color and Contrast

```tsx
// ✅ Ensure sufficient color contrast
function StatusBadge({ status }: { status: 'success' | 'error' | 'warning' }) {
  const styles = {
    success: 'bg-green-100 text-green-800 border-green-300',
    error: 'bg-red-100 text-red-800 border-red-300',
    warning: 'bg-yellow-100 text-yellow-800 border-yellow-300'
  };

  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠'
  };

  return (
    <span className={`inline-flex items-center px-2 py-1 rounded ${styles[status]}`}>
      <span aria-hidden="true">{icons[status]}</span>
      <span className="sr-only">{status}:</span>
      <span className="ml-1">{status.charAt(0).toUpperCase() + status.slice(1)}</span>
    </span>
  );
}
```

---

## 9. Documentation Patterns

### 9.1 Storybook Setup

```tsx
// Button.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';

const meta: Meta<typeof Button> = {
  title: 'UI/Button',
  component: Button,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'ghost', 'danger'],
    },
    size: {
      control: 'select',
      options: ['sm', 'md', 'lg'],
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: {
    children: 'Button',
    variant: 'primary',
  },
};

export const Secondary: Story = {
  args: {
    children: 'Button',
    variant: 'secondary',
  },
};

export const Loading: Story = {
  args: {
    children: 'Loading',
    isLoading: true,
  },
};

export const WithIcon: Story = {
  args: {
    children: 'With Icon',
    leftIcon: '🔍',
  },
};

// Interactive story with play function
export const ClickInteraction: Story = {
  args: {
    children: 'Click Me',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const button = canvas.getByRole('button', { name: /click me/i });
    await userEvent.click(button);
  },
};
```

### 9.2 JSDoc Documentation

```tsx
/**
 * A versatile button component that supports multiple variants, sizes, and states.
 *
 * @example
 * ```tsx
 * <Button variant="primary" size="lg" onClick={handleClick}>
 *   Click me
 * </Button>
 * ```
 *
 * @example
 * With loading state:
 * ```tsx
 * <Button isLoading loadingText="Submitting...">
 *   Submit
 * </Button>
 * ```
 */
export interface ButtonProps {
  /** The content to display inside the button */
  children: React.ReactNode;
  /** Visual style variant of the button */
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  /** Size of the button */
  size?: 'sm' | 'md' | 'lg';
  /** Whether the button is in a loading state */
  isLoading?: boolean;
  /** Text to display during loading (for screen readers) */
  loadingText?: string;
  /** Icon to display before the button text */
  leftIcon?: React.ReactNode;
  /** Icon to display after the button text */
  rightIcon?: React.ReactNode;
  /** Whether the button should take full width of its container */
  isFullWidth?: boolean;
  /** Click event handler */
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
}
```

### 9.3 README for Complex Components

```markdown
# Tabs Component

A compound component for creating accessible tabbed interfaces.

## Installation

```bash
npm install @my-ui/tabs
```

## Usage

### Basic Example

```tsx
import { Tabs, TabList, Tab, TabPanel } from '@my-ui/tabs';

function Example() {
  return (
    <Tabs defaultTab="tab1">
      <TabList>
        <Tab id="tab1">First Tab</Tab>
        <Tab id="tab2">Second Tab</Tab>
      </TabList>
      <TabPanel id="tab1">Content 1</TabPanel>
      <TabPanel id="tab2">Content 2</TabPanel>
    </Tabs>
  );
}
```

### Controlled Tabs

```tsx
function ControlledExample() {
  const [activeTab, setActiveTab] = useState('tab1');

  return (
    <Tabs activeTab={activeTab} onChange={setActiveTab}>
      {/* ... */}
    </Tabs>
  );
}
```

## API Reference

### Tabs

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| defaultTab | string | - | Initial active tab (uncontrolled) |
| activeTab | string | - | Controlled active tab value |
| onChange | (id: string) => void | - | Callback when tab changes |
| children | ReactNode | required | Tab components |

### Tab

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| id | string | required | Unique identifier for the tab |
| disabled | boolean | false | Whether the tab is disabled |
| children | ReactNode | required | Tab label |

## Accessibility

- Follows WAI-ARIA Tabs pattern
- Full keyboard navigation support
- Manages focus appropriately
- Announces tab changes to screen readers
```

### 9.4 Type-Driven Documentation

```tsx
// Use TypeScript to document expected shapes
interface DataTableProps<T extends Record<string, unknown>> {
  /**
   * Array of data items to display
   * Must have a unique 'id' field for React keys
   */
  data: Array<T & { id: string | number }>;

  /**
   * Column definitions
   * Keys must exist in the data objects
   */
  columns: Array<{
    key: keyof T;
    header: string;
    width?: string;
    render?: (value: T[keyof T], item: T) => React.ReactNode;
  }>;

  /**
   * Called when a row is clicked
   * @param item - The clicked row's data
   * @param index - The row's index in the data array
   */
  onRowClick?: (item: T, index: number) => void;
}
```

---

## 10. Ref Forwarding and Component Polymorphism

### 10.1 Ref Forwarding (React 19 Simplified)

```tsx
// React 19 - refs are now regular props, no forwardRef needed!
// React 18 and earlier - use forwardRef

// React 19 Style (Modern)
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
}

export function Button({ ref, variant = 'primary', ...props }: ButtonProps) {
  return (
    <button
      ref={ref}
      className={`btn btn-${variant}`}
      {...props}
    />
  );
}

// React 18 Style (Legacy - still works in 19)
import { forwardRef } from 'react';

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={`btn btn-${variant}`}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';
```

### 10.2 useImperativeHandle for Custom APIs

```tsx
import { useRef, useImperativeHandle } from 'react';

// Define the imperative handle interface
export interface TextInputHandle {
  focus: () => void;
  blur: () => void;
  select: () => void;
  setValue: (value: string) => void;
}

interface TextInputProps {
  defaultValue?: string;
  onChange?: (value: string) => void;
}

export const TextInput = forwardRef<TextInputHandle, TextInputProps>(
  ({ defaultValue, onChange }, ref) => {
    const inputRef = useRef<HTMLInputElement>(null);
    const [value, setValue] = useState(defaultValue || '');

    useImperativeHandle(ref, () => ({
      focus: () => inputRef.current?.focus(),
      blur: () => inputRef.current?.blur(),
      select: () => inputRef.current?.select(),
      setValue: (newValue: string) => {
        setValue(newValue);
        onChange?.(newValue);
      }
    }), [onChange]);

    return (
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          onChange?.(e.target.value);
        }}
      />
    );
  }
);

// Usage
function Parent() {
  const inputRef = useRef<TextInputHandle>(null);

  return (
    <>
      <TextInput ref={inputRef} />
      <button onClick={() => inputRef.current?.focus()}>
        Focus Input
      </button>
      <button onClick={() => inputRef.current?.setValue('Reset')}>
        Reset
      </button>
    </>
  );
}
```

### 10.3 Polymorphic Components with as Prop

```tsx
// Polymorphic component that can render as different elements
import type { ElementType, ComponentPropsWithRef, ReactNode } from 'react';

type PolymorphicProps<T extends ElementType> = {
  as?: T;
  children: ReactNode;
} & Omit<ComponentPropsWithRef<T>, 'as' | 'children'>;

// Box component - can be any HTML element
export function Box<T extends ElementType = 'div'>({
  as,
  children,
  ...props
}: PolymorphicProps<T>) {
  const Component = as || 'div';
  return <Component {...props}>{children}</Component>;
}

// Usage
<Box>Default div</Box>
<Box as="span">Span element</Box>
<Box as="section">Section element</Box>
<Box as={CustomComponent} customProp>Custom component</Box>
```

### 10.4 Advanced Polymorphic Component with Ref Forwarding

```tsx
import {
  ElementType,
  ComponentPropsWithRef,
  ReactNode,
  forwardRef,
  Ref,
} from 'react';

// Extract the ref type correctly for any element type
type PolymorphicRef<T extends ElementType> = Ref<ComponentPropsWithRef<T>['ref']>;

interface PolymorphicComponentProps<T extends ElementType> {
  as?: T;
  children?: ReactNode;
  className?: string;
}

type Props<T extends ElementType> = PolymorphicComponentProps<T> &
  Omit<ComponentPropsWithRef<T>, keyof PolymorphicComponentProps<T>>;

// Container component that can be any semantic element
export const Container = forwardRef(
  <T extends ElementType = 'div'>(
    { as, children, className, ...props }: Props<T>,
    ref: PolymorphicRef<T>
  ) => {
    const Component = as || 'div';
    return (
      <Component
        ref={ref}
        className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 ${className || ''}`}
        {...props}
      >
        {children}
      </Component>
    );
  }
) as <T extends ElementType = 'div'>(
  props: Props<T> & { ref?: PolymorphicRef<T> }
) => ReactNode;

// Usage with full type safety
<Container>Default div container</Container>
<Container as="header">Semantic header</Container>
<Container as="main" id="content">Main content area</Container>
<Container as={Link} href="/">Next.js Link</Container>
```

### 10.5 Polymorphic Button with Preserved Types

```tsx
interface BaseButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

type ButtonProps<T extends ElementType = 'button'> = BaseButtonProps &
  Omit<ComponentPropsWithRef<T>, keyof BaseButtonProps> & {
    as?: T;
  };

export const Button = forwardRef(
  <T extends ElementType = 'button'>(
    {
      as,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      children,
      disabled,
      className,
      ...props
    }: ButtonProps<T>,
    ref: PolymorphicRef<T>
  ) => {
    const Component = as || 'button';

    return (
      <Component
        ref={ref}
        disabled={disabled || isLoading}
        className={`
          inline-flex items-center justify-center font-medium rounded
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${className || ''}
        `}
        {...props}
      >
        {isLoading ? <Spinner /> : children}
      </Component>
    );
  }
) as <T extends ElementType = 'button'>(
  props: ButtonProps<T> & { ref?: PolymorphicRef<T> }
) => ReactNode;

// All these work with full type safety:
<Button onClick={handleClick}>Click me</Button>
<Button as="a" href="/about">Link button</Button>
<Button as={Link} href="/dashboard" prefetch>Next Link</Button>
```

### 10.6 Merging Refs

```tsx
import { useCallback } from 'react';

// Utility to merge multiple refs
export function useMergeRefs<T>(...refs: Array<Ref<T> | undefined>) {
  return useCallback(
    (value: T) => {
      refs.forEach((ref) => {
        if (typeof ref === 'function') {
          ref(value);
        } else if (ref && 'current' in ref) {
          (ref as MutableRefObject<T>).current = value;
        }
      });
    },
    [refs]
  );
}

// Usage in component
function InputWithMultipleRefs(props: InputProps) {
  const localRef = useRef<HTMLInputElement>(null);
  const forwardedRef = props.ref;
  const mergedRef = useMergeRefs(localRef, forwardedRef);

  useEffect(() => {
    // Can access input via localRef.current
    localRef.current?.focus();
  }, []);

  return <input ref={mergedRef} {...props} />;
}
```

---

## Summary Checklist

When creating a new React component in 2026:

- [ ] **Composition**: Use children or slots pattern for flexible content
- [ ] **TypeScript**: Define comprehensive interfaces with proper generics
- [ ] **Server/Client**: Mark Client Components with 'use client' only when needed
- [ ] **Accessibility**: Include ARIA attributes, keyboard support, and focus management
- [ ] **Refs**: Forward refs properly (or pass as prop in React 19+)
- [ ] **Naming**: Use PascalCase for components, camelCase for props
- [ ] **Documentation**: Add JSDoc comments and Storybook stories
- [ ] **Testing**: Write unit tests with proper accessibility queries
- [ ] **Polymorphism**: Support `as` prop for flexible rendering when appropriate
- [ ] **Performance**: Memoize expensive computations, lazy load when beneficial

---

## Additional Resources

- [React Documentation](https://react.dev)
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [Storybook Documentation](https://storybook.js.org/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [Radix UI Primitives](https://www.radix-ui.com/) - Unstyled, accessible components
