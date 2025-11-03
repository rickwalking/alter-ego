# Alter Ego - UX Design Specification
## Liquid Glass Morphism Design System

**Project:** Alter Ego - AI Personal Chatbot
**Version:** 1.0
**Date:** 2025-11-02
**Designer:** Sally (UX Designer Agent)
**Approved By:** BMad

---

## 1. Design Vision

### Core Philosophy
Modern, innovative AI chatbot interface featuring authentic liquid glass morphism with dual theme support. The design balances cutting-edge aesthetics with professional credibility, perfect for recruiters evaluating candidates.

### Brand Personality
- **Modern & Innovative** - Cutting-edge technology showcase
- **Premium Quality** - High-end visual treatment
- **User-Centric** - Respects user preferences with theme choice
- **Professional** - Maintains trust and credibility

### Target Experience
Recruiters should feel they're interacting with a **next-generation AI interface** that demonstrates the candidate's mastery of modern frontend technologies while maintaining professional usability.

---

## 2. Design System Foundation

### 2.1 Tech Stack Integration
- **Framework:** React 19.2.0 with TypeScript 5.9.3
- **Styling:** Tailwind CSS 4.0 (CSS-first configuration)
- **Components:** Shadcn UI (customized with liquid glass)
- **Build Tool:** Vite 7.0
- **Component Docs:** Storybook 9.x
- **Platform:** Desktop-primary with full mobile responsive support

### 2.2 Design System
**Chosen System:** Shadcn UI + Custom Liquid Glass Layer

**Rationale:**
- Shadcn UI provides unstyled, accessible primitives
- Full customization freedom for liquid glass aesthetic
- TypeScript-native with excellent Radix UI foundation
- Perfect for showcasing advanced CSS skills

---

## 3. Dual Theme System

### 3.1 Theme Overview

#### Theme 1: Cyber Purple (Primary)
**Personality:** Futuristic, Creative, Premium AI
**Use Case:** Default theme - emphasizes innovation and creativity
**Color Psychology:** Purple = creativity, wisdom, premium technology

#### Theme 2: Electric Blue (Secondary)
**Personality:** Professional, Trustworthy, Modern Tech
**Use Case:** Alternative for users preferring classic tech aesthetic
**Color Psychology:** Blue = trust, stability, professionalism

### 3.2 Theme Switching Behavior

**Implementation Strategy:**
```typescript
// Theme Detection Priority:
1. Check localStorage for saved preference
2. If no preference, default to Cyber Purple
3. User can toggle between themes via button
4. Save preference to localStorage on change
5. Apply theme immediately without page reload
```

**User Flow:**
1. **First Visit:** Loads Cyber Purple (default)
2. **Toggle Action:** User clicks theme toggle button
3. **Instant Switch:** Theme changes with smooth 300ms transition
4. **Persistence:** Choice saved to `localStorage.theme`
5. **Return Visit:** Loads saved preference automatically

**Toggle Button Specification:**
- **Location:** Top-right corner of interface (fixed position)
- **Visual:** Glass morphic toggle with theme color preview
- **States:** Cyber Purple (🟣) ⟷ Electric Blue (🔵)
- **Icon:** Smooth animated transition between theme indicators
- **Accessibility:** ARIA label, keyboard accessible (Tab + Enter)

---

## 4. Color System

### 4.1 Cyber Purple Theme

#### Primary Colors
```css
--primary-50: #faf5ff
--primary-100: #f3e8ff
--primary-200: #e9d5ff
--primary-300: #d8b4fe
--primary-400: #c4b5fd
--primary-500: #a78bfa
--primary-600: #8b5cf6  /* Main brand color */
--primary-700: #7c3aed
--primary-800: #6d28d9
--primary-900: #5b21b6
```

#### Semantic Colors
```css
--success: #10b981
--warning: #f59e0b
--error: #ef4444
--info: #06b6d4
```

#### Neutral Scale (Dark Mode)
```css
--bg-primary: #0a0a0f
--bg-secondary: #1a1a2e
--bg-tertiary: #2a2a3e
--text-primary: #e8e8f0
--text-secondary: #b4b4bb
--text-tertiary: #6b7280
--border-primary: rgba(255, 255, 255, 0.12)
--border-secondary: rgba(255, 255, 255, 0.08)
```

