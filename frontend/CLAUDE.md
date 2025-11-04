# Frontend Development Guide - Alter Ego

## Project Overview

This is the frontend application for Alter Ego, an AI-powered personal chatbot. Built with React 19, TypeScript, Vite, and Tailwind CSS v4, featuring a modern **liquid glass morphism** design system.

## Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Framework** | React | 19.1.1 | UI library |
| **Build Tool** | Vite | 7.1.7 | Fast development and build |
| **Language** | TypeScript | 5.9.3 | Type-safe development |
| **Styling** | Tailwind CSS | 4.1.16 | Utility-first CSS framework |
| **UI Components** | Radix UI | Latest | Accessible component primitives |
| **Component Docs** | Storybook | 10.0.2 | Component development and documentation |
| **Testing** | Vitest + Playwright | 4.0.6 | Unit and component testing |
| **HTTP Client** | Axios | 1.13.1 | API communication |

## Design System & Styleguide

### Design Philosophy: Liquid Glass Morphism

The application uses a **liquid glass morphism** aesthetic characterized by:

- **Translucent surfaces** with backdrop blur effects
- **Subtle borders** with semi-transparent white overlays
- **Layered depth** using shadows and inset highlights
- **Smooth transitions** for interactive states
- **Glow effects** on hover and focus states
- **Flowing animations** that feel organic and fluid

This creates a modern, futuristic interface that feels both tactile and ethereal.

### Color Theme

The application features a **Cyber Purple** theme by default with support for theme switching.

#### Default Theme (Cyber Purple)

```css
/* Primary Colors - Purple Spectrum */
--color-primary-50: #faf5ff
--color-primary-100: #f3e8ff
--color-primary-200: #e9d5ff
--color-primary-300: #d8b4fe
--color-primary-400: #c4b5fd
--color-primary-500: #a78bfa
--color-primary-600: #8b5cf6  /* Main brand color */
--color-primary-700: #7c3aed
--color-primary-800: #6d28d9
--color-primary-900: #5b21b6

/* Semantic Colors */
--color-success: #10b981   /* Green */
--color-warning: #f59e0b   /* Amber */
--color-error: #ef4444     /* Red */
--color-info: #06b6d4      /* Cyan */

/* Background Colors - Dark Mode */
--color-bg-primary: #0a0a0f      /* Main background */
--color-bg-secondary: #1a1a2e    /* Card backgrounds */
--color-bg-tertiary: #2a2a3e     /* Elevated surfaces */

/* Text Colors */
--color-text-primary: #e8e8f0    /* Primary text */
--color-text-secondary: #b4b4bb  /* Secondary text */
--color-text-tertiary: #6b7280   /* Muted text */
```

#### Alternative Theme (Electric Blue)

```css
/* Override with data-theme="electric-blue" */
--color-primary-600: #2563eb  /* Main brand color - Blue */
```

### Spacing System

```css
--spacing-1: 0.25rem   /* 4px */
--spacing-2: 0.5rem    /* 8px */
--spacing-3: 0.75rem   /* 12px */
--spacing-4: 1rem      /* 16px */
--spacing-5: 1.25rem   /* 20px */
--spacing-6: 1.5rem    /* 24px */
--spacing-8: 2rem      /* 32px */
--spacing-10: 2.5rem   /* 40px */
--spacing-12: 3rem     /* 48px */
--spacing-16: 4rem     /* 64px */
--spacing-20: 5rem     /* 80px */
```

### Border Radius

```css
--radius-sm: 0.5rem    /* 8px */
--radius-md: 0.75rem   /* 12px */
--radius-lg: 1rem      /* 16px */
--radius-xl: 1.5rem    /* 24px - Standard for glass cards */
--radius-2xl: 2rem     /* 32px */
--radius-full: 9999px  /* Fully rounded */
```

**Standard:** Use `24px` (`--radius-xl`) for glass card components to maintain the liquid glass aesthetic.

### Shadows & Effects

```css
/* Liquid Glass Morphism Shadows */
--shadow-glass: 0 8px 32px rgba(0, 0, 0, 0.3)
--shadow-glass-lg: 0 12px 48px rgba(0, 0, 0, 0.4)

/* Glow Effects for Interactive States */
--shadow-glow-purple: 0 0 40px rgba(139, 92, 246, 0.4)
--shadow-glow-blue: 0 0 40px rgba(59, 130, 246, 0.4)
```

### Typography

Standard HTML typography applies. Use Tailwind utility classes for sizes:

- **Heading**: `text-2xl`, `text-xl`, `text-lg`
- **Body**: `text-base` (default), `text-sm`
- **Small**: `text-xs`

Text colors:
- Primary: `text-text-primary`
- Secondary: `text-text-secondary`
- Tertiary: `text-text-tertiary`

## Liquid Glass Morphism Utilities

The application uses custom liquid glass morphism utilities defined in `src/index.css`:

### Glass Card

The foundational building block for liquid glass surfaces.

