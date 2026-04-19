# Modern React UI Style Guide 2026

A comprehensive guide for building modern, accessible, and performant React applications with Tailwind CSS.

---

## Table of Contents

1. [Modern Tailwind CSS Patterns](#1-modern-tailwind-css-patterns)
2. [Color Palette Recommendations](#2-color-palette-recommendations)
3. [Typography Systems](#3-typography-systems)
4. [Spacing and Layout Systems](#4-spacing-and-layout-systems)
5. [Dark Mode Implementation](#5-dark-mode-implementation)
6. [Design Tokens Approach](#6-design-tokens-approach)
7. [Component Styling with CVA](#7-component-styling-with-cva)
8. [Animation and Transitions](#8-animation-and-transitions)
9. [Mobile-First Responsive Design](#9-mobile-first-responsive-design)
10. [Accessibility-First Styling](#10-accessibility-first-styling)

---

## 1. Modern Tailwind CSS Patterns

### Tailwind CSS v4 Setup (2026)

Tailwind CSS v4 is a complete rewrite with significant improvements:

```css
/* app.css - Tailwind v4 Configuration */
@import "tailwindcss";

/* Custom theme extensions */
@theme {
  /* Custom colors using OKLCH color space */
  --color-primary: oklch(0.65 0.22 267);
  --color-secondary: oklch(0.7 0.15 300);
  
  /* Custom fonts */
  --font-sans: Inter, system-ui, sans-serif;
  --font-display: "Cal Sans", ui-sans-serif, system-ui, sans-serif;
  
  /* Custom spacing */
  --spacing-4-5: 1.125rem;
  --spacing-18: 4.5rem;
  
  /* Custom animations */
  --animate-fade-in: fade-in 0.3s ease-out;
  --animate-slide-up: slide-up 0.4s ease-out;
  
  @keyframes fade-in {
    0% { opacity: 0; }
    100% { opacity: 1; }
  }
  
  @keyframes slide-up {
    0% { opacity: 0; transform: translateY(10px); }
    100% { opacity: 1; transform: translateY(0); }
  }
}

/* Custom variant for dark mode */
@custom-variant dark (&:where(.dark, .dark *));
```

### Best Practices

```tsx
// ✅ Good: Semantic class ordering
<button className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50">
  Submit
</button>

// ✅ Good: Extract repeated patterns to components
// ❌ Bad: Copy-pasting long class strings

// ✅ Good: Use arbitrary values sparingly
<div className="w-[123px]"> /* Only when necessary */ </div>

// ✅ Good: Use the @apply directive for complex components in CSS
@layer components {
  .btn-primary {
    @apply flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/90;
  }
}
```

### Class Ordering Convention (Tailwind Prettier Plugin)

```tsx
// Order: Layout → Flexbox/Grid → Spacing → Sizing → Typography → Visual → Interactivity
<div className="
  /* Layout */
  relative block overflow-hidden
  /* Flexbox & Grid */
  flex flex-col items-center justify-center gap-4
  /* Spacing */
  m-2 p-4 px-6
  /* Sizing */
  h-full w-full min-w-0 max-w-md
  /* Typography */
  text-left text-base font-semibold leading-tight tracking-tight
  /* Visual */
  rounded-xl border-2 border-gray-200 bg-white shadow-lg
  /* Interactivity */
  cursor-pointer select-none transition-all duration-200 ease-out
  /* States */
  hover:border-primary hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-primary/50
  /* Dark mode */
  dark:border-gray-800 dark:bg-gray-900 dark:hover:border-primary
"/>
```

---

## 2. Color Palette Recommendations

### Modern Accessible Color System (OKLCH)

OKLCH is the recommended color space for 2026 - it provides perceptual uniformity and better accessibility.

```css
/* Primary Brand Colors */
:root {
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
}

.dark {
  --color-success: oklch(0.45 0.15 150);
  --color-warning: oklch(0.55 0.12 80);
  --color-error: oklch(0.58 0.25 25);
  --color-info: oklch(0.55 0.14 250);
}
```

### Recommended Color Scales

```css
/* Neutral Scale (Gray) - Most versatile */
--color-gray-50: oklch(0.985 0.002 247);
--color-gray-100: oklch(0.967 0.003 264);
--color-gray-200: oklch(0.928 0.006 264);
--color-gray-300: oklch(0.872 0.01 258);
--color-gray-400: oklch(0.707 0.022 261);
--color-gray-500: oklch(0.551 0.027 264);
--color-gray-600: oklch(0.446 0.03 256);
--color-gray-700: oklch(0.373 0.034 259);
--color-gray-800: oklch(0.278 0.033 256);
--color-gray-900: oklch(0.21 0.034 264);
--color-gray-950: oklch(0.13 0.028 261);

/* Zinc Scale - Slightly warm */
--color-zinc-50: oklch(0.985 0 0);
--color-zinc-100: oklch(0.967 0.001 286);
--color-zinc-200: oklch(0.92 0.004 286);
--color-zinc-300: oklch(0.871 0.006 286);
--color-zinc-400: oklch(0.705 0.015 286);
--color-zinc-500: oklch(0.552 0.016 285);
--color-zinc-600: oklch(0.442 0.017 285);
--color-zinc-700: oklch(0.37 0.013 285);
--color-zinc-800: oklch(0.274 0.006 286);
--color-zinc-900: oklch(0.21 0.006 285);
--color-zinc-950: oklch(0.141 0.005 285);

/* Stone Scale - Earthy/warm */
--color-stone-50: oklch(0.985 0.001 106);
--color-stone-100: oklch(0.97 0.001 106);
--color-stone-200: oklch(0.923 0.003 48);
--color-stone-300: oklch(0.869 0.005 56);
--color-stone-400: oklch(0.709 0.01 56);
--color-stone-500: oklch(0.553 0.013 58);
--color-stone-600: oklch(0.444 0.011 73);
--color-stone-700: oklch(0.374 0.01 67);
--color-stone-800: oklch(0.268 0.007 34);
--color-stone-900: oklch(0.216 0.006 56);
--color-stone-950: oklch(0.147 0.004 49);
```

### Color Usage Guidelines

| Purpose | Light Mode | Dark Mode |
|---------|------------|-----------|
| Background | gray-50 / white | gray-950 / gray-900 |
| Surface | white / gray-50 | gray-900 / gray-800 |
| Text Primary | gray-900 | gray-50 |
| Text Secondary | gray-600 | gray-400 |
| Text Muted | gray-400 | gray-600 |
| Border | gray-200 | gray-800 |
| Border Hover | gray-300 | gray-700 |

---

## 3. Typography Systems

### Recommended Font Pairings

```css
@theme {
  /* Option 1: Modern Sans (Recommended) */
  --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-display: "Cal Sans", "SF Pro Display", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  
  /* Option 2: Geometric (For tech/fintech) */
  --font-sans: "Plus Jakarta Sans", ui-sans-serif, system-ui, sans-serif;
  --font-display: "Space Grotesk", ui-sans-serif, system-ui, sans-serif;
  
  /* Option 3: Editorial (For content-heavy) */
  --font-sans: "DM Sans", ui-sans-serif, system-ui, sans-serif;
  --font-display: "DM Serif Display", Georgia, ui-serif, serif;
  --font-body: "Source Serif 4", Georgia, ui-serif, serif;
  
  /* Option 4: Swiss/Minimal (High-end products) */
  --font-sans: "Switzer", "Helvetica Neue", Arial, sans-serif;
  --font-display: "General Sans", "Helvetica Neue", Arial, sans-serif;
}
```

### Modern Type Scale

```css
@theme {
  /* Fluid Type Scale (using clamp) */
  --text-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.8125rem);
  --text-xs--line-height: calc(1 / 0.75);
  --text-xs--letter-spacing: 0.01em;
  
  --text-sm: clamp(0.8125rem, 0.75rem + 0.3vw, 0.875rem);
  --text-sm--line-height: calc(1.25 / 0.875);
  --text-sm--letter-spacing: 0em;
  
  --text-base: clamp(0.9375rem, 0.875rem + 0.3vw, 1rem);
  --text-base--line-height: 1.5;
  --text-base--letter-spacing: 0em;
  
  --text-lg: clamp(1.0625rem, 0.95rem + 0.55vw, 1.125rem);
  --text-lg--line-height: calc(1.75 / 1.125);
  --text-lg--letter-spacing: -0.01em;
  
  --text-xl: clamp(1.125rem, 0.975rem + 0.75vw, 1.25rem);
  --text-xl--line-height: calc(1.75 / 1.25);
  --text-xl--letter-spacing: -0.01em;
  
  --text-2xl: clamp(1.25rem, 1rem + 1.25vw, 1.5rem);
  --text-2xl--line-height: calc(2 / 1.5);
  --text-2xl--letter-spacing: -0.02em;
  
  --text-3xl: clamp(1.5rem, 1.125rem + 1.875vw, 1.875rem);
  --text-3xl--line-height: calc(2.25 / 1.875);
  --text-3xl--letter-spacing: -0.02em;
  
  --text-4xl: clamp(1.75rem, 1.25rem + 2.5vw, 2.25rem);
  --text-4xl--line-height: calc(2.5 / 2.25);
  --text-4xl--letter-spacing: -0.03em;
  
  --text-5xl: clamp(2rem, 1.25rem + 3.75vw, 3rem);
  --text-5xl--line-height: 1.1;
  --text-5xl--letter-spacing: -0.03em;
  
  --text-6xl: clamp(2.5rem, 1.5rem + 5vw, 3.75rem);
  --text-6xl--line-height: 1.05;
  --text-6xl--letter-spacing: -0.04em;
  
  --text-7xl: clamp(3rem, 1.75rem + 6.25vw, 4.5rem);
  --text-7xl--line-height: 1;
  --text-7xl--letter-spacing: -0.04em;
  
  --text-8xl: clamp(3.5rem, 1.5rem + 10vw, 6rem);
  --text-8xl--line-height: 1;
  --text-8xl--letter-spacing: -0.05em;
  
  --text-9xl: clamp(4rem, 1rem + 15vw, 8rem);
  --text-9xl--line-height: 1;
  --text-9xl--letter-spacing: -0.05em;
}
```

### Typography Component Examples

```tsx
// components/ui/typography.tsx
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const headingVariants = cva("font-display tracking-tight", {
  variants: {
    size: {
      h1: "text-5xl font-bold leading-tight",
      h2: "text-4xl font-semibold leading-tight",
      h3: "text-3xl font-semibold leading-snug",
      h4: "text-2xl font-semibold leading-snug",
      h5: "text-xl font-medium leading-snug",
      h6: "text-lg font-medium leading-snug",
    },
    color: {
      default: "text-foreground",
      muted: "text-muted-foreground",
      primary: "text-primary",
    },
  },
  defaultVariants: {
    size: "h1",
    color: "default",
  },
});

const textVariants = cva("font-sans", {
  variants: {
    size: {
      xs: "text-xs leading-relaxed",
      sm: "text-sm leading-relaxed",
      base: "text-base leading-relaxed",
      lg: "text-lg leading-relaxed",
      xl: "text-xl leading-relaxed",
    },
    weight: {
      normal: "font-normal",
      medium: "font-medium",
      semibold: "font-semibold",
      bold: "font-bold",
    },
    color: {
      default: "text-foreground",
      muted: "text-muted-foreground",
      primary: "text-primary",
      destructive: "text-destructive",
    },
  },
  defaultVariants: {
    size: "base",
    weight: "normal",
    color: "default",
  },
});

interface HeadingProps 
  extends React.HTMLAttributes<HTMLHeadingElement>,
    VariantProps<typeof headingVariants> {
  as?: "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
}

export function Heading({
  className,
  size,
  color,
  as: Component = "h1",
  ...props
}: HeadingProps) {
  return (
    <Component
      className={cn(headingVariants({ size, color }), className)}
      {...props}
    />
  );
}

interface TextProps
  extends React.HTMLAttributes<HTMLParagraphElement>,
    VariantProps<typeof textVariants> {}

export function Text({
  className,
  size,
  weight,
  color,
  ...props
}: TextProps) {
  return (
    <p
      className={cn(textVariants({ size, weight, color }), className)}
      {...props}
    />
  );
}
```

### Typography Usage

```tsx
// Example usage
<Heading size="h1" color="default">
  Main Page Title
</Heading>

<Heading as="h2" size="h2" color="muted">
  Section Subtitle
</Heading>

<Text size="lg" weight="medium" color="default">
  Lead paragraph with larger text for introductions.
</Text>

<Text size="base" color="muted">
  Body text with comfortable reading experience and muted color for secondary content.
</Text>

<Text size="sm" color="muted">
  Small text for captions, metadata, and supporting information.
</Text>
```

---

## 4. Spacing and Layout Systems

### Spacing Scale

```css
@theme {
  /* 4px base unit */
  --spacing-0: 0;
  --spacing-0-5: 0.125rem;  /* 2px */
  --spacing-1: 0.25rem;     /* 4px */
  --spacing-1-5: 0.375rem;  /* 6px */
  --spacing-2: 0.5rem;      /* 8px */
  --spacing-2-5: 0.625rem;  /* 10px */
  --spacing-3: 0.75rem;     /* 12px */
  --spacing-3-5: 0.875rem;  /* 14px */
  --spacing-4: 1rem;        /* 16px */
  --spacing-5: 1.25rem;     /* 20px */
  --spacing-6: 1.5rem;      /* 24px */
  --spacing-7: 1.75rem;     /* 28px */
  --spacing-8: 2rem;        /* 32px */
  --spacing-9: 2.25rem;     /* 36px */
  --spacing-10: 2.5rem;     /* 40px */
  --spacing-11: 2.75rem;    /* 44px */
  --spacing-12: 3rem;       /* 48px */
  --spacing-14: 3.5rem;     /* 56px */
  --spacing-16: 4rem;       /* 64px */
  --spacing-20: 5rem;       /* 80px */
  --spacing-24: 6rem;       /* 96px */
  --spacing-28: 7rem;       /* 112px */
  --spacing-32: 8rem;       /* 128px */
  --spacing-36: 9rem;       /* 144px */
  --spacing-40: 10rem;      /* 160px */
  --spacing-44: 11rem;      /* 176px */
  --spacing-48: 12rem;      /* 192px */
  --spacing-52: 13rem;      /* 208px */
  --spacing-56: 14rem;      /* 224px */
  --spacing-60: 15rem;      /* 240px */
  --spacing-64: 16rem;      /* 256px */
  --spacing-72: 18rem;      /* 288px */
  --spacing-80: 20rem;      /* 320px */
  --spacing-96: 24rem;      /* 384px */
}
```

### Container System

```css
@theme {
  /* Container widths */
  --container-3xs: 16rem;   /* 256px */
  --container-2xs: 18rem;   /* 288px */
  --container-xs: 20rem;    /* 320px */
  --container-sm: 24rem;    /* 384px */
  --container-md: 28rem;    /* 448px */
  --container-lg: 32rem;    /* 512px */
  --container-xl: 36rem;    /* 576px */
  --container-2xl: 42rem;   /* 672px */
  --container-3xl: 48rem;   /* 768px */
  --container-4xl: 56rem;   /* 896px */
  --container-5xl: 64rem;   /* 1024px */
  --container-6xl: 72rem;   /* 1152px */
  --container-7xl: 80rem;   /* 1280px */
  --container-prose: 65ch;  /* Optimal reading width */
}
```

### Layout Components

```tsx
// components/ui/container.tsx
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const containerVariants = cva("mx-auto w-full px-4 sm:px-6 lg:px-8", {
  variants: {
    size: {
      default: "max-w-7xl",
      sm: "max-w-3xl",
      md: "max-w-4xl",
      lg: "max-w-5xl",
      xl: "max-w-6xl",
      "2xl": "max-w-7xl",
      full: "max-w-none",
      prose: "max-w-prose",
    },
  },
  defaultVariants: {
    size: "default",
  },
});

interface ContainerProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof containerVariants> {}

export function Container({ className, size, ...props }: ContainerProps) {
  return (
    <div className={cn(containerVariants({ size }), className)} {...props} />
  );
}

// components/ui/stack.tsx
const stackVariants = cva("flex flex-col", {
  variants: {
    gap: {
      0: "gap-0",
      1: "gap-1",
      2: "gap-2",
      3: "gap-3",
      4: "gap-4",
      5: "gap-5",
      6: "gap-6",
      8: "gap-8",
      10: "gap-10",
      12: "gap-12",
    },
    align: {
      start: "items-start",
      center: "items-center",
      end: "items-end",
      stretch: "items-stretch",
    },
    justify: {
      start: "justify-start",
      center: "justify-center",
      end: "justify-end",
      between: "justify-between",
    },
  },
  defaultVariants: {
    gap: 4,
    align: "stretch",
    justify: "start",
  },
});

interface StackProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof stackVariants> {}

export function Stack({ className, gap, align, justify, ...props }: StackProps) {
  return (
    <div
      className={cn(stackVariants({ gap, align, justify }), className)}
      {...props}
    />
  );
}

// components/ui/grid.tsx
const gridVariants = cva("grid", {
  variants: {
    cols: {
      1: "grid-cols-1",
      2: "grid-cols-2",
      3: "grid-cols-3",
      4: "grid-cols-4",
      5: "grid-cols-5",
      6: "grid-cols-6",
      12: "grid-cols-12",
    },
    gap: {
      0: "gap-0",
      2: "gap-2",
      4: "gap-4",
      6: "gap-6",
      8: "gap-8",
      12: "gap-12",
    },
  },
  defaultVariants: {
    cols: 1,
    gap: 4,
  },
});

interface GridProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof gridVariants> {}

export function Grid({ className, cols, gap, ...props }: GridProps) {
  return <div className={cn(gridVariants({ cols, gap }), className)} {...props} />;
}
```

---

## 5. Dark Mode Implementation

### CSS Variable Approach (Recommended)

```css
/* globals.css */
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

@theme inline {
  /* Semantic color tokens */
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  
  /* Radius */
  --radius-sm: calc(var(--radius) * 0.6);
  --radius-md: calc(var(--radius) * 0.8);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) * 1.4);
  --radius-2xl: calc(var(--radius) * 1.8);
}

:root {
  --radius: 0.625rem;
  
  /* Light mode tokens */
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0 0);
  --secondary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.97 0 0);
  --accent-foreground: oklch(0.205 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --destructive-foreground: oklch(0.985 0 0);
  --border: oklch(0.922 0 0);
  --input: oklch(0.922 0 0);
  --ring: oklch(0.708 0 0);
}

.dark {
  /* Dark mode tokens */
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --card: oklch(0.205 0 0);
  --card-foreground: oklch(0.985 0 0);
  --popover: oklch(0.205 0 0);
  --popover-foreground: oklch(0.985 0 0);
  --primary: oklch(0.922 0 0);
  --primary-foreground: oklch(0.205 0 0);
  --secondary: oklch(0.269 0 0);
  --secondary-foreground: oklch(0.985 0 0);
  --muted: oklch(0.269 0 0);
  --muted-foreground: oklch(0.708 0 0);
  --accent: oklch(0.269 0 0);
  --accent-foreground: oklch(0.985 0 0);
  --destructive: oklch(0.704 0.191 22.216);
  --destructive-foreground: oklch(0.985 0 0);
  --border: oklch(1 0 0 / 10%);
  --input: oklch(1 0 0 / 15%);
  --ring: oklch(0.556 0 0);
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground antialiased;
  }
}
```

### React Theme Provider

```tsx
// components/theme-provider.tsx
"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "dark" | "light" | "system";

type ThemeProviderProps = {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
};

type ThemeProviderState = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resolvedTheme: "light" | "dark";
};

const initialState: ThemeProviderState = {
  theme: "system",
  setTheme: () => null,
  resolvedTheme: "light",
};

const ThemeProviderContext = createContext<ThemeProviderState>(initialState);

export function ThemeProvider({
  children,
  defaultTheme = "system",
  storageKey = "theme",
  ...props
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(defaultTheme);
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const root = window.document.documentElement;
    
    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
    
    const resolved = theme === "system" ? systemTheme : theme;
    
    setResolvedTheme(resolved);
    
    root.classList.remove("light", "dark");
    root.classList.add(resolved);
  }, [theme]);

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem(storageKey) as Theme;
    if (saved) setTheme(saved);
  }, [storageKey]);

  const value = {
    theme,
    setTheme: (theme: Theme) => {
      localStorage.setItem(storageKey, theme);
      setTheme(theme);
    },
    resolvedTheme,
  };

  // Prevent hydration mismatch
  if (!mounted) {
    return <div style={{ visibility: "hidden" }}>{children}</div>;
  }

  return (
    <ThemeProviderContext.Provider {...props} value={value}>
      {children}
    </ThemeProviderContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeProviderContext);
  if (context === undefined)
    throw new Error("useTheme must be used within a ThemeProvider");
  return context;
};
```

### Theme Toggle Component

```tsx
// components/theme-toggle.tsx
"use client";

import { Moon, Sun, Monitor } from "lucide-react";
import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function ThemeToggle() {
  const { setTheme, theme } = useTheme();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme("light")}>
          <Sun className="mr-2 h-4 w-4" />
          Light
          {theme === "light" && <Check className="ml-auto h-4 w-4" />}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("dark")}>
          <Moon className="mr-2 h-4 w-4" />
          Dark
          {theme === "dark" && <Check className="ml-auto h-4 w-4" />}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("system")}>
          <Monitor className="mr-2 h-4 w-4" />
          System
          {theme === "system" && <Check className="ml-auto h-4 w-4" />}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

---

## 6. Design Tokens Approach

### Token Structure

```css
/* tokens/colors.css */
@theme {
  /* Brand Colors */
  --color-brand-50: oklch(0.97 0.02 267);
  --color-brand-100: oklch(0.94 0.04 267);
  --color-brand-200: oklch(0.88 0.08 267);
  --color-brand-300: oklch(0.81 0.12 267);
  --color-brand-400: oklch(0.71 0.18 267);
  --color-brand-500: oklch(0.62 0.23 267);
  --color-brand-600: oklch(0.55 0.26 267);
  --color-brand-700: oklch(0.48 0.24 267);
  --color-brand-800: oklch(0.41 0.20 267);
  --color-brand-900: oklch(0.36 0.16 267);
  --color-brand-950: oklch(0.27 0.12 267);
  
  /* Semantic Mappings */
  --color-background-default: var(--color-gray-50);
  --color-background-elevated: var(--color-white);
  --color-background-pressed: var(--color-gray-100);
  
  --color-foreground-default: var(--color-gray-900);
  --color-foreground-muted: var(--color-gray-600);
  --color-foreground-subtle: var(--color-gray-400);
  --color-foreground-inverse: var(--color-white);
  
  --color-border-default: var(--color-gray-200);
  --color-border-hover: var(--color-gray-300);
  --color-border-active: var(--color-brand-500);
}

/* tokens/spacing.css */
@theme {
  /* Spacing Scale */
  --space-0: 0;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-10: 2.5rem;
  --space-12: 3rem;
  --space-16: 4rem;
  --space-20: 5rem;
  --space-24: 6rem;
  
  /* Semantic Spacing */
  --space-page-padding: var(--space-4);
  --space-section-gap: var(--space-16);
  --space-component-gap: var(--space-6);
  --space-element-gap: var(--space-4);
}

/* tokens/typography.css */
@theme {
  /* Font Families */
  --font-family-sans: Inter, system-ui, sans-serif;
  --font-family-display: "Cal Sans", Inter, system-ui, sans-serif;
  --font-family-mono: "JetBrains Mono", monospace;
  
  /* Font Sizes */
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 1.875rem;
  --font-size-4xl: 2.25rem;
  
  /* Font Weights */
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  
  /* Line Heights */
  --line-height-tight: 1.25;
  --line-height-snug: 1.375;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.625;
  
  /* Letter Spacing */
  --letter-spacing-tight: -0.02em;
  --letter-spacing-normal: 0;
  --letter-spacing-wide: 0.01em;
}

/* tokens/elevation.css */
@theme {
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-base: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
  --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
  --shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
  
  /* Dark Mode Shadows */
  --shadow-sm-dark: 0 1px 2px 0 rgb(0 0 0 / 0.3);
  --shadow-base-dark: 0 1px 3px 0 rgb(0 0 0 / 0.4), 0 1px 2px -1px rgb(0 0 0 / 0.4);
}

/* tokens/radius.css */
@theme {
  --radius-none: 0;
  --radius-xs: 0.125rem;
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  --radius-2xl: 1rem;
  --radius-3xl: 1.5rem;
  --radius-full: 9999px;
  
  /* Semantic */
  --radius-component: var(--radius-lg);
  --radius-button: var(--radius-md);
  --radius-card: var(--radius-xl);
  --radius-input: var(--radius-md);
}

/* tokens/animation.css */
@theme {
  /* Durations */
  --duration-instant: 0ms;
  --duration-fast: 100ms;
  --duration-normal: 150ms;
  --duration-slow: 300ms;
  --duration-slower: 500ms;
  
  /* Easings */
  --ease-linear: linear;
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  
  /* Animations */
  --animate-fade-in: fade-in var(--duration-normal) var(--ease-out);
  --animate-fade-out: fade-out var(--duration-fast) var(--ease-in);
  --animate-scale-in: scale-in var(--duration-normal) var(--ease-spring);
  --animate-slide-up: slide-up var(--duration-normal) var(--ease-out);
  --animate-slide-down: slide-down var(--duration-normal) var(--ease-out);
  
  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  @keyframes fade-out {
    from { opacity: 1; }
    to { opacity: 0; }
  }
  
  @keyframes scale-in {
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
  }
  
  @keyframes slide-up {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  @keyframes slide-down {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
  }
}
```

### Token Usage Examples

```tsx
// Using design tokens in components
<button className="
  /* Colors */
  bg-primary text-primary-foreground
  /* Spacing */
  px-4 py-2
  /* Typography */
  text-sm font-medium
  /* Visual */
  rounded-md
  /* Interactions */
  transition-colors duration-normal ease-out
  hover:bg-primary/90
  focus:ring-2 focus:ring-ring focus:ring-offset-2
  disabled:opacity-50 disabled:cursor-not-allowed
">
  Button Text
</button>
```

---

## 7. Component Styling with CVA

### CVA Setup

```bash
npm install class-variance-authority clsx tailwind-merge
```

```ts
// lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### Button Component with CVA

```tsx
// components/ui/button.tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Slot } from "@radix-ui/react-slot";

const buttonVariants = cva(
  // Base styles
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        xs: "h-7 rounded-md px-2 text-xs gap-1 [&_svg]:size-3",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-11 rounded-md px-8 text-base",
        xl: "h-12 rounded-lg px-10 text-base",
        icon: "h-10 w-10",
        "icon-sm": "h-8 w-8",
        "icon-lg": "h-11 w-11",
      },
      radius: {
        default: "rounded-md",
        none: "rounded-none",
        sm: "rounded-sm",
        lg: "rounded-lg",
        xl: "rounded-xl",
        full: "rounded-full",
      },
      width: {
        default: "w-auto",
        full: "w-full",
        min: "min-w-fit",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      radius: "default",
      width: "default",
    },
    compoundVariants: [
      {
        variant: "link",
        size: ["icon", "icon-sm", "icon-lg"],
        className: "h-auto w-auto p-0",
      },
    ],
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    className, 
    variant, 
    size, 
    radius,
    width,
    asChild = false, 
    isLoading = false,
    children,
    disabled,
    ...props 
  }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, radius, width }), className)}
        ref={ref}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && (
          <Loader2 className="animate-spin" />
        )}
        {children}
      </Comp>
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

### Input Component with CVA

```tsx
// components/ui/input.tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const inputVariants = cva(
  "flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "",
        filled: "border-transparent bg-muted/50 focus-visible:bg-background",
        flushed: "rounded-none border-0 border-b border-input px-0 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-primary",
      },
      size: {
        default: "h-10",
        sm: "h-8 px-2 text-xs",
        lg: "h-12 px-4 text-base",
        xl: "h-14 px-4 text-lg",
      },
      state: {
        default: "",
        error: "border-destructive focus-visible:ring-destructive",
        success: "border-green-500 focus-visible:ring-green-500",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      state: "default",
    },
  }
);

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size">,
    VariantProps<typeof inputVariants> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, variant, size, state, ...props }, ref) => {
    return (
      <input
        className={cn(inputVariants({ variant, size, state }), className)}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input, inputVariants };
```

### Card Component with CVA

```tsx
// components/ui/card.tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const cardVariants = cva(
  "rounded-xl border bg-card text-card-foreground shadow",
  {
    variants: {
      variant: {
        default: "",
        elevated: "shadow-lg",
        outlined: "shadow-none",
        ghost: "border-transparent bg-transparent shadow-none",
        interactive: "transition-shadow hover:shadow-md cursor-pointer",
      },
      padding: {
        default: "",
        none: "",
        sm: "p-4",
        md: "p-6",
        lg: "p-8",
      },
    },
    defaultVariants: {
      variant: "default",
      padding: "none",
    },
  }
);

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, padding }), className)}
      {...props}
    />
  )
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn("font-semibold leading-none tracking-tight", className)}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
));
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
```

---

## 8. Animation and Transitions

### Motion (Framer Motion) Patterns

```bash
npm install motion
```

```tsx
// components/animations/fade-in.tsx
"use client";