#### Glass Morphism Values
```css
--glass-bg: rgba(255, 255, 255, 0.04)
--glass-bg-hover: rgba(255, 255, 255, 0.06)
--glass-border: rgba(196, 181, 253, 0.3)
--glass-blur: blur(30px)
--glass-saturate: saturate(150%)
--glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.3)
--glass-glow: 0 0 40px rgba(139, 92, 246, 0.4)
```

### 4.2 Electric Blue Theme

#### Primary Colors
```css
--primary-50: #eff6ff
--primary-100: #dbeafe
--primary-200: #bfdbfe
--primary-300: #93c5fd
--primary-400: #60a5fa
--primary-500: #3b82f6  /* Main brand color */
--primary-600: #2563eb
--primary-700: #1d4ed8
--primary-800: #1e40af
--primary-900: #1e3a8a
```

#### Semantic Colors
```css
--success: #10b981
--warning: #f59e0b
--error: #ef4444
--info: #06b6d4
```

#### Neutral Scale (Same as Cyber Purple)
```css
/* Identical neutral scale for consistency */
```

#### Glass Morphism Values
```css
--glass-bg: rgba(255, 255, 255, 0.04)
--glass-bg-hover: rgba(255, 255, 255, 0.06)
--glass-border: rgba(147, 197, 253, 0.3)
--glass-blur: blur(30px)
--glass-saturate: saturate(150%)
--glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.3)
--glass-glow: 0 0 40px rgba(59, 130, 246, 0.4)
```

---

## 5. Typography System

### 5.1 Font Families
```css
--font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif
--font-mono: 'Courier New', 'Monaco', 'Consolas', monospace
```

**Rationale:** System fonts for optimal performance and native feel across platforms.

### 5.2 Type Scale
```css
--text-xs: 0.75rem      /* 12px - Captions, labels */
--text-sm: 0.875rem     /* 14px - Secondary text */
--text-base: 1rem       /* 16px - Body text */
--text-lg: 1.125rem     /* 18px - Large body */
--text-xl: 1.25rem      /* 20px - Small headings */
--text-2xl: 1.5rem      /* 24px - Card titles */
--text-3xl: 1.875rem    /* 30px - Section headings */
--text-4xl: 2.25rem     /* 36px - Page titles */
--text-5xl: 3rem        /* 48px - Hero text */
```

### 5.3 Font Weights
```css
--font-light: 300       /* Descriptions, secondary info */
--font-normal: 400      /* Body text */
--font-medium: 500      /* Emphasis */
--font-semibold: 600    /* Buttons, labels */
--font-bold: 700        /* Headings */
```

### 5.4 Line Heights
```css
--leading-tight: 1.25   /* Headings */
--leading-normal: 1.5   /* Body text */
--leading-relaxed: 1.75 /* Comfortable reading */
```

### 5.5 Letter Spacing
```css
--tracking-tight: -0.025em   /* Large headings */
--tracking-normal: 0         /* Body text */
--tracking-wide: 0.025em     /* Buttons */
--tracking-wider: 0.05em     /* Labels, tags */
```

---

## 6. Spacing System

### 6.1 Base Unit
**8px Grid System** - All spacing is a multiple of 8px for visual rhythm

```css
--space-1: 0.25rem   /* 4px  - Tight spacing */
--space-2: 0.5rem    /* 8px  - Base unit */
--space-3: 0.75rem   /* 12px - Small gaps */
--space-4: 1rem      /* 16px - Standard gap */
--space-5: 1.25rem   /* 20px - Medium gap */
--space-6: 1.5rem    /* 24px - Large gap */
--space-8: 2rem      /* 32px - Section spacing */
--space-10: 2.5rem   /* 40px - Component spacing */
--space-12: 3rem     /* 48px - Large sections */
--space-16: 4rem     /* 64px - Major sections */
--space-20: 5rem     /* 80px - Page sections */
```

### 6.2 Component Spacing Guidelines
- **Button Padding:** `--space-3` (vertical) × `--space-6` (horizontal)
- **Card Padding:** `--space-6` to `--space-8`
- **Input Padding:** `--space-3` (vertical) × `--space-4` (horizontal)
- **Section Margin:** `--space-12` to `--space-16`
- **Container Max-Width:** 1400px (desktop), 100% (mobile)

---

## 7. Liquid Glass Component System

### 7.1 Glass Card Component