```tsx
<div className="glass-card">
  {/* Content */}
</div>
```

**CSS Implementation:**
```css
.glass-card {
  position: relative;
  background: rgba(255, 255, 255, 0.04);  /* Translucent base */
  backdrop-filter: blur(30px) saturate(150%);  /* Liquid blur effect */
  border: 1.5px solid rgba(255, 255, 255, 0.12);  /* Subtle border */
  border-radius: 24px;  /* Smooth, rounded corners */
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.3),  /* Depth shadow */
    inset 0 1px 0 rgba(255, 255, 255, 0.1);  /* Inner highlight */
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);  /* Smooth transitions */
}
```

**Key Properties:**
- **Backdrop Filter**: `blur(30px) saturate(150%)` creates the signature liquid glass effect
- **Translucency**: `rgba(255, 255, 255, 0.04)` provides subtle surface tint
- **Inset Shadow**: Adds dimensional highlight on top edge
- **Smooth Bezier**: `cubic-bezier(0.4, 0, 0.2, 1)` for fluid transitions

### Glass Button (Primary)

Interactive glass button with glow effects on hover.

```tsx
<Button className="glass-button-primary">
  Action
</Button>
```

**Features:**
- Hover glow effect with `--shadow-glow-purple`
- Transform scale on hover for tactile feedback
- Maintains glass morphism aesthetic

### Glass Input

Translucent input field matching the glass aesthetic.

```tsx
<Input className="glass-input" placeholder="Type here..." />
```

**Features:**
- Blurred background for readability
- Focus glow state
- Smooth border transitions

### Glass Scroll Area

Custom scrollable container with glass styling.

```tsx
<ScrollArea className="glass-scroll">
  {/* Scrollable content */}
</ScrollArea>
```

**Features:**
- Semi-transparent scrollbar
- Maintains backdrop blur within scrollable region
- Smooth scrolling behavior

## UI Component Patterns

### Component Library

All UI components are built on **Radix UI** primitives and use **class-variance-authority (CVA)** for variant management.

#### Button Component

```tsx
import { Button } from '@/components/ui/button';

// Variants
<Button variant="default">Default</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline">Outline</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="link">Link</Button>

// Sizes
<Button size="default">Default</Button>
<Button size="sm">Small</Button>
<Button size="lg">Large</Button>
<Button size="icon">Icon</Button>

// Apply liquid glass style
<Button className="glass-button-primary">Glass Button</Button>
```

#### Card Component

```tsx
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

<Card className="glass-card">
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Card description</CardDescription>
  </CardHeader>
  <CardContent>
    {/* Content */}
  </CardContent>
</Card>
```

#### Input Component

```tsx
import { Input } from '@/components/ui/input';

<Input
  placeholder="Type here..."
  className="glass-input"
  aria-label="Input label"
/>
```

#### Avatar Component

```tsx
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

<Avatar className="border-2 border-primary-600">
  <AvatarFallback className="bg-primary-600/20 text-primary-400">
    U
  </AvatarFallback>
</Avatar>
```

### Animations

#### Message Animation (Slide In)

Fluid slide-in animation for chat messages.

```tsx
<div className="animate-[message-in_0.3s_ease-out]">
  {/* Message content */}
</div>
```

**Timing**: 300ms with ease-out for natural deceleration.

#### Loading Dots

Bouncing dots animation for loading states.

```tsx
<div className="flex gap-1">
  <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '0ms' }} />
  <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '150ms' }} />
  <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '300ms' }} />
</div>
```

**Stagger**: 150ms delay between each dot for wave effect.

#### Pulse Effect

Subtle pulsing for loading states.

```tsx
<div className="animate-pulse">
  {/* Pulsing content */}
</div>
```

#### Transition Standards

All interactive elements should use smooth transitions:

```css
transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
```

- **Duration**: 500ms for major state changes (hover, focus)
- **Duration**: 300ms for minor transitions (color, opacity)
- **Easing**: `cubic-bezier(0.4, 0, 0.2, 1)` for fluid, organic feel

## Architecture Patterns

### Project Structure

```
frontend/
├── src/
│   ├── components/        # React components
│   │   ├── ui/           # Reusable UI components (Radix-based)
│   │   ├── ChatInterface.tsx
│   │   ├── LandingPage.tsx
│   │   └── ThemeSwitcher.tsx
│   ├── services/         # API services
│   │   └── api.ts        # Axios-based API client
│   ├── types/            # TypeScript type definitions
│   │   └── index.ts
│   ├── lib/              # Utility functions
│   │   └── utils.ts      # cn() helper
│   ├── stories/          # Storybook stories
│   ├── assets/           # Static assets
│   ├── App.tsx           # Root component
│   ├── main.tsx          # Application entry point
│   └── index.css         # Global styles & design tokens
├── public/               # Public static files
├── .storybook/           # Storybook configuration
├── vite.config.ts        # Vite configuration
├── tsconfig.json         # TypeScript configuration
└── package.json          # Dependencies
```