import { motion, type Variants } from "motion/react";
import { type ReactNode } from "react";

interface FadeInProps {
  children: ReactNode;
  delay?: number;
  duration?: number;
  direction?: "up" | "down" | "left" | "right" | "none";
  className?: string;
}

const directionOffset = {
  up: { y: 20 },
  down: { y: -20 },
  left: { x: 20 },
  right: { x: -20 },
  none: {},
};

export function FadeIn({
  children,
  delay = 0,
  duration = 0.5,
  direction = "up",
  className,
}: FadeInProps) {
  return (
    <motion.div
      initial={{ opacity: 0, ...directionOffset[direction] }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{
        duration,
        delay,
        ease: [0.25, 0.1, 0.25, 1],
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// Stagger container for lists
interface StaggerContainerProps {
  children: ReactNode;
  staggerDelay?: number;
  className?: string;
}

export function StaggerContainer({
  children,
  staggerDelay = 0.1,
  className,
}: StaggerContainerProps) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: {
          transition: {
            staggerChildren: staggerDelay,
          },
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 20 },
        visible: { 
          opacity: 1, 
          y: 0,
          transition: {
            duration: 0.5,
            ease: [0.25, 0.1, 0.25, 1],
          },
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
```

### Hover and Tap Animations

```tsx
// components/animations/interactive.tsx
"use client";

import { motion } from "motion/react";
import { type ReactNode } from "react";

interface ScaleOnHoverProps {
  children: ReactNode;
  scale?: number;
  className?: string;
}

export function ScaleOnHover({
  children,
  scale = 1.02,
  className,
}: ScaleOnHoverProps) {
  return (
    <motion.div
      whileHover={{ scale }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.2 }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

interface PressableProps {
  children: ReactNode;
  className?: string;
}

export function Pressable({ children, className }: PressableProps) {
  return (
    <motion.div
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.97 }}
      transition={{ 
        type: "spring", 
        stiffness: 400, 
        damping: 17 
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
```

### Page Transitions

```tsx
// components/animations/page-transition.tsx
"use client";

import { motion, AnimatePresence } from "motion/react";
import { usePathname } from "next/navigation";
import { type ReactNode } from "react";

interface PageTransitionProps {
  children: ReactNode;
}

export function PageTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{
          duration: 0.3,
          ease: [0.25, 0.1, 0.25, 1],
        }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
```

### CSS Transition Utilities

```css
@theme {
  /* Transitions */
  --transition-base: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-smooth: 300ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-spring: 400ms cubic-bezier(0.34, 1.56, 0.64, 1);
  
  /* Predefined transitions */
  --transition-colors: color, background-color, border-color, outline-color, text-decoration-color, fill, stroke;
  --transition-transform: transform, translate, scale, rotate;
  --transition-opacity: opacity;
  --transition-shadow: box-shadow;
}
```

### Best Practices for Animations

```tsx
// ✅ Good: Respect reduced motion preferences
"use client";

import { motion } from "motion/react";

function AnimatedComponent() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      // Reduced motion support
      {...(typeof window !== "undefined" && 
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? { initial: false }
        : {}
      )}
    >
      Content
    </motion.div>
  );
}

// ✅ Good: Use transform and opacity for smooth 60fps animations
// ✅ Good: Limit simultaneous animations
// ✅ Good: Use will-change sparingly
// ✅ Good: Test on low-end devices
```

---

## 9. Mobile-First Responsive Design

### Breakpoint Strategy

```css
@theme {
  /* Default Tailwind breakpoints */
  --breakpoint-sm: 40rem;   /* 640px */
  --breakpoint-md: 48rem;   /* 768px */
  --breakpoint-lg: 64rem;   /* 1024px */
  --breakpoint-xl: 80rem;   /* 1280px */
  --breakpoint-2xl: 96rem;  /* 1536px */
  
  /* Extended breakpoints for 2026 */
  --breakpoint-3xl: 120rem; /* 1920px - Large monitors */
  --breakpoint-xs: 30rem;   /* 480px - Small phones */
}
```

### Responsive Patterns

```tsx
// ✅ Good: Mobile-first approach
// Start with mobile styles, then add breakpoints for larger screens

function ResponsiveLayout() {
  return (
    <div className="
      /* Base: Mobile (0px+) */
      grid grid-cols-1 gap-4 p-4
      /* Small (640px+) */
      sm:grid-cols-2 sm:gap-6 sm:p-6
      /* Medium (768px+) */
      md:grid-cols-3 md:gap-8
      /* Large (1024px+) */
      lg:grid-cols-4 lg:p-8
      /* Extra Large (1280px+) */
      xl:gap-10
      /* 2XL (1536px+) */
      2xl:max-w-7xl 2xl:mx-auto
    ">
      {/* Content */}
    </div>
  );
}

// Responsive typography
function ResponsiveHeading() {
  return (
    <h1 className="
      text-2xl
      sm:text-3xl
      md:text-4xl
      lg:text-5xl
      xl:text-6xl
      font-bold
      tracking-tight
    ">
      Responsive Heading
    </h1>
  );
}

// Responsive navigation
function ResponsiveNav() {
  return (
    <nav>
      {/* Mobile: Hamburger menu */}
      <button className="lg:hidden">
        <MenuIcon />
      </button>
      
      {/* Desktop: Full navigation */}
      <ul className="hidden lg:flex lg:gap-8">
        <li>Home</li>
        <li>About</li>
        <li>Contact</li>
      </ul>
    </nav>
  );
}
```

### Container Query Pattern (Modern Alternative)

```css
@theme {
  /* Container query sizes */
  --container-xs: 20rem;
  --container-sm: 24rem;
  --container-md: 28rem;
  --container-lg: 32rem;
  --container-xl: 36rem;
  --container-2xl: 42rem;
}
```

```tsx
// Using container queries for component-level responsiveness
function CardGrid() {
  return (
    <div className="@container">
      <div className="
        grid gap-4
        /* Based on container width, not viewport */
        @xs:grid-cols-1
        @sm:grid-cols-2
        @md:grid-cols-3
        @lg:grid-cols-4
      ">
        {/* Cards */}
      </div>
    </div>
  );
}
```

### Touch Target Guidelines

```css
/* Minimum touch target size: 44px × 44px (Apple) or 48px × 48px (Material) */
.touch-target {
  @apply min-h-11 min-w-11; /* 44px minimum */
  @apply p-3; /* Comfortable padding */
}

/* Larger touch targets for primary actions */
.touch-target-lg {
  @apply min-h-12 min-w-12; /* 48px minimum */
  @apply p-4;
}

/* Spacing between touch targets */
.touch-group > * + * {
  @apply ml-2;
}
```

### Responsive Spacing Scale

```css
@theme {
  /* Fluid spacing that scales with viewport */
  --spacing-fluid-4: clamp(1rem, 0.8rem + 1vw, 1.5rem);
  --spacing-fluid-6: clamp(1.5rem, 1.2rem + 1.5vw, 2.25rem);
  --spacing-fluid-8: clamp(2rem, 1.5rem + 2.5vw, 3rem);
  --spacing-fluid-12: clamp(3rem, 2rem + 5vw, 4.5rem);
  --spacing-fluid-16: clamp(4rem, 2.5rem + 7.5vw, 6rem);
  --spacing-fluid-20: clamp(5rem, 3rem + 10vw, 7.5rem);
  --spacing-fluid-24: clamp(6rem, 3.5rem + 12.5vw, 9rem);
}
```

---

## 10. Accessibility-First Styling

### Focus Management

```css
@layer base {
  /* Visible focus indicators */
  :focus-visible {
    @apply outline-none ring-2 ring-ring ring-offset-2 ring-offset-background;
  }
  
  /* Skip link */
  .skip-link {
    @apply sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md;
  }
}
```

### Screen Reader Utilities

```css
@layer utilities {
  /* Visually hidden but accessible to screen readers */
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  
  /* Show element when focused */
  .not-sr-only {
    position: static;
    width: auto;
    height: auto;
    padding: 0;
    margin: 0;
    overflow: visible;
    clip: auto;
    white-space: normal;
  }
}
```

### Accessible Form Patterns

```tsx
// components/ui/form-field.tsx
interface FormFieldProps {
  label: string;
  error?: string;
  helperText?: string;
  children: React.ReactNode;
  required?: boolean;
}

export function FormField({
  label,
  error,
  helperText,
  children,
  required,
}: FormFieldProps) {
  const id = React.useId();
  const errorId = `${id}-error`;
  const helperId = `${id}-helper`;
  
  return (
    <div className="space-y-2">
      <label
        htmlFor={id}
        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
      >
        {label}
        {required && <span className="text-destructive ml-1" aria-hidden="true">*</span>}
      </label>
      
      {React.cloneElement(children as React.ReactElement, {
        id,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": error ? errorId : helperText ? helperId : undefined,
        "aria-required": required,
      })}
      
      {helperText && !error && (
        <p id={helperId} className="text-sm text-muted-foreground">
          {helperText}
        </p>
      )}
      
      {error && (
        <p id={errorId} className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
```

### Color Contrast Guidelines

```css
/* Minimum contrast ratios:
   - Normal text: 4.5:1
   - Large text (18pt+): 3:1
   - UI components: 3:1
*/

/* Safe color combinations */
.text-on-light {
  /* Contrast ratio > 4.5:1 on light backgrounds */
  @apply text-gray-900; /* 16.1:1 on white */
  @apply text-gray-600; /* 6.3:1 on white */
}

.text-on-dark {
  /* Contrast ratio > 4.5:1 on dark backgrounds */
  @apply text-white; /* 16.1:1 on gray-900 */
  @apply text-gray-300; /* 8.5:1 on gray-900 */
}

/* Error states with sufficient contrast */
.text-error {
  @apply text-red-600; /* 5.4:1 on white */
  @apply dark:text-red-400; /* 5.6:1 on gray-900 */
}
```

### Motion Preferences

```tsx
// components/animations/respect-motion.tsx
"use client";

import { motion, useReducedMotion } from "motion/react";
import { type ReactNode } from "react";

interface RespectMotionProps {
  children: ReactNode;
}

export function RespectMotion({ children }: RespectMotionProps) {
  const shouldReduceMotion = useReducedMotion();
  
  return (
    <motion.div
      initial={shouldReduceMotion ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: shouldReduceMotion ? 0 : 0.3 }}
    >
      {children}
    </motion.div>
  );
}
```

### CSS for Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* Or use Tailwind's motion variants */
.motion-safe\:animate-fade {
  @media (prefers-reduced-motion: no-preference) {
    animation: fade-in 0.3s ease-out;
  }
}

.motion-reduce\:transform-none {
  @media (prefers-reduced-motion: reduce) {
    transform: none !important;
  }
}
```

### Semantic HTML Patterns

```tsx
// ✅ Good: Proper heading hierarchy
<article>
  <header>
    <h1>Main Article Title</h1>
    <p>Published on <time dateTime="2026-01-15">January 15, 2026</time></p>
  </header>
  
  <section aria-labelledby="section-1">
    <h2 id="section-1">First Section</h2>
    <p>Content...</p>
  </section>
  
  <section aria-labelledby="section-2">
    <h2 id="section-2">Second Section</h2>
    <p>Content...</p>
  </section>
</article>

// ✅ Good: Accessible navigation
<nav aria-label="Main">
  <ul role="menubar">
    <li role="none">
      <a href="/" role="menuitem" aria-current="page">Home</a>
    </li>
  </ul>
</nav>

// ✅ Good: Accessible button
<button
  type="button"
  aria-expanded={isOpen}
  aria-controls="menu-panel"
  aria-haspopup="true"
>
  Menu
  <ChevronIcon aria-hidden="true" className={isOpen ? "rotate-180" : ""} />
</button>
<div id="menu-panel" role="region" aria-label="Menu panel" hidden={!isOpen}>
  {/* Menu content */}
</div>
```

### ARIA Landmarks

```tsx
function App() {
  return (
    <div className="min-h-screen">
      {/* Skip to main content link */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      
      <header role="banner">
        <nav role="navigation" aria-label="Main">
          {/* Navigation */}
        </nav>
      </header>
      
      <main id="main-content" role="main" tabIndex={-1}>
        {/* Main content */}
      </main>
      
      <aside role="complementary" aria-label="Related content">
        {/* Sidebar content */}
      </aside>
      
      <footer role="contentinfo">
        {/* Footer content */}
      </footer>
    </div>
  );
}
```

---

## Quick Reference

### Common Patterns Cheat Sheet

```tsx
// Button with all variants
<Button variant="default" size="default">Default</Button>
<Button variant="destructive">Destructive</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="link">Link</Button>

// Input states
<Input placeholder="Default" />
<Input state="error" placeholder="Error state" />
<Input state="success" placeholder="Success state" />
<Input disabled placeholder="Disabled" />

// Container sizes
<Container size="sm">Small container</Container>
<Container size="md">Medium container</Container>
<Container size="lg">Large container</Container>
<Container size="prose">Prose width</Container>

// Spacing utilities
<div className="space-y-4">Vertical stack</div>
<div className="space-x-4">Horizontal stack</div>
<div className="gap-4">Grid gap</div>

// Responsive patterns
<div className="hidden md:block">Desktop only</div>
<div className="md:hidden">Mobile only</div>
<div className="text-sm md:text-base lg:text-lg">Responsive text</div>

// Dark mode
<div className="bg-white dark:bg-gray-900">
<div className="text-gray-900 dark:text-gray-100">
<div className="border-gray-200 dark:border-gray-800">
```

### File Structure

```
app/
├── globals.css           # Global styles, Tailwind imports
├── layout.tsx           # Root layout with theme provider
components/
├── ui/                  # Reusable UI components
│   ├── button.tsx
│   ├── input.tsx
│   ├── card.tsx
│   ├── typography.tsx
│   ├── container.tsx
│   ├── stack.tsx
│   └── grid.tsx
├── theme-provider.tsx   # Theme context
├── theme-toggle.tsx     # Theme toggle button
└── animations/          # Animation components
    ├── fade-in.tsx
    ├── stagger.tsx
    └── page-transition.tsx
lib/
└── utils.ts             # cn() utility
hooks/
└── use-media-query.ts   # Responsive hooks
styles/
├── tokens/
│   ├── colors.css
│   ├── spacing.css
│   ├── typography.css
│   ├── elevation.css
│   ├── radius.css
│   └── animation.css
└── utilities/
    ├── focus.css
    ├── sr-only.css
    └── touch-targets.css
```

---

## Recommended Resources

### Fonts (Google Fonts)
- **Inter** - Primary sans-serif (highly recommended)
- **Cal Sans** - Display font
- **Plus Jakarta Sans** - Geometric alternative
- **DM Sans** - Modern grotesque
- **JetBrains Mono** - Developer-focused monospace
- **Source Serif 4** - Reading-optimized serif

### Tools
- **Tailwind CSS IntelliSense** - VS Code extension
- **Headless UI** - Unstyled accessible components
- **Radix UI** - Low-level accessible primitives
- **shadcn/ui** - Copy-paste component collection
- **CVA** - Class variance authority
- **clsx + tailwind-merge** - Conditional class merging

### Documentation
- [Tailwind CSS v4 Docs](https://tailwindcss.com/docs)
- [CVA Documentation](https://cva.style/docs)
- [shadcn/ui Theming](https://ui.shadcn.com/docs/theming)
- [Radix UI Themes](https://www.radix-ui.com/themes)
- [Motion (Framer Motion)](https://motion.dev)
- [Web.dev Accessibility](https://web.dev/accessibility)

---

*This style guide is a living document. Update it as your project evolves and new best practices emerge.*