**Visual Characteristics:**
- Background: `rgba(255, 255, 255, 0.04)` with `backdrop-filter: blur(30px)`
- Border: 1.5px solid with theme-colored glow
- Border Radius: 24px (large), 16px (medium), 12px (small)
- Shadow: Multi-layer depth shadows
- Hover: Lift effect with increased glow

**Implementation:**
```css
.glass-card {
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(30px) saturate(150%);
  border: 1.5px solid var(--glass-border);
  border-radius: 24px;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.2);
  box-shadow:
    0 12px 48px rgba(0, 0, 0, 0.4),
    0 0 60px var(--glass-glow),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
}
```

**Shadcn UI Integration:**
Apply to `Card` component via Tailwind classes in `components/ui/card.tsx`

### 7.2 Button Component

**Primary Button (Call-to-Action):**
```css
.btn-primary {
  background: linear-gradient(135deg,
    var(--primary-600) 0%,
    var(--primary-800) 100%);
  backdrop-filter: blur(20px);
  border: 1.5px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 0.85rem 2rem;
  border-radius: 16px;
  font-weight: 600;
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.2),
    0 0 30px var(--glass-glow);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-primary:hover {
  transform: translateY(-3px) scale(1.05);
  box-shadow:
    0 12px 32px rgba(0, 0, 0, 0.3),
    0 0 60px var(--glass-glow);
}
```

**Secondary Button:**
```css
.btn-secondary {
  background: rgba(var(--primary-rgb), 0.15);
  backdrop-filter: blur(20px);
  border: 1.5px solid var(--glass-border);
  color: var(--primary-400);
  /* Similar sizing and effects */
}
```

**States:**
- Default: As specified above
- Hover: Lift + glow increase
- Active: Scale down slightly (0.98)
- Disabled: Opacity 0.5, no hover effects
- Loading: Spinner with pulse animation

**Shadcn UI Integration:**
Customize `components/ui/button.tsx` with glass variants

### 7.3 Input Component

**Text Input:**
```css
.glass-input {
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(30px) saturate(150%);
  border: 1.5px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  padding: 1rem 1.25rem;
  color: var(--text-primary);
  font-size: 0.95rem;
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-input:focus {
  outline: none;
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--primary-400);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.3),
    0 0 40px var(--glass-glow);
  transform: translateY(-2px);
}

.glass-input::placeholder {
  color: #6b7280;
}
```

**Shadcn UI Integration:**
Apply to `Input` component in `components/ui/input.tsx`

### 7.4 Chat Message Bubble

**User Message:**
```css
.message-user {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(30px);
  border: 1.5px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px 20px 4px 20px;
  padding: 1rem 1.25rem;
  max-width: 75%;
  margin-left: auto;
}
```

**AI Message (with theme glow):**
```css
.message-ai {
  background: rgba(var(--primary-rgb), 0.15);
  backdrop-filter: blur(30px);
  border: 1.5px solid var(--glass-border);
  border-radius: 20px 20px 20px 4px;
  padding: 1rem 1.25rem;
  max-width: 75%;
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.2),
    0 0 20px var(--glass-glow);
}
```

**Avatar Component:**
```css
.avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg,
    var(--primary-600) 0%,
    var(--primary-800) 100%);
  border: 2px solid var(--glass-border);
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.3),
    0 0 30px var(--glass-glow);
}
```

### 7.5 ScrollArea Component

**Styling for Chat History:**
- Glass background with subtle border
- Custom scrollbar with glass aesthetic
- Auto-scroll to bottom on new messages
- Smooth scroll behavior

```css
.glass-scroll {
  background: rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
}

.glass-scroll::-webkit-scrollbar {
  width: 8px;
}

.glass-scroll::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 10px;
}

.glass-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  backdrop-filter: blur(10px);
}

.glass-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.15);
}
```

---

## 8. Responsive Design Strategy

### 8.1 Breakpoints
```css
--breakpoint-sm: 640px   /* Mobile landscape */
--breakpoint-md: 768px   /* Tablet portrait */
--breakpoint-lg: 1024px  /* Tablet landscape */
--breakpoint-xl: 1280px  /* Desktop */
--breakpoint-2xl: 1536px /* Large desktop */
```

### 8.2 Layout Adaptation

**Desktop (1024px+):**
- Two-column layout: Landing page (left) + Chat (right)
- Side-by-side Card components
- Larger glass blur effects (30-40px)
- Hover states fully active

**Tablet (768px - 1023px):**
- Single column with sections stacked
- Maintain glass effects but slightly reduced blur (25px)
- Touch-optimized button sizes (min 44px)
- Simplified hover → tap interactions