### Component Development Pattern

1. **Use TypeScript** for all components
2. **Extract types** to `src/types/index.ts` for reusability
3. **Use functional components** with hooks
4. **Follow Radix UI patterns** for accessible components
5. **Apply liquid glass morphism** via utility classes

**Example Component:**

```tsx
import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { Message } from '@/types';

export function ExampleComponent() {
  const [state, setState] = useState<Message[]>([]);

  return (
    <Card className="glass-card">
      <CardContent>
        <Button className="glass-button-primary">
          Action
        </Button>
      </CardContent>
    </Card>
  );
}
```

### State Management

- **Local state**: `useState` for component-specific state
- **Refs**: `useRef` for DOM references and mutable values
- **Side effects**: `useEffect` for data fetching and subscriptions

**No global state management** is currently used (Redux, Zustand not needed for current scope).

### API Integration Pattern

All backend communication uses the centralized API service (`src/services/api.ts`):

```tsx
import { sendMessage, ApiError } from '@/services/api';

try {
  const response = await sendMessage(userMessage);
  // Handle response
} catch (err) {
  if (err instanceof ApiError) {
    // Handle API error
  }
}
```

**API Client Configuration:**
- Base URL: `http://localhost:8000`
- Timeout: 10 seconds
- Custom error handling with `ApiError` class

## Accessibility Standards

### ARIA Implementation

- **Roles**: Use semantic HTML and ARIA roles (`role="log"` for chat)
- **Live regions**: `aria-live="polite"` for dynamic content
- **Labels**: Always provide `aria-label` for inputs and buttons
- **Descriptions**: Use `aria-describedby` for additional context
- **Error states**: Mark with `aria-invalid`

**Example:**
```tsx
<Input
  aria-label="Message input"
  aria-describedby="message-input-description"
  aria-invalid={!!error}
/>
```

### Screen Reader Support

- Use `.sr-only` class for screen-reader-only text
- Provide descriptive labels for all interactive elements

```tsx
<span className="sr-only">
  Type your message and press Enter to send
</span>
```

### Keyboard Navigation

- **Enter**: Submit forms/send messages
- **Escape**: Clear input or dismiss modals
- **Tab**: Navigate through interactive elements
- All buttons and inputs must be keyboard accessible

## Development Workflow

### Path Aliases

Use `@/` for imports from `src/`:

```tsx
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { Message } from '@/types';
```

### Running the Application

```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm run test

# Run Storybook
npm run storybook
```

### Component Development with Storybook

1. Create component in `src/components/ui/`
2. Create corresponding story in `src/components/ui/*.stories.tsx`
3. Run `npm run storybook` to develop in isolation
4. Document variants and usage examples

**Story Example:**
```tsx
import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './button';

const meta: Meta<typeof Button> = {
  component: Button,
  title: 'UI/Button',
};

export default meta;

export const Default: StoryObj<typeof Button> = {
  args: {
    children: 'Button',
    variant: 'default',
  },
};
```

### Testing Guidelines

- **Unit tests**: For utility functions and hooks
- **Component tests**: For UI components with Vitest + Playwright
- **Accessibility tests**: Use Storybook addon-a11y

## Best Practices

### Component Guidelines

1. **Keep components small and focused** - Single responsibility
2. **Extract reusable logic** to custom hooks
3. **Type everything** - Avoid `any`
4. **Use composition** over prop drilling
5. **Handle loading and error states** explicitly

### Styling Guidelines

1. **Use Tailwind utilities first** - Avoid custom CSS when possible
2. **Apply liquid glass morphism** with provided utility classes (`glass-card`, `glass-button-primary`, etc.)
3. **Use design tokens** (CSS variables) for colors
4. **Maintain consistent spacing** using the spacing system
5. **Ensure dark mode compatibility** with theme variables
6. **Preserve the liquid glass aesthetic** - Always use backdrop blur and translucent surfaces

### Performance Guidelines

1. **Lazy load components** when appropriate
2. **Memoize expensive calculations** with `useMemo`
3. **Avoid unnecessary re-renders** with `React.memo` and `useCallback`
4. **Optimize images** (use WebP format)
5. **Code split routes** if application grows

## Integration with Backend

The frontend communicates with the FastAPI backend at `http://localhost:8000`:

**Endpoints:**
- `POST /api/chat` - Send chat message and receive AI response

**CORS Configuration:**
- Allowed origins: `http://localhost:5173`

**Request/Response Format:**
```typescript
// Request
interface ChatRequest {
  message: string;
}

// Response
interface ChatResponse {
  response: string;
  timestamp: string; // ISO8601 format
}
```

## Environment Configuration

Create `.env` file in the frontend root:

```env
VITE_API_URL=http://localhost:8000
```

Access in code:
```tsx
const apiUrl = import.meta.env.VITE_API_URL;
```

---

**Generated:** 2025-11-04
**Last Updated:** 2025-11-04
**Design System:** Liquid Glass Morphism with Cyber Purple theme