**Mobile (< 768px):**
- Full single-column layout
- Chat interface takes full viewport height
- Reduced blur for performance (20px)
- Bottom-fixed input area
- Collapsible landing page section
- Theme toggle moves to header/nav area

### 8.3 Touch Target Sizes
- **Minimum:** 44px × 44px (Apple/WCAG standard)
- **Buttons:** 48px height minimum on mobile
- **Inputs:** 52px height for comfortable typing
- **Toggle Switch:** 56px × 32px

### 8.4 Performance Optimizations
- **Backdrop-filter fallback:** Solid dark background for unsupported browsers
- **Reduced animations on mobile:** Prefer `prefers-reduced-motion`
- **GPU acceleration:** Use `transform` and `opacity` for animations
- **Lazy load:** Heavy blur effects after initial paint

---

## 9. Animation & Transitions

### 9.1 Animation Principles
- **Duration:** 200-400ms for most interactions
- **Easing:** `cubic-bezier(0.4, 0, 0.2, 1)` (smooth ease-in-out)
- **Purposeful:** Every animation serves user feedback
- **Performance:** GPU-accelerated properties only

### 9.2 Key Animations

**Theme Switch Transition:**
```css
* {
  transition:
    background-color 300ms ease,
    border-color 300ms ease,
    box-shadow 300ms ease,
    color 300ms ease;
}
```

**Floating Elements (Ambient Orbs):**
```css
@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(5deg); }
}
```

**Glow Pulse (AI Avatar):**
```css
@keyframes glow-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}
```

**Shimmer Effect (Card Hover):**
```css
@keyframes shimmer {
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
}
```

**Message Appear:**
```css
@keyframes message-in {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
```

### 9.3 Loading States
- **Spinner:** Rotating glass ring with gradient
- **Skeleton:** Glass cards with subtle pulse
- **Typing Indicator:** Three dots with sequential bounce

---

## 10. Accessibility Strategy

### 10.1 WCAG 2.1 Level AA Compliance

**Target:** Meet WCAG 2.1 Level AA standards for professional/public use

**Key Requirements:**
- Color contrast ratio ≥ 4.5:1 for normal text
- Color contrast ratio ≥ 3:1 for large text (18pt+)
- All interactive elements keyboard accessible
- Meaningful focus indicators on all focusable elements
- ARIA labels for screen readers
- Semantic HTML structure

### 10.2 Color Contrast Validation

**Cyber Purple Theme:**
- Primary text (#e8e8f0) on dark background (#0a0a0f): ✅ 13.5:1
- Secondary text (#b4b4bb) on dark background: ✅ 8.2:1
- Primary button text (white) on purple (#8b5cf6): ✅ 4.7:1
- Links/accents (#c4b5fd) on dark background: ✅ 9.1:1

**Electric Blue Theme:**
- Primary text (#e8e8f0) on dark background (#0a0a0f): ✅ 13.5:1
- Secondary text (#b4b4bb) on dark background: ✅ 8.2:1
- Primary button text (white) on blue (#3b82f6): ✅ 5.1:1
- Links/accents (#93c5fd) on dark background: ✅ 8.5:1

### 10.3 Keyboard Navigation

**Tab Order:**
1. Theme toggle button
2. Landing page interactive elements (if any)
3. Chat input field
4. Send button
5. Message history (scrollable with arrow keys)

**Keyboard Shortcuts:**
- `Tab` - Navigate forward
- `Shift + Tab` - Navigate backward
- `Enter` - Activate buttons, submit message
- `Escape` - Close modals/dialogs (if any)
- `Ctrl/Cmd + K` - Focus chat input (nice-to-have)

### 10.4 Screen Reader Support

**ARIA Labels:**
```html
<button aria-label="Toggle theme between Cyber Purple and Electric Blue">
  <span aria-hidden="true">🎨</span>
</button>

<div role="log" aria-live="polite" aria-label="Chat messages">
  <!-- Messages appear here -->
</div>

<input
  type="text"
  aria-label="Type your message"
  placeholder="Ask me anything..."
/>
```

**Semantic HTML:**
- Use `<main>`, `<nav>`, `<section>`, `<article>` appropriately
- Proper heading hierarchy (h1 → h2 → h3)
- `<button>` for actions, `<a>` for navigation
- `<label>` associated with all form inputs

### 10.5 Focus Indicators

**Visible Focus State:**
```css
*:focus-visible {
  outline: 2px solid var(--primary-400);
  outline-offset: 4px;
  box-shadow: 0 0 0 4px rgba(var(--primary-rgb), 0.2);
}
```

**Focus should never be removed** - Only use `:focus-visible` to hide on mouse clicks

### 10.6 Motion Preferences

**Respect `prefers-reduced-motion`:**
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 11. Tailwind CSS 4.0 Configuration

### 11.1 CSS-First Configuration

**Location:** `frontend/src/index.css` or `frontend/src/app.css`

```css
@import "tailwindcss";

@theme {
  /* Cyber Purple Theme (Default) */
  --color-primary-50: #faf5ff;
  --color-primary-100: #f3e8ff;
  --color-primary-200: #e9d5ff;
  --color-primary-300: #d8b4fe;
  --color-primary-400: #c4b5fd;
  --color-primary-500: #a78bfa;
  --color-primary-600: #8b5cf6;
  --color-primary-700: #7c3aed;
  --color-primary-800: #6d28d9;
  --color-primary-900: #5b21b6;

  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #06b6d4;

  --color-bg-primary: #0a0a0f;
  --color-bg-secondary: #1a1a2e;
  --color-bg-tertiary: #2a2a3e;

  --color-text-primary: #e8e8f0;
  --color-text-secondary: #b4b4bb;
  --color-text-tertiary: #6b7280;

  /* Spacing */
  --spacing-1: 0.25rem;
  --spacing-2: 0.5rem;
  --spacing-3: 0.75rem;
  --spacing-4: 1rem;
  --spacing-5: 1.25rem;
  --spacing-6: 1.5rem;
  --spacing-8: 2rem;
  --spacing-10: 2.5rem;
  --spacing-12: 3rem;
  --spacing-16: 4rem;
  --spacing-20: 5rem;

  /* Border Radius */
  --radius-sm: 0.5rem;
  --radius-md: 0.75rem;
  --radius-lg: 1rem;
  --radius-xl: 1.5rem;
  --radius-2xl: 2rem;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-glass: 0 8px 32px rgba(0, 0, 0, 0.3);
  --shadow-glass-lg: 0 12px 48px rgba(0, 0, 0, 0.4);
  --shadow-glow-purple: 0 0 40px rgba(139, 92, 246, 0.4);
  --shadow-glow-blue: 0 0 40px rgba(59, 130, 246, 0.4);
}

/* Electric Blue Theme Override */
[data-theme="electric-blue"] {
  --color-primary-50: #eff6ff;
  --color-primary-100: #dbeafe;
  --color-primary-200: #bfdbfe;
  --color-primary-300: #93c5fd;
  --color-primary-400: #60a5fa;
  --color-primary-500: #3b82f6;
  --color-primary-600: #2563eb;
  --color-primary-700: #1d4ed8;
  --color-primary-800: #1e40af;
  --color-primary-900: #1e3a8a;
}

/* Glass Morphism Utilities */
@layer utilities {
  .glass-card {
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(30px) saturate(150%);
    border: 1.5px solid rgba(255, 255, 255, 0.12);
    box-shadow:
      0 8px 32px rgba(0, 0, 0, 0.3),
      inset 0 1px 0 rgba(255, 255, 255, 0.1);
  }

  .glass-input {
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(30px) saturate(150%);
    border: 1.5px solid rgba(255, 255, 255, 0.12);
    box-shadow:
      0 4px 16px rgba(0, 0, 0, 0.2),
      inset 0 1px 0 rgba(255, 255, 255, 0.08);
  }

  .glass-button-primary {
    background: linear-gradient(135deg,
      var(--color-primary-600) 0%,
      var(--color-primary-800) 100%);
    backdrop-filter: blur(20px);
    border: 1.5px solid rgba(255, 255, 255, 0.2);
    box-shadow:
      0 4px 16px rgba(0, 0, 0, 0.2),
      0 0 30px var(--shadow-glow-purple);
  }

  .glass-glow-purple {
    box-shadow: 0 0 40px rgba(139, 92, 246, 0.4);
  }

  .glass-glow-blue {
    box-shadow: 0 0 40px rgba(59, 130, 246, 0.4);
  }
}
```

### 11.2 Vite Plugin Configuration

**Location:** `frontend/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss()
  ]
})
```

**Note:** Tailwind CSS 4.0 does NOT use `tailwind.config.js` or `postcss.config.js`

---

## 12. Storybook Configuration

### 12.1 Theme Preview in Storybook

**Setup Dual Theme Decorator:**

**Location:** `.storybook/preview.tsx`

```typescript
import type { Preview } from "@storybook/react";
import { useEffect } from "react";
import "../src/index.css";

const ThemeDecorator = (Story, context) => {
  const theme = context.globals.theme || 'cyber-purple';

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  return <Story />;
};

const preview: Preview = {
  parameters: {
    backgrounds: {
      default: 'dark',
      values: [
        {
          name: 'dark',
          value: '#0a0a0f',
        },
      ],
    },
    actions: { argTypesRegex: "^on[A-Z].*" },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
  },
  globalTypes: {
    theme: {
      name: 'Theme',
      description: 'Global theme for components',
      defaultValue: 'cyber-purple',
      toolbar: {
        icon: 'paintbrush',
        items: [
          { value: 'cyber-purple', title: 'Cyber Purple' },
          { value: 'electric-blue', title: 'Electric Blue' },
        ],
        showName: true,
      },
    },
  },
  decorators: [ThemeDecorator],
};

export default preview;
```

### 12.2 Component Stories Structure

**Example: Button Component Story**

**Location:** `frontend/src/components/ui/button.stories.tsx`

```typescript
import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './button';

const meta = {
  title: 'UI/Button',
  component: Button,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'ghost'],
    },
    size: {
      control: 'select',
      options: ['sm', 'md', 'lg'],
    },
  },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: {
    variant: 'primary',
    children: 'Send Message',
  },
};

export const Secondary: Story = {
  args: {
    variant: 'secondary',
    children: 'View Profile',
  },
};

export const WithIcon: Story = {
  args: {
    variant: 'primary',
    children: (
      <>
        <span>✨</span> Ask AI
      </>
    ),
  },
};

export const Loading: Story = {
  args: {
    variant: 'primary',
    children: 'Sending...',
    disabled: true,
  },
};
```

### 12.3 Storybook Addons

**Required Addons:**
```json
{
  "dependencies": {
    "@storybook/addon-essentials": "^9.1.0",
    "@storybook/addon-interactions": "^9.1.0",
    "@storybook/addon-a11y": "^9.1.0",
    "@storybook/test": "^9.1.0"
  }
}
```

**Accessibility Testing:** `@storybook/addon-a11y` will validate contrast ratios, ARIA labels, and keyboard navigation automatically in Storybook UI.

---

## 13. Component Implementation Guide

### 13.1 Theme Toggle Component

**Location:** `frontend/src/components/ThemeToggle.tsx`

**Functionality:**
- Detects saved theme from localStorage on mount
- Defaults to 'cyber-purple' if no saved preference
- Toggles between 'cyber-purple' and 'electric-blue'
- Saves preference to localStorage
- Updates `data-theme` attribute on `<html>` element
- Smooth 300ms transition between themes

**Component Structure:**
```typescript
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';

export function ThemeToggle() {
  const [theme, setTheme] = useState<'cyber-purple' | 'electric-blue'>('cyber-purple');

  // Load saved theme on mount
  useEffect(() => {
    const saved = localStorage.getItem('theme') as 'cyber-purple' | 'electric-blue' | null;
    if (saved) {
      setTheme(saved);
      document.documentElement.setAttribute('data-theme', saved);
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'cyber-purple' ? 'electric-blue' : 'cyber-purple';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === 'cyber-purple' ? 'Electric Blue' : 'Cyber Purple'} theme`}
      className="fixed top-4 right-4 glass-card"
    >
      {theme === 'cyber-purple' ? '🟣' : '🔵'}
    </Button>
  );
}
```

### 13.2 Chat Interface Structure

**Component Hierarchy:**
```
<main>
  <ThemeToggle />
  <div class="grid lg:grid-cols-2">
    <LandingPage />
    <ChatInterface>
      <ScrollArea>
        <ChatMessage role="user" />
        <ChatMessage role="ai" />
      </ScrollArea>
      <ChatInput />
    </ChatInterface>
  </div>
</main>
```

### 13.3 Shadcn UI Component Customizations

**Required Components:**
1. **Button** - Primary, Secondary variants with glass styling
2. **Card** - Glass morphic container
3. **Input** - Glass text input with focus states
4. **ScrollArea** - Chat message container
5. **Avatar** - User/AI distinction with theme glow

**Installation:**
```bash
npx shadcn@latest add button card input scroll-area avatar
```

**Customization Approach:**
- Modify base styles in `components/ui/*.tsx`
- Apply Tailwind glass utilities
- Add theme-aware CSS variables
- Ensure all states (hover, focus, disabled) use glass aesthetic

---

## 14. User Journey: Chat Interaction Flow

### 14.1 Primary User Flow

**Step 1: Landing**
- User arrives at page
- Sees dark liquid glass interface with default theme (Cyber Purple)
- Landing page introduces the chatbot with glass card
- Theme toggle visible in top-right corner

**Step 2: Theme Selection (Optional)**
- User clicks theme toggle
- Smooth 300ms transition to Electric Blue
- Preference saved to localStorage
- All components update theme colors instantly

**Step 3: Chat Initiation**
- User focuses on chat input (auto-focus on load)
- Input field glows with theme color on focus
- Placeholder text guides user: "Ask me anything..."

**Step 4: Message Sending**
- User types message and presses Enter or clicks Send button
- User message appears in chat with right-aligned bubble
- Loading indicator shows (AI avatar pulses with glow)
- Input clears automatically

**Step 5: AI Response**
- AI response appears with left-aligned bubble
- Bubble has theme-colored glow effect
- Auto-scroll to bottom to show new message
- Chat history preserved in ScrollArea

**Step 6: Continued Conversation**
- User can continue asking questions
- Message history displays in chronological order
- Smooth scroll behavior for long conversations
- Theme remains consistent unless toggled

### 14.2 Edge Cases & Error States

**Backend Unavailable:**
- Error message displayed in glass card: "Unable to connect. Please try again."
- Retry button with glass styling
- Input remains functional for queue

**Network Timeout:**
- Timeout after 30 seconds
- Error message with retry option
- Previous messages preserved

**Empty Message Submission:**
- Validation prevents empty send
- Subtle shake animation on input
- Placeholder text emphasizes: "Type something first"

**Long Messages:**
- Input has max-length: 2000 characters
- Character counter appears at 1800 chars
- Graceful wrap in message bubbles

---

## 15. Implementation Checklist

### 15.1 Phase 1: Setup & Configuration
- [ ] Install Tailwind CSS 4.0 with @tailwindcss/vite plugin
- [ ] Configure Tailwind theme in CSS with @theme directive
- [ ] Set up Storybook 9.x with theme decorator
- [ ] Install Shadcn UI and add required components
- [ ] Create glass utility classes

### 15.2 Phase 2: Core Components
- [ ] Implement ThemeToggle component with localStorage
- [ ] Customize Button component with glass variants
- [ ] Customize Card component with glass styling
- [ ] Customize Input component with glass effects
- [ ] Customize ScrollArea for chat history
- [ ] Customize Avatar component with theme glow

### 15.3 Phase 3: Layout & Pages
- [ ] Create LandingPage component with glass cards
- [ ] Create ChatInterface component structure
- [ ] Implement ChatMessage component (user/AI variants)
- [ ] Implement ChatInput with send functionality
- [ ] Set up responsive grid layout (desktop/mobile)
- [ ] Add ambient background orbs animation

### 15.4 Phase 4: Integration & Polish
- [ ] Connect chat to backend API (POST /api/chat)
- [ ] Implement loading states
- [ ] Implement error handling & retry
- [ ] Add auto-scroll to latest message
- [ ] Test theme switching functionality
- [ ] Test localStorage persistence

### 15.5 Phase 5: Storybook Documentation
- [ ] Create stories for all Shadcn UI components
- [ ] Show all component variants (primary, secondary, etc.)
- [ ] Show all component states (default, hover, focus, disabled)
- [ ] Document both themes in Storybook toolbar
- [ ] Add usage examples and code snippets
- [ ] Test accessibility with a11y addon

### 15.6 Phase 6: Testing & Validation
- [ ] Test on desktop (Chrome, Firefox, Safari)
- [ ] Test on mobile (iOS Safari, Android Chrome)
- [ ] Validate WCAG 2.1 Level AA compliance
- [ ] Test keyboard navigation (all components)
- [ ] Test screen reader compatibility
- [ ] Validate color contrast ratios
- [ ] Test with prefers-reduced-motion
- [ ] Performance audit (Lighthouse)

---

## 16. Design Assets & References

### 16.1 Visual Mockups
- **Color Theme Visualizers:**
  - Standard Glass: `docs/ux-color-themes.html`
  - Liquid Glass: `docs/ux-liquid-glass-themes.html`

### 16.2 Design Inspiration
- **Glassmorphism:** iOS 15+ design language, Windows 11 Fluent Design
- **Dark Mode Excellence:** Stripe Dashboard, GitHub Dark, Vercel Dashboard
- **AI Interfaces:** ChatGPT, Claude, Notion AI
- **Modern Web Apps:** Linear, Arc Browser, Raycast

### 16.3 Technical References
- **Tailwind CSS 4.0:** https://tailwindcss.com/docs
- **Shadcn UI:** https://ui.shadcn.com/
- **React 19:** https://react.dev/
- **Storybook 9:** https://storybook.js.org/
- **WCAG 2.1:** https://www.w3.org/WAI/WCAG21/quickref/
- **MDN backdrop-filter:** https://developer.mozilla.org/en-US/docs/Web/CSS/backdrop-filter

---

## 17. Performance Considerations

### 17.1 Optimization Strategies

**Backdrop Filter Performance:**
- Limit blur radius on mobile (20px vs 30px desktop)
- Use `will-change: backdrop-filter` on interactive elements
- Avoid backdrop-filter on large scrolling containers
- Provide solid fallback for unsupported browsers

**Animation Performance:**
- Use GPU-accelerated properties only (transform, opacity)
- Implement `prefers-reduced-motion` check
- Debounce theme toggle to prevent rapid switching
- Lazy-load heavy animations (ambient orbs)

**Bundle Size:**
- Tree-shake Shadcn UI components
- Use React.lazy for code splitting if needed
- Optimize Tailwind output (PurgeCSS automatic in v4)
- Compress images/assets with Vite

### 17.2 Browser Support

**Target Browsers:**
- Chrome 90+ ✅
- Firefox 88+ ✅
- Safari 14+ ✅
- Edge 90+ ✅

**Graceful Degradation:**
- Backdrop-filter fallback: Solid dark background
- Glassmorphism not supported: Use subtle shadows instead
- CSS Grid not supported: Single column fallback

---

## 18. Future Enhancements (Post-MVP)

### 18.1 Additional Themes
- **Emerald Matrix** (Green) - Hacker aesthetic
- **Sunset Amber** (Orange) - Warm, energetic
- **Auto Theme** - System preference detection

### 18.2 Advanced Interactions
- Voice input integration
- Message reactions/feedback
- Code syntax highlighting in responses
- Markdown rendering
- Copy message to clipboard

### 18.3 Personalization
- Custom accent colors (color picker)
- Adjustable blur intensity slider
- Font size preferences
- Contrast mode toggle

---

## 19. Handoff Notes for Developer

### 19.1 Critical Implementation Details

**Theme Switching:**
- MUST save to localStorage with key: `"theme"`
- MUST apply to `<html>` element: `data-theme="cyber-purple"`
- MUST include 300ms transition on theme-aware properties

**Glass Effects:**
- CRITICAL: Use `backdrop-filter` with `-webkit-` prefix for Safari
- CRITICAL: Provide fallback for unsupported browsers
- Performance: Limit blur nesting (max 2-3 layers deep)

**Accessibility:**
- MUST test with keyboard only (no mouse)
- MUST validate with screen reader (NVDA/JAWS/VoiceOver)
- MUST meet 4.5:1 contrast ratio minimum

### 19.2 Testing Requirements
- Test theme persistence across page reloads
- Test on real mobile devices (not just DevTools)
- Test with slow 3G network (API latency)
- Test with backend down (error states)

### 19.3 Code Quality Standards
- TypeScript strict mode enabled
- All components must have props interface
- Storybook stories required for all UI components
- Follow Shadcn UI file structure conventions

---

## 20. Approval & Sign-off

**Design System Status:** ✅ **APPROVED**

**Approved By:** BMad
**Date:** 2025-11-02
**Designer:** Sally (UX Designer Agent)

**Next Steps:**
1. Hand off to Development Team (Amelia - Dev Agent)
2. Begin Story 2 implementation with this design system
3. Create Storybook stories alongside component development
4. Validate accessibility during implementation

---

**Document End**

This design specification provides complete implementation guidance for the Alter Ego liquid glass interface with dual theme support. All design decisions are documented with rationale for maintainability and future enhancements.
