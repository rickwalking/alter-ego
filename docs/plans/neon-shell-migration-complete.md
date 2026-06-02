# Neon Shell Migration: Complete Plan with Atomic Design Architecture

**Status**: Draft
**Branch**: `design-implementation`
**Last Updated**: 2026-05-28

---

## Table of Contents

1. [Architecture Decisions](#1-architecture-decisions)
2. [Atomic Design Classification & Page Mapping](#2-atomic-design-classification--page-mapping)
3. [Component Specifications with Zod Schemas](#3-component-specifications-with-zod-schemas)
4. [Theming Architecture](#4-theming-architecture)
5. [Storybook Integration](#5-storybook-integration)
6. [Testing Strategy & Gherkin Scenarios](#6-testing-strategy--gherkin-scenarios)
7. [Phase 0: Foundation — Design Tokens + Shared Components](#7-phase-0-foundation)
8. [Phase 1: Refactor Converted Pages to Shared Components](#8-phase-1-refactor-converted-pages)
9. [Phase 2: Convert Analytics Page](#9-phase-2-convert-analytics)
10. [Phase 3: Convert Knowledge Pages](#10-phase-3-convert-knowledge)
11. [Phase 4: Convert Blog Edit Page](#11-phase-4-convert-blog-edit)
12. [Phase 5: Convert Feature Components](#12-phase-5-convert-feature-components)
13. [Phase 6: Cleanup — Remove Old Components + Orphan Code](#13-phase-6-cleanup)
14. [Cross-Cutting Concerns](#14-cross-cutting-concerns)
15. [Appendix: Component Usage Map](#15-appendix-component-usage-map)

---

## 1. Architecture Decisions

### 1.1 Design Methodology: Atomic Design (Brad Frost)

| Level | Definition | Neon Shell Examples |
|---|---|---|
| **Atoms** | Basic HTML elements, can't be broken further | `NeonButton`, `NeonInput`, `NeonBadge`, `NeonIcon`, `NeonSpinner`, `NeonSelect`, `NeonTextarea`, `NeonLabel`, `NeonSkeleton`, `NeonLink` |
| **Molecules** | Groups of atoms working as a unit | `NeonCard`, `NeonFormField`, `NeonSearchBar`, `NeonStatCard`, `NeonProgressBar`, `NeonBadgeGroup`, `NeonToast`, `NeonModal`, `NeonDropdown`, `NeonTab` (compound) |
| **Organisms** | Complex sections of molecules/atoms | `NeonSidebar`, `NeonTopBar`, `NeonBreadcrumb`, `NeonStatsGrid`, `NeonActivityList`, `NeonKanbanBoard`, `NeonPersonaCard`, `NeonRubricCard`, `NeonBlogPostCard`, `NeonPagination`, `NeonGridBackground`, `NeonScanlineOverlay` |
| **Templates** | Page-level layouts | `DashboardLayout`, `PublicLayout`, `LoginLayout` |
| **Pages** | Specific instances with real content | `dashboard/page.tsx`, `dashboard/analytics/page.tsx`, etc. |

### 1.2 Component Pattern: CVA + Compound Components

**Atoms/Molecules** use **CVA** (`class-variance-authority`) for variant management (matching existing shadcn pattern):
```typescript
import { cva, type VariantProps } from "class-variance-authority";

const neonButtonVariants = cva("inline-flex items-center ...", {
  variants: {
    variant: {
      primary: "bg-gradient-to-r from-[#00d4ff] to-[#0090b0] text-[#060a12]",
      secondary: "border border-[rgba(0,212,255,0.3)] text-[#00d4ff] bg-transparent",
      ghost: "bg-transparent text-[rgba(255,255,255,0.88)] hover:bg-[rgba(0,212,255,0.08)]",
      danger: "bg-gradient-to-r from-[#ef4444] to-[#dc2626] text-white",
    },
    size: { sm: "px-3 py-1.5 text-xs", md: "px-4 py-2 text-sm", lg: "px-6 py-3 text-base" },
  },
  defaultVariants: { variant: "primary", size: "md" },
});
```

**Organisms with shared state** use **Compound Components** (React Context + `useContext`).

### 1.3 Theming Architecture

**CSS Custom Properties** in `globals.css` `@theme` block — enables Tailwind utilities like `text-neon-cyan`.

**TypeScript Constants** in `src/constants/neon.ts` — enables inline style references.

### 1.4 Import Conventions (Path Aliases + Route Groups)

All code in this plan follows these conventions:

**Path aliases** (configured in `tsconfig.json`):
```
"paths": { "@/*": ["./src/*"] }
```

- Cross-directory imports use `@/` prefix: `@/components/ui/neon-button`, `@/features/knowledge/hooks/use-documents`, `@/schemas/neon-card`, `@/constants/neon`
- Same-directory imports use `"./"` prefix: `./neon-button`, `./constants`
- **Never** use `"../"` or `"../../"` — always use `@/` for directory traversal

**Next.js Route Groups** (parenthesized directories):

| Route Group | URL Path | Pages |
|---|---|---|
| `(public)/` | `/` | Landing page |
| `(blog)/` | `/blog`, `/blog/[id]` | Blog listing + detail |
| `(create)/` | `/create`, `/create/[id]`, `/create/[id]/publish` | Carousel creation flow |
| `(admin)/` | `/admin/users` | Admin dashboard |
| (none) | `/dashboard/*` | All dashboard pages |
| (none) | `/login` | Login page |

Dashboard pages (`/dashboard/*`) currently do NOT use a route group — they are directly nested under `src/app/dashboard/`. This is fine because route groups are optional and exist primarily for shared layouts. The `src/app/dashboard/layout.tsx` provides the shared sidebar layout for all dashboard pages.

### 1.5 State Management (Unchanged)
- **TanStack Query** for server state
- **Zod** for validation schemas
- **React hooks** for local state
- **Compound Components** for shared implicit state

### 1.6 Testing Stack
- **Vitest** + **Testing Library** for unit/integration tests
- **Playwright** for E2E tests
- **StrykerJS** for mutation testing (thresholds: break 80%, low 80%, high 90%)
- **Storybook** for visual regression (via Chromatic)

---

## 2. Atomic Design Classification & Page Mapping

### 2.1 Where Each Component Will Be Used

```
ATOMS (10)
├── NeonButton          → Login form, Blog edit, Knowledge, Chat, Analytics, Calendar, All dashboard pages
├── NeonInput           → Login form, Blog edit, Knowledge search, Chat input, Analytics filters
├── NeonTextarea        → Blog edit page, Knowledge document form
├── NeonSelect          → Create carousel form (theme, image preset), Blog filters
├── NeonBadge           → Dashboard stats, Workflow cards, Persona cards, Rubric cards, Blog posts, Calendar events
├── NeonIcon            → Sidebar nav, Stat cards, Quick actions, Activity items, All icon usages
├── NeonSpinner         → All loading states across all pages
├── NeonLabel           → All form labels (Login, Blog edit, Knowledge, Create carousel)
├── NeonSkeleton        → Knowledge loading, Chat loading, Dashboard loading states
├── NeonLink            → Sidebar nav, Public header nav, Blog article links, Footer links

MOLECULES (10)
├── NeonCard            → Dashboard stats, Workflow board, Personas, Rubrics, Blog posts, Calendar, Knowledge
├── NeonFormField       → Login form, Blog edit, Knowledge form, Create carousel form
├── NeonSearchBar       → Personas page (search input), Knowledge page (search)
├── NeonStatCard        → Dashboard page (4 stat cards), Analytics page (stat cards)
├── NeonProgressBar     → Create carousel (7-step progress bar)
├── NeonBadgeGroup      → Blog post tags, Persona skill tags, Rubric evaluation tags
├── NeonToast           → All form submissions (success/error notifications)
├── NeonModal           → Blog edit (image gen modal), Knowledge (document upload confirm)
├── NeonDropdown        → Dashboard top-bar (user menu), Blog edit (more actions)
├── NeonTab (compound)  → Dashboard (potential future), Analytics (potential tab sections)

ORGANISMS (12)
├── NeonSidebar         → Dashboard layout (ALL dashboard pages)
├── NeonTopBar          → Dashboard overview, Analytics, Blog posts, Calendar, Workflow, Personas, Rubrics
├── NeonBreadcrumb      → Dashboard top-bar (ALL dashboard pages)
├── NeonStatsGrid       → Dashboard overview page, Analytics page
├── NeonActivityList    → Dashboard overview page (Recent Activity section)
├── NeonKanbanBoard     → Workflow board page (6-column kanban)
├── NeonPersonaCard     → Personas page (persona profiles grid)
├── NeonRubricCard      → Rubrics page (rubric evaluations grid)
├── NeonBlogPostCard    → Blog posts listing page, Landing page (Latest Posts section)
├── NeonPagination      → Blog posts listing, Knowledge documents list
├── NeonGridBackground  → Dashboard layout, Public layout, Login page
├── NeonScanlineOverlay → Dashboard layout, Public layout, Login page

TEMPLATES (4)
├── DashboardLayout     → ALL dashboard/* routes
├── PublicLayout        → / (landing), /blog/*, /create/* routes
├── LoginLayout         → /login route
```

### 2.2 Component Dependency Graph

```
NeonIcon ────────────────────────────────────────┐
NeonLabel ──────┐                                │
                 ├── NeonFormField                │
NeonInput ───────┘                                │
NeonTextarea ────┘                                │
NeonSelect ──────┘                                │
NeonBadge ───────┬── NeonBadgeGroup               │
                 ├── NeonCard ───── NeonStatCard ──┤
                 │                ── NeonBlogPostCard
                 │                ── NeonPersonaCard
                 │                ── NeonRubricCard
NeonButton ──────┬── NeonToast                    │
                 ├── NeonModal                    │
                 ├── NeonDropdown                 │
                 ├── NeonPagination               │
                 └── NeonTopBar                   │
NeonSpinner ─────┴── (used by all async)          │
NeonSkeleton ────┴── (used by all loading)        │
NeonLink ────────┬── NeonSidebar                  │
                 ├── NeonBreadcrumb               │
                 └── NeonPagination               │
NeonProgressBar ──── Create carousel page         │
NeonTab (compound) ─ Future tabbed sections       │
NeonGridBackground ─┬── DashboardLayout ──────────┘
NeonScanlineOverlay ─┘
```

---

## 3. Component Specifications with Zod Schemas

Following CLAUDE.md rules:
- **Interfaces in their own files** — Zod schemas + inferred types in `src/schemas/`
- **Constants in `src/constants/`**
- **No magic strings** — all extracted to constants
- **Named exports only**

### 3.1 NeonButton

**File**: `src/schemas/neon-button.ts`

```typescript
import { z } from "zod";

// ── Zod Schema ──
export const neonButtonVariantSchema = z.enum(["primary", "secondary", "ghost", "danger"]);
export const neonButtonSizeSchema = z.enum(["sm", "md", "lg"]);
export const neonButtonPropsSchema = z.object({
  variant: neonButtonVariantSchema.default("primary"),
  size: neonButtonSizeSchema.default("md"),
  disabled: z.boolean().default(false),
  loading: z.boolean().default(false),
  fullWidth: z.boolean().default(false),
  type: z.enum(["button", "submit", "reset"]).default("button"),
});

// ── Inferred Types ──
export type NeonButtonVariant = z.infer<typeof neonButtonVariantSchema>;
export type NeonButtonSize = z.infer<typeof neonButtonSizeSchema>;
export type NeonButtonProps = z.infer<typeof neonButtonPropsSchema>;

// ── Default Values ──
export const NEON_BUTTON_DEFAULTS = {
  variant: "primary" as const,
  size: "md" as const,
  disabled: false,
  loading: false,
  fullWidth: false,
  type: "button" as const,
} as const;
```

**File**: `src/components/ui/neon-button.tsx`

```typescript
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { NeonSpinner } from "./neon-spinner";
import type { NeonButtonVariant, NeonButtonSize } from "@/schemas/neon-button";

// ── CVA Variants ──
const neonButtonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00d4ff] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-gradient-to-r from-[#00d4ff] to-[#0090b0] text-[#060a12] shadow-[0_0_16px_rgba(0,212,255,0.15)] hover:shadow-[0_0_24px_rgba(0,212,255,0.25)]",
        secondary: "border border-[rgba(0,212,255,0.3)] text-[#00d4ff] bg-transparent hover:bg-[rgba(0,212,255,0.08)]",
        ghost: "bg-transparent text-[rgba(255,255,255,0.88)] hover:bg-[rgba(0,212,255,0.06)]",
        danger: "bg-gradient-to-r from-[#ef4444] to-[#dc2626] text-white shadow-[0_0_12px_rgba(239,68,68,0.2)]",
      },
      size: {
        sm: "px-3 py-1.5 text-xs h-8",
        md: "px-4 py-2 text-sm h-10",
        lg: "px-6 py-3 text-base h-12",
      },
      fullWidth: {
        true: "w-full",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

// ── Props Interface ──
interface NeonButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof neonButtonVariants> {
  loading?: boolean;
  icon?: ReactNode;
  iconPosition?: "left" | "right";
}

// ── Component ──
export const NeonButton = forwardRef<HTMLButtonElement, NeonButtonProps>(
  ({ className, variant, size, fullWidth, loading, disabled, icon, iconPosition = "left", children, type = "button", ...props }, ref) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        className={cn(neonButtonVariants({ variant, size, fullWidth, className }))}
        aria-disabled={isDisabled}
        aria-busy={loading}
        {...props}
      >
        {loading && <NeonSpinner size="sm" aria-hidden="true" />}
        {!loading && icon && iconPosition === "left" && <span aria-hidden="true">{icon}</span>}
        {children}
        {!loading && icon && iconPosition === "right" && <span aria-hidden="true">{icon}</span>}
      </button>
    );
  },
);
NeonButton.displayName = "NeonButton";

// ── Exports ──
export { NeonButton, neonButtonVariants };
export type { NeonButtonProps };
```

### 3.2 NeonBadge

**File**: `src/schemas/neon-badge.ts`

```typescript
import { z } from "zod";

export const neonBadgeVariantSchema = z.enum(["cyan", "magenta", "teal", "amber", "green", "red"]);
export const neonBadgeSizeSchema = z.enum(["sm", "md"]);

export const neonBadgePropsSchema = z.object({
  variant: neonBadgeVariantSchema.default("cyan"),
  size: neonBadgeSizeSchema.default("md"),
  dot: z.boolean().default(false),
  outline: z.boolean().default(false),
});

export type NeonBadgeVariant = z.infer<typeof neonBadgeVariantSchema>;
export type NeonBadgeSize = z.infer<typeof neonBadgeSizeSchema>;

// Color map (not magic strings)
export const BADGE_COLORS: Record<NeonBadgeVariant, { bg: string; text: string }> = {
  cyan: { bg: "rgba(0,212,255,0.15)", text: "#00d4ff" },
  magenta: { bg: "rgba(255,39,112,0.15)", text: "#ff2770" },
  teal: { bg: "rgba(10,197,168,0.15)", text: "#0ac5a8" },
  amber: { bg: "rgba(245,158,11,0.15)", text: "#f59e0b" },
  green: { bg: "rgba(34,197,94,0.15)", text: "#22c55e" },
  red: { bg: "rgba(239,68,68,0.15)", text: "#ef4444" },
};
```

### 3.3 NeonCard

**File**: `src/schemas/neon-card.ts`

```typescript
import { z } from "zod";

export const neonCardAccentSchema = z.enum(["cyan", "magenta", "teal", "amber", "purple", "none"]);
export const neonCardPaddingSchema = z.enum(["sm", "md", "lg"]);

export const neonCardPropsSchema = z.object({
  accent: neonCardAccentSchema.default("none"),
  hover: z.boolean().default(false),
  padding: neonCardPaddingSchema.default("md"),
  onClick: z.function().args().returns(z.void()).optional(),
});

export type NeonCardAccent = z.infer<typeof neonCardAccentSchema>;
export type NeonCardPadding = z.infer<typeof neonCardPaddingSchema>;

export const CARD_PADDING_MAP: Record<NeonCardPadding, string> = {
  sm: "p-4",
  md: "p-6",
  lg: "p-8",
};

export const CARD_ACCENT_COLORS: Record<Exclude<NeonCardAccent, "none">, string> = {
  cyan: "#00d4ff",
  magenta: "#ff2770",
  teal: "#0ac5a8",
  amber: "#f59e0b",
  purple: "#a855f7",
};
```

### 3.4 NeonFormField

**File**: `src/schemas/neon-form-field.ts`

```typescript
import { z } from "zod";

export const neonFormFieldPropsSchema = z.object({
  label: z.string().min(1, "Label is required"),
  name: z.string().min(1, "Name is required"),
  error: z.string().optional(),
  hint: z.string().optional(),
  required: z.boolean().default(false),
});

export type NeonFormFieldProps = z.infer<typeof neonFormFieldPropsSchema>;
```

### 3.5 NeonStatCard

**File**: `src/schemas/neon-stat-card.ts`

```typescript
import { z } from "zod";

export const statCardTrendSchema = z.enum(["up", "down"]);

export const neonStatCardPropsSchema = z.object({
  label: z.string().min(1),
  value: z.union([z.string(), z.number()]),
  change: z.object({
    value: z.string(),
    trend: statCardTrendSchema,
  }).optional(),
  loading: z.boolean().default(false),
});

export type StatCardTrend = z.infer<typeof statCardTrendSchema>;
export type NeonStatCardProps = z.infer<typeof neonStatCardPropsSchema>;
```

### 3.6 NeonSidebar

**File**: `src/schemas/neon-sidebar.ts`

```typescript
import { z } from "zod";

export const sidebarItemSchema = z.object({
  href: z.string(),
  labelKey: z.string(),    // i18n key
  icon: z.string(),        // SVG path data
  badge: z.string().optional(),
});

export const sidebarSectionSchema = z.object({
  sectionKey: z.string(),  // i18n key
  items: z.array(sidebarItemSchema).min(1),
});

export const neonSidebarPropsSchema = z.object({
  sections: z.array(sidebarSectionSchema).min(1),
});

export type SidebarItem = z.infer<typeof sidebarItemSchema>;
export type SidebarSection = z.infer<typeof sidebarSectionSchema>;
```

### 3.7 NeonKanbanBoard

**File**: `src/schemas/neon-kanban.ts`

```typescript
import { z } from "zod";

export const kanbanCardSchema = z.object({
  id: z.string().uuid(),
  title: z.string().min(1),
  description: z.string(),
  phase: z.string(),
  phaseStatus: z.string(),
  assignee: z.string().optional(),
});

export const kanbanColumnSchema = z.object({
  phase: z.string(),
  status: z.string(),
  count: z.number().int().nonnegative().optional(),
  cards: z.array(kanbanCardSchema),
});

export const neonKanbanPropsSchema = z.object({
  columns: z.array(kanbanColumnSchema).min(1),
});

export type KanbanCard = z.infer<typeof kanbanCardSchema>;
export type KanbanColumn = z.infer<typeof kanbanColumnSchema>;
```

### 3.8 NeonBlogPostCard

**File**: `src/schemas/neon-blog-post-card.ts`

```typescript
import { z } from "zod";

export const neonBlogPostCardPropsSchema = z.object({
  id: z.string().uuid(),
  title: z.string().min(1),
  subtitle: z.string().optional(),
  niche: z.string().optional(),
  imageUrl: z.string().optional(),
  createdAt: z.string().datetime(),
  href: z.string(),
});

export type NeonBlogPostCardProps = z.infer<typeof neonBlogPostCardPropsSchema>;
```

---

## 4. Theming Architecture

### 4.1 CSS Custom Properties — Add to globals.css @theme

```css
@theme {
  /* ── Neon Shell Accent Colors ── */
  --color-neon-cyan: #00d4ff;
  --color-neon-cyan-dim: rgba(0, 212, 255, 0.12);
  --color-neon-magenta: #ff2770;
  --color-neon-magenta-dim: rgba(255, 39, 112, 0.12);
  --color-neon-teal: #0ac5a8;
  --color-neon-teal-dim: rgba(10, 197, 168, 0.12);
  --color-neon-amber: #f59e0b;
  --color-neon-amber-dim: rgba(245, 158, 11, 0.12);
  --color-neon-green: #22c55e;
  --color-neon-red: #ef4444;
  --color-neon-purple: #a855f7;

  /* ── Background Hierarchy ── */
  --color-bg-deep: #060a12;
  --color-bg-surface: #0a0f1e;
  --color-bg-card: #0d1324;
  --color-bg-elevated: #111a30;
  --color-bg-sidebar: #080c18;

  /* ── Text Hierarchy ── */
  --color-text-primary: rgba(255, 255, 255, 0.88);
  --color-text-muted: rgba(255, 255, 255, 0.55);
  --color-text-dim: rgba(255, 255, 255, 0.3);

  /* ── Component Defaults ── */
  --color-neon-card-bg: var(--color-bg-card);
  --color-neon-card-border: rgba(255, 255, 255, 0.06);
  --color-neon-card-hover-border: rgba(0, 212, 255, 0.2);
  --color-neon-input-bg: rgba(6, 10, 18, 0.45);
  --color-neon-input-border: rgba(255, 255, 255, 0.08);
  --color-neon-input-focus-border: #00d4ff;
  --color-neon-sidebar-bg: #080c18;
}
```

### 4.2 TypeScript Color Constants

**File**: `src/constants/neon.ts`

```typescript
/* ── Colors ── */
export const NEON_CYAN = "#00d4ff";
export const NEON_CYAN_DIM = "rgba(0,212,255,0.12)";
export const NEON_MAGENTA = "#ff2770";
export const NEON_MAGENTA_DIM = "rgba(255,39,112,0.12)";
export const NEON_TEAL = "#0ac5a8";
export const NEON_TEAL_DIM = "rgba(10,197,168,0.12)";
export const NEON_AMBER = "#f59e0b";
export const NEON_AMBER_DIM = "rgba(245,158,11,0.12)";
export const NEON_GREEN = "#22c55e";
export const NEON_RED = "#ef4444";
export const NEON_PURPLE = "#a855f7";

/* ── Backgrounds ── */
export const BG_DEEP = "#060a12";
export const BG_SURFACE = "#0a0f1e";
export const BG_CARD = "#0d1324";
export const BG_ELEVATED = "#111a30";
export const BG_SIDEBAR = "#080c18";

/* ── Text ── */
export const TEXT = "rgba(255,255,255,0.88)";
export const TEXT_MUTED = "rgba(255,255,255,0.55)";
export const TEXT_DIM = "rgba(255,255,255,0.3)";

/* ── Gradients ── */
export const CYAN_GRADIENT = "linear-gradient(135deg, #00d4ff 0%, #0090b0 100%)";
export const MAGENTA_GRADIENT = "linear-gradient(135deg, #ff2770 0%, #cc1f5a 100%)";
```

---

## 5. Storybook Integration

### 5.1 Installation
```bash
cd frontend
npx storybook@latest init --type nextjs
```

### 5.2 Story Organization (per component)

```
src/components/ui/neon-button.stories.tsx
src/components/ui/neon-card.stories.tsx
src/components/ui/neon-badge.stories.tsx
...
```

### 5.3 Story Format (CSF 3)

```typescript
import type { Meta, StoryObj } from "@storybook/react";
import { NeonButton } from "./neon-button";

const meta = {
  title: "Atoms/NeonButton",
  component: NeonButton,
  parameters: {
    backgrounds: { default: "dark", values: [{ name: "dark", value: "#060a12" }] },
  },
  argTypes: {
    variant: { control: "select", options: ["primary", "secondary", "ghost", "danger"] },
    size: { control: "select", options: ["sm", "md", "lg"] },
    loading: { control: "boolean" },
    disabled: { control: "boolean" },
  },
} satisfies Meta<typeof NeonButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: { variant: "primary", children: "Primary Button" },
};

export const Loading: Story = {
  args: { loading: true, children: "Saving..." },
};

export const Disabled: Story = {
  args: { disabled: true, children: "Disabled" },
};

export const WithIcon: Story = {
  args: { variant: "secondary", children: "Search", icon: <span>🔍</span> },
};
```

---

## 6. Testing Strategy & Gherkin Scenarios

### 6.1 Gherkin Feature Files

Each component gets a `.feature` file in `tests/features/`:

**File**: `tests/features/neon-button.feature`

```gherkin
Feature: NeonButton Component
  As a developer using the NeonButton component
  I want to render buttons in different variants, sizes, and states
  So that I can use consistent button UI across the application

  Background:
    Given the NeonButton component is rendered on a dark background

  Scenario: Primary variant renders with cyan gradient
    When I render a primary NeonButton with text "Submit"
    Then I should see a button with text "Submit"
    And the button should have a cyan gradient background
    And the button should have a dark text color

  Scenario: Secondary variant renders with border outline
    When I render a secondary NeonButton with text "Cancel"
    Then I should see a button with text "Cancel"
    And the button should have a cyan border
    And the button should have a transparent background

  Scenario: Ghost variant renders with no background
    When I render a ghost NeonButton with text "Dismiss"
    Then I should see a button with text "Dismiss"
    And the button should have no background
    And the button should have white text

  Scenario: Danger variant renders with red gradient
    When I render a danger NeonButton with text "Delete"
    Then I should see a button with text "Delete"
    And the button should have a red gradient background

  Scenario: Disabled state prevents interaction
    Given a disabled NeonButton with an onClick handler
    When I click the button
    Then the onClick handler should NOT be called
    And the button should have the disabled attribute

  Scenario: Loading state shows spinner
    Given a NeonButton in loading state
    When I render the button
    Then I should see a spinner element inside the button
    And the button should be disabled
    And the button text should still be visible

  Scenario: Button fires onClick on click
    Given a NeonButton with an onClick handler
    When I click the button
    Then the onClick handler should be called exactly once

  Scenario: Full width variant spans container
    When I render a fullWidth NeonButton
    Then the button should span the full width of its container
    And the button should have the w-full class

  Scenario: Small size renders correctly
    When I render a small (sm) NeonButton
    Then the button should have smaller padding and font size
    And the button height should be 32px

  Scenario: Large size renders correctly
    When I render a large (lg) NeonButton
    Then the button should have larger padding and font size
    And the button height should be 48px

  Scenario: Icon positioned on the left
    Given a NeonButton with an icon and iconPosition="left"
    When I render the button
    Then the icon should appear before the button text

  Scenario: Icon positioned on the right
    Given a NeonButton with an icon and iconPosition="right"
    When I render the button
    Then the icon should appear after the button text

  Scenario: Focus-visible outline on keyboard navigation
    When I focus the button via keyboard (Tab)
    Then the button should have a 2px cyan focus outline
    And the outline should be offset by 2px

  Scenario: Custom className merges correctly
    When I render a NeonButton with a custom className
    Then the custom class should be applied alongside default classes

  Scenario: Hover state lightens background
    Given a primary NeonButton
    When I hover over the button
    Then the button shadow should intensify

  Scenario: Type attribute is set correctly
    When I render a NeonButton with type="submit"
    Then the button should have type="submit" attribute

  Scenario: Button maintains text visibility during loading
    Given a NeonButton with loading=true and text "Processing"
    When I render the button
    Then the text "Processing" should still be visible
    And the spinner should not replace the text

  Scenario: ARIA attributes for accessibility
    When I render a disabled NeonButton
    Then the button should have aria-disabled="true"
    When I render a loading NeonButton
    Then the button should have aria-busy="true"
```

**File**: `tests/features/neon-card.feature`

```gherkin
Feature: NeonCard Component

  Scenario: Default card renders with dark background
    When I render a NeonCard with content
    Then I should see a card with background #0d1324
    And the card should have a subtle border
    And the card should have rounded corners

  Scenario: Card with title displays header
    When I render a NeonCard with a title
    Then I should see a card header with the title text
    And the title should have bold font weight

  Scenario: Card with subtitle displays secondary text
    When I render a NeonCard with a subtitle
    Then I should see a subtitle below the title
    And the subtitle should have muted text color

  Scenario: Accent variant shows colored top border
    When I render a NeonCard with accent="cyan"
    Then the card should have a cyan top border line
    When I render with accent="magenta"
    Then the card should have a magenta top border line

  Scenario: Hover card lifts on mouse over
    When I render a NeonCard with hover=true
    Then the card should have a hover effect
    And on hover the border should become more visible
    And the card should slightly lift (transform)

  Scenario: Clickable card has cursor pointer
    When I render a NeonCard with an onClick handler
    Then the card should have cursor:pointer
    And clicking should call the onClick handler

  Scenario: Card has correct padding based on size prop
    When I render a NeonCard with padding="sm"
    Then the card should have small padding (16px)
    When I render with padding="lg"
    Then the card should have large padding (32px)

  Scenario: Card renders without accent by default
    When I render a default NeonCard
    Then the card should have no accent border
```

### 6.2 Test Implementation Pattern

**File**: `tests/unit/components/neon-button.test.tsx`

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NeonButton } from "@/components/ui/neon-button";

// Feature: NeonButton Component
// Scenario: Primary variant renders with cyan gradient
describe("NeonButton Component", () => {
  describe("Given the NeonButton component is rendered", () => {
    describe("When a primary variant is rendered with text 'Submit'", () => {
      it("Then the button should be visible with the provided text", () => {
        render(<NeonButton variant="primary">Submit</NeonButton>);
        expect(
          screen.getByRole("button", { name: /submit/i }),
        ).toBeInTheDocument();
      });
    });

    // Scenario: Disabled state prevents interaction
    describe("When the button has disabled prop set to true", () => {
      it("Then the button should be disabled and not respond to clicks", async () => {
        const handleClick = vi.fn();
        const user = userEvent.setup();

        render(
          <NeonButton disabled onClick={handleClick}>
            Disabled
          </NeonButton>,
        );

        const button = screen.getByRole("button");
        expect(button).toBeDisabled();
        expect(button).toHaveAttribute("aria-disabled", "true");

        await user.click(button);
        expect(handleClick).not.toHaveBeenCalled();
      });
    });

    // Scenario: Loading state shows spinner
    describe("When the button is in loading state", () => {
      it("Then a spinner should be shown and button should be disabled", () => {
        render(<NeonButton loading>Processing</NeonButton>);

        const button = screen.getByRole("button");
        expect(button).toBeDisabled();
        expect(button).toHaveAttribute("aria-busy", "true");
        // Spinner has role="status" for accessibility
        expect(screen.getByRole("status")).toBeInTheDocument();
        // Text still visible
        expect(button).toHaveTextContent("Processing");
      });
    });

    // Scenario: Button fires onClick on click
    describe("When the user clicks the button", () => {
      it("Then the onClick handler should be called", async () => {
        const handleClick = vi.fn();
        const user = userEvent.setup();

        render(<NeonButton onClick={handleClick}>Click</NeonButton>);
        await user.click(screen.getByRole("button"));

        expect(handleClick).toHaveBeenCalledTimes(1);
      });
    });

    // Scenario: Full width variant
    describe("When fullWidth prop is true", () => {
      it("Then the button should have w-full class", () => {
        render(<NeonButton fullWidth>Full Width</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("w-full");
      });
    });

    // Scenario: Different sizes
    describe("When different size props are provided", () => {
      it("Then the button should have corresponding size classes", () => {
        const { rerender } = render(<NeonButton size="sm">Small</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("h-8");

        rerender(<NeonButton size="md">Medium</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("h-10");

        rerender(<NeonButton size="lg">Large</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("h-12");
      });
    });

    // Scenario: Different variants
    describe("When different variant props are provided", () => {
      it("Then the button should have variant-specific gradient classes", () => {
        const { rerender } = render(
          <NeonButton variant="primary">Primary</NeonButton>,
        );
        expect(screen.getByRole("button")).toHaveClass("bg-gradient-to-r");

        rerender(<NeonButton variant="ghost">Ghost</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("bg-transparent");

        rerender(<NeonButton variant="danger">Danger</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("bg-gradient-to-r");
      });
    });

    // Scenario: Custom className merges
    describe("When custom className is provided", () => {
      it("Then the custom class should be applied alongside defaults", () => {
        render(
          <NeonButton className="my-custom-class">Custom</NeonButton>,
        );
        const button = screen.getByRole("button");
        expect(button).toHaveClass("my-custom-class");
        expect(button).toHaveClass("inline-flex"); // default CVA class
      });
    });

    // Scenario: Type attribute
    describe("When type prop is specified", () => {
      it("Then the button should have the correct type attribute", () => {
        render(<NeonButton type="submit">Submit</NeonButton>);
        expect(screen.getByRole("button")).toHaveAttribute("type", "submit");
      });
    });

    // Scenario: ARIA attributes
    describe("When the button is disabled", () => {
      it("Then it should have aria-disabled='true'", () => {
        render(<NeonButton disabled>Disabled</NeonButton>);
        expect(screen.getByRole("button")).toHaveAttribute("aria-disabled", "true");
      });
    });

    // Scenario: ARIA attributes for loading
    describe("When the button is loading", () => {
      it("Then it should have aria-busy='true'", () => {
        render(<NeonButton loading>Loading</NeonButton>);
        expect(screen.getByRole("button")).toHaveAttribute("aria-busy", "true");
      });
    });
  });
});
```

### 6.3 Mutation Testing Expectations

| Component | Expected Mutation Score | Key Mutants to Survive |
|---|---|---|
| `NeonButton` | ≥90% | variant mapping, disabled logic, loading logic, aria attributes |
| `NeonBadge` | ≥90% | color mapping, dot/outline toggle |
| `NeonCard` | ≥85% | accent colors, padding map, hover toggle |
| `NeonFormField` | ≥90% | error display logic, required indicator |
| `NeonStatCard` | ≥85% | change trend display, loading skeleton toggle |
| `NeonSidebar` | ≥80% | active path matching, badge display, section rendering |
| `NeonKanbanBoard` | ≥75% | column count logic, card filtering, status display |
| `NeonBlogPostCard` | ≥85% | conditional image rendering, date formatting |

**Stryker config additions** (for neon components): Update `stryker.conf.json` mutate globs to include neon component source when they reach 80%+ baseline.

```json
{
  "mutate": [
    "src/lib/api-client.ts",
    "src/features/carousel/queries.ts",
    // ... existing entries
    "src/components/ui/neon-button.tsx",
    "src/components/ui/neon-badge.tsx",
    "src/components/ui/neon-card.tsx",
    "src/components/ui/neon-form-field.tsx",
    "src/components/ui/neon-stat-card.tsx",
    "src/components/neon/neon-sidebar.tsx",
    "src/components/neon/neon-kanban-board.tsx"
  ],
  "thresholds": {
    "high": 90,
    "low": 80,
    "break": 80
  },
  "mutator": {
    "plugins": []
  },
  "ignorePatterns": [
    "node_modules",
    ".next",
    "tests/e2e",
    "reports",
    "coverage",
    ".stryker-tmp",
    "tests/unit/components/ui/neon-button.test.tsx",
    "tests/unit/components/ui/neon-card.test.tsx"
  ]
}
```

**Note**: Component-level mutation tests are added only after 80%+ baseline is established on business logic. Initial Stryker runs skip pure UI components (high noise, low signal).

---

## 7. Phase 0: Foundation

### Task 0.1: Add Neon Shell CSS Custom Properties

**Acceptance Criteria:**
- [ ] All `--color-neon-*`, `--color-bg-*`, `--color-text-*` variables added to `globals.css` `@theme`
- [ ] `npm run build` passes with 0 errors
- [ ] `npm run typecheck` passes with 0 errors
- [ ] `npm run test -- --run` passes (existing tests)
- [ ] Verified: Tailwind utility `text-neon-cyan` renders `#00d4ff` (browser DevTools)

**Implementation:**
1. Open `src/app/globals.css`
2. Add neon shell color variables to the existing `@theme` block (after existing color definitions)
3. Run build and test suite

**Gherkin Scenarios:**
```gherkin
Feature: Neon Shell CSS Tokens
  Scenario: Cyan color is available as Tailwind utility
    When I use text-neon-cyan on an element
    Then the element text color should be #00d4ff

  Scenario: Background hierarchy is correct
    When I use bg-bg-card on an element
    Then the background should be #0d1324
    When I use bg-bg-sidebar on an element
    Then the background should be #080c18
```

### Task 0.2: Create `src/constants/neon.ts`

**Acceptance Criteria:**
- [ ] All neon color constants exported from single file
- [ ] No duplicate definitions across the codebase
- [ ] `npm run typecheck` passes
- [ ] All existing imports still resolve (backward compatible)

**Implementation:**
1. Create `src/constants/neon.ts`
2. Export all color, background, text, and gradient constants
3. Catalog all current usages with `rg "#00d4ff" src/ --include="*.tsx" --include="*.ts"`

### Task 0.3: Create Atom Components (10 atoms)

Per atom, the same pattern:

1. **Create Zod schema** in `src/schemas/<component>.ts`
2. **Create component** in `src/components/ui/neon-<name>.tsx`
3. **Create `.feature` file** in `tests/features/neon-<name>.feature`
4. **Create test file** in `tests/unit/components/neon-<name>.test.tsx`
5. **Create Storybook story** in `src/components/ui/neon-<name>.stories.tsx`
6. **Create barrel export** in `src/components/ui/index.ts`

**Build order** (bottom of dependency graph first):

| Order | Component | Dependencies | Pages Using It |
|---|---|---|---|
| 1 | `NeonIcon` | none | ALL pages |
| 2 | `NeonSpinner` | none | ALL pages (loading states) |
| 3 | `NeonSkeleton` | none | Knowledge, Chat, Dashboard loading |
| 4 | `NeonLabel` | none | Login, Blog edit, Knowledge, Create |
| 5 | `NeonLink` | none | Sidebar nav, Public nav, Blog, Footer |
| 6 | `NeonBadge` | none | Dashboard, Workflow, Personas, Rubrics, Blog, Calendar |
| 7 | `NeonButton` | `NeonSpinner` | ALL pages |
| 8 | `NeonInput` | `NeonLabel` | Login, Blog edit, Knowledge, Chat |
| 9 | `NeonTextarea` | `NeonLabel` | Blog edit, Knowledge form |
| 10 | `NeonSelect` | `NeonLabel` | Create carousel, Blog filters |

**Edge cases to test per atom:**
- Empty state (no children, no text)
- Boundary values (min/max lengths, extreme sizes)
- Combined modifiers (disabled + loading, all variant + size combinations)
- Accessibility (aria attributes, keyboard navigation, focus management)
- Ref forwarding (for form library integration)
- Custom className merging (no class conflicts)

### Task 0.4: Create Molecule Components (10 molecules)

| Order | Component | Depends On | Pages Using It |
|---|---|---|---|
| 1 | `NeonCard` | `NeonBadge` | Dashboard, Workflow, Personas, Rubrics, Blog, Calendar, Knowledge |
| 2 | `NeonFormField` | `NeonLabel` + `NeonInput`/`NeonSelect`/`NeonTextarea` | Login, Blog edit, Knowledge, Create |
| 3 | `NeonStatCard` | `NeonCard` + `NeonIcon` | Dashboard, Analytics |
| 4 | `NeonSearchBar` | `NeonInput` + `NeonIcon` | Personas, Knowledge |
| 5 | `NeonProgressBar` | none (pure CSS) | Create carousel |
| 6 | `NeonBadgeGroup` | `NeonBadge` | Blog tags, Persona skills |
| 7 | `NeonToast` | `NeonBadge` + `NeonIcon` | All form submissions |
| 8 | `NeonModal` | `NeonCard` + `NeonButton` | Blog edit, Knowledge |
| 9 | `NeonDropdown` | `NeonButton` + `NeonCard` | Dashboard top-bar, Blog edit |
| 10 | `NeonTab` (compound) | Context API + `NeonBadge` | Future tabbed sections |

### Task 0.5: Create Organism Components (12 organisms)

| Order | Component | Depends On | Pages Using It |
|---|---|---|---|
| 1 | `NeonGridBackground` | none (pure CSS) | Dashboard layout, Public layout, Login |
| 2 | `NeonScanlineOverlay` | none (pure CSS) | Dashboard layout, Public layout, Login |
| 3 | `NeonSidebar` | `NeonLink` + `NeonBadge` + `NeonIcon` | Dashboard layout (ALL dashboard pages) |
| 4 | `NeonBreadcrumb` | `NeonLink` | Dashboard top-bar (ALL dashboard pages) |
| 5 | `NeonTopBar` | `NeonBreadcrumb` + `NeonButton` | Dashboard overview, Analytics, Blog posts, Calendar, Workflow, Personas, Rubrics |
| 6 | `NeonStatsGrid` | `NeonStatCard` | Dashboard, Analytics |
| 7 | `NeonActivityList` | `NeonCard` + `NeonBadge` (dot) | Dashboard |
| 8 | `NeonBlogPostCard` | `NeonCard` + `NeonBadge` + Image | Blog posts, Landing page |
| 9 | `NeonPersonaCard` | `NeonCard` + `NeonBadge` + avatar | Personas |
| 10 | `NeonRubricCard` | `NeonCard` + `NeonBadge` + score | Rubrics |
| 11 | `NeonPagination` | `NeonButton` | Blog posts, Knowledge |
| 12 | `NeonKanbanBoard` | `NeonCard` + `NeonBadge` | Workflow board |

---

## 8. Phase 1: Refactor Converted Pages

### Task 1.1: Refactor `dashboard/layout.tsx`

**Acceptance Criteria:**
- [ ] Inline grid background replaced with `NeonGridBackground`
- [ ] Inline scanline overlay replaced with `NeonScanlineOverlay`
- [ ] Inline sidebar replaced with `NeonSidebar` component
- [ ] All sidebar sections, items, badges preserved exactly
- [ ] Active tab detection via `usePathname()` preserved
- [ ] Logout button preserved
- [ ] `npm run build` passes
- [ ] Visual check: layout looks identical to before

**Implementation:**
1. Import `NeonGridBackground`, `NeonScanlineOverlay`, `NeonSidebar`
2. Replace inline grid `<div>` with `<NeonGridBackground />`
3. Replace inline scanline `<div>` with `<NeonScanlineOverlay />`
4. Extract sidebar items config into `NeonSidebar` props using existing `SIDEBAR_SECTIONS` constant
5. Remove inline grid/scanline/sidebar JSX and their local style constants

### Task 1.2: Refactor `(public)/layout.tsx`

Same as Task 1.1 — replace grid/scanline overlays with shared components.

### Task 1.3: Refactor `login/page.tsx`

Replace grid/scanline with shared components. Replace form elements with `NeonFormField`, `NeonInput`, `NeonButton`.

### Tasks 1.4–1.7: Refactor Dashboard Pages

| Task | File | Replacements |
|---|---|---|
| 1.4 | `dashboard/page.tsx` | `NeonStatsGrid`, `NeonActivityList`, `NeonCard` (quick actions) |
| 1.5 | `dashboard/workflow/page.tsx` | `NeonKanbanBoard`, `NeonCard`, `NeonBadge` |
| 1.6 | `dashboard/create/page.tsx` | `NeonProgressBar`, `NeonFormField`, `NeonCard` |
| 1.7 | Other dashboard pages | `NeonCard`, `NeonBadge`, `NeonSpinner`, `NeonTopBar` |

---

## 9. Phase 2: Convert Analytics Page

### Task 2.1: Convert `dashboard/analytics/page.tsx`

**Acceptance Criteria:**
- [ ] All shadcn `Card`, `CardContent`, `CardHeader`, `CardTitle` → `NeonCard`
- [ ] All shadcn `Spinner` → `NeonSpinner`
- [ ] `text-muted-foreground` → `TEXT_MUTED` constant
- [ ] `bg-primary` → `NEON_CYAN` constant
- [ ] `container mx-auto` → neon-styled container
- [ ] Same 4 stat cards with same data bindings
- [ ] Same velocity chart rendering
- [ ] Same loading/error states
- [ ] `npm run build` passes
- [ ] `npm run typecheck` passes
- [ ] `npm run test -- --run` passes (existing tests)

**Implementation:**
1. Remove imports from `@/components/ui`
2. Import `NeonCard`, `NeonSpinner` from `@/components/ui`
3. Replace `<Card>` → `<NeonCard>`, `<CardContent>` → direct children
4. Replace `<Spinner>` → `<NeonSpinner>`
5. Replace Tailwind classes `text-muted-foreground`, `bg-primary` with inline styles
6. Keep all data fetching, hooks, and logic exactly as-is

**Gherkin Scenarios:**
```gherkin
Feature: Analytics Page Visual Update

  Scenario: Stats cards display neon styling
    Given the analytics page is loaded with data
    When I view the stats grid
    Then I see 4 stat cards with dark backgrounds (#0d1324)
    And each card shows a label and value
    And the cards match the dashboard neon theme

  Scenario: Loading state shows neon spinner
    Given data is loading
    When the analytics page renders
    Then a neon-styled spinner is displayed centered on page
    And no stat cards are visible

  Scenario: Error state shows error message
    Given the data fetch failed
    When the analytics page renders
    Then an error message in red text is displayed
    And the error text matches the API error

  Scenario: Velocity chart uses neon bar styling
    Given the analytics page is loaded
    When I view the velocity chart section
    Then weekly bars are displayed in cyan
    And each bar has a date label
    And the bar width corresponds proportionally to count
```

**Test Cases (edge cases):**
- Empty data (no velocity_by_week entries)
- Missing summary values (null/undefined)
- Very large velocity values (bar width overflow)
- Rapid loading → data transitions
- Network error during fetch

---

## 10. Phase 3: Convert Knowledge Pages

### Task 3.1: Convert `features/knowledge/` (bottom-up)

Order and expected changes per file:

| File | Old Import | New Component |
|---|---|---|
| `file-upload.tsx` | `Button` → `Input` → `Label` | `NeonButton` → `NeonInput` → `NeonLabel` |
| `document-card.tsx` | `Card`, `CardContent`, `CardHeader`, `CardTitle`, `Badge` | `NeonCard`, `NeonBadge` |
| `document-form.tsx` | `Button`, `Input`, `Textarea`, `Label`, `Badge` | `NeonButton`, `NeonInput`, `NeonTextarea`, `NeonLabel`, `NeonBadge` |
| `document-list.tsx` | `Input`, `Button` | `NeonInput`, `NeonButton` |
| `knowledge-base-interface.tsx` | `Card`, `CardContent`, `CardHeader`, `CardTitle` | `NeonCard` |

**Acceptance Criteria (per file):**
- [ ] All shadcn UI imports replaced with neon equivalents
- [ ] Same props interfaces (no changes to data flow)
- [ ] Same event handlers preserved
- [ ] Same functionality (upload, search, list, form submission)
- [ ] `npm run build` passes after each file
- [ ] `npm run typecheck` passes

### Task 3.2: Convert `dashboard/knowledge/` error/loading pages

- `error.tsx`: `Button` → `NeonButton`
- `loading.tsx`: `Skeleton` → `NeonSkeleton`

---

## 11. Phase 4: Convert Blog Edit Page

### Task 4.1: Convert `dashboard/blog-posts/[id]/edit/page.tsx`

**Acceptance Criteria:**
- [ ] All shadcn UI components replaced with neon equivalents
- [ ] Same form state management (useState hooks preserved)
- [ ] Same submit/validation logic
- [ ] Same version history sidebar integration
- [ ] Same AI suggestion panel integration
- [ ] Same rich text editor integration
- [ ] `npm run build` passes
- [ ] `npm run test -- --run` passes (existing tests)

**Replacements:**
| Old | New |
|---|---|
| `Button` | `NeonButton` |
| `Card`, `CardContent`, `CardHeader`, `CardTitle` | `NeonCard` |
| `Input` | `NeonInput` |
| `Spinner` | `NeonSpinner` |
| `Textarea` | `NeonTextarea` |

### Task 4.2: Convert `dashboard/chat/` error/loading pages

- `error.tsx`: `Button` → `NeonButton`
- `loading.tsx`: `Skeleton` → `NeonSkeleton`

---

## 12. Phase 5: Convert Feature Components

### Task 5.1: Convert `features/blog/` (7 files)

| File | Old Components | New Components |
|---|---|---|
| `blog-post-filters.tsx` | `Input` | `NeonInput` |
| `seo-preview.tsx` | `Badge`, `Button`, `Card*` | `NeonBadge`, `NeonButton`, `NeonCard` |
| `keyboard-shortcuts-help.tsx` | `Button`, `Card*` | `NeonButton`, `NeonCard` |
| `accessibility-checker.tsx` | `Alert*`, `Badge`, `Button`, `Card*` | replace Alert inline, `NeonBadge`, `NeonButton`, `NeonCard` |
| `image-gen-modal.tsx` | `Alert*`, `Button`, `Input` | replace Alert inline, `NeonButton`, `NeonInput` |
| `ai-suggestion-panel.tsx` | `Alert*`, `Badge`, `Button`, `Textarea` | replace Alert inline, `NeonBadge`, `NeonButton`, `NeonTextarea` |
| `version-history-sidebar.tsx` | `Badge`, `Button`, `Card*` | `NeonBadge`, `NeonButton`, `NeonCard` |

**Note**: `Alert` from shadcn has no direct neon equivalent — replace with styled `<div>` with appropriate role="alert".

### Task 5.2: Convert `features/chat/` (2 files)

| File | Old Components | New Components |
|---|---|---|
| `message-input.tsx` | `Button`, `Textarea` | `NeonButton`, `NeonTextarea` |
| `conversation-sidebar.tsx` | `Button` | `NeonButton` |

### Task 5.3: Convert `features/workflow/` (2 files)

| File | Old Components | New Components |
|---|---|---|
| `review-assignment-panel.tsx` | `Label` | `NeonLabel` |
| `scheduled-publish-picker.tsx` | `Label` | `NeonLabel` |

---

## 13. Phase 6: Cleanup

### Task 6.1: Verify Zero shadcn Imports

**Acceptance Criteria:**
- [ ] `rg "@/components/ui" src/ --include="*.tsx" --include="*.ts"` returns 0 matches
- [ ] No file in `src/` imports from any old shadcn component

**Implementation:**
```bash
cd frontend
rg "@/components/ui" src/ --include="*.tsx" --include="*.ts"
# Expected: 0 results
rg "from.*components/ui" src/ --include="*.tsx"
# Expected: 0 results (or only neon-ui components)
```

### Task 6.2: Delete `src/components/ui/` Directory

**Acceptance Criteria:**
- [ ] All old shadcn component files deleted
- [ ] Barrel export `src/components/ui/index.ts` removed or updated (only neon exports)
- [ ] `npm run build` passes
- [ ] `npm run typecheck` passes
- [ ] `npm run test -- --run` passes

**Files to delete:**
```
src/components/ui/alert.tsx
src/components/ui/alert.test.tsx
src/components/ui/badge.tsx
src/components/ui/badge.test.tsx
src/components/ui/button.tsx
src/components/ui/button.test.tsx
src/components/ui/card.tsx
src/components/ui/card.test.tsx
src/components/ui/input.tsx
src/components/ui/input.test.tsx
src/components/ui/label.tsx
src/components/ui/label.test.tsx
src/components/ui/skeleton.tsx
src/components/ui/skeleton.test.tsx
src/components/ui/spinner.tsx
src/components/ui/spinner.test.tsx
src/components/ui/textarea.tsx
src/components/ui/textarea.test.tsx
```

**Update `src/components/ui/index.ts`** to only export neon components:
```typescript
export { NeonButton } from "./neon-button";
export { NeonCard } from "./neon-card";
export { NeonBadge } from "./neon-badge";
export { NeonInput } from "./neon-input";
export { NeonTextarea } from "./neon-textarea";
export { NeonSelect } from "./neon-select";
export { NeonLabel } from "./neon-label";
export { NeonSpinner } from "./neon-spinner";
export { NeonSkeleton } from "./neon-skeleton";
export { NeonIcon } from "./neon-icon";
export { NeonLink } from "./neon-link";
export { NeonFormField } from "./neon-form-field";
export { NeonSearchBar } from "./neon-search-bar";
export { NeonStatCard } from "./neon-stat-card";
export { NeonProgressBar } from "./neon-progress-bar";
export { NeonBadgeGroup } from "./neon-badge-group";
export { NeonToast } from "./neon-toast";
export { NeonModal } from "./neon-modal";
export { NeonDropdown } from "./neon-dropdown";
export { NeonTab, NeonTabPanel } from "./neon-tab";
export { NeonSidebar } from "@/components/neon/neon-sidebar";
export { NeonTopBar } from "@/components/neon/neon-top-bar";
export { NeonBreadcrumb } from "@/components/neon/neon-breadcrumb";
export { NeonStatsGrid } from "@/components/neon/neon-stats-grid";
export { NeonActivityList } from "@/components/neon/neon-activity-list";
export { NeonKanbanBoard } from "@/components/neon/neon-kanban-board";
export { NeonPersonaCard } from "@/components/neon/neon-persona-card";
export { NeonRubricCard } from "@/components/neon/neon-rubric-card";
export { NeonBlogPostCard } from "@/components/neon/neon-blog-post-card";
export { NeonPagination } from "@/components/neon/neon-pagination";
export { NeonGridBackground } from "@/components/neon/neon-grid-background";
export { NeonScanlineOverlay } from "@/components/neon/neon-scanline-overlay";
```

### Task 6.3: Consolidate Color Constants

**Acceptance Criteria:**
- [ ] `src/app/dashboard/constants.tsx` imports from `@/constants/neon` instead of redefining
- [ ] `src/features/dashboard/chat/constants.ts` imports from `@/constants/neon`
- [ ] No local `const CYAN = "#00d4ff"` in any page file
- [ ] `npm run build` passes

**Implementation:**
```bash
# Find all duplicate constant definitions
rg "const CYAN = \|const MAGENTA = \|const TEAL = \|const BG_DEEP = \|const BG_CARD = \|const TEXT = " src/ --include="*.tsx"
# Replace each with imports from @/constants/neon
```

### Task 6.4: Remove Old Test Mocks

**Files to update:**
- `features/knowledge/components/knowledge-base-interface.test.tsx` — remove `vi.mock("@/components/ui/card")`
- Any other test file mocking old shadcn components

### Task 6.5: Handle Legacy Route Groups

- `(admin)/admin/users/page.tsx` — no shadcn imports, uses raw Tailwind. Can remain or be flagged for future conversion.
- `(blog)/` and `(create)/` — clean, use CSS variables. Keep as-is.

### Task 6.6: Update Stryker Config

Add neon component source files to the `mutate` glob once they reach 80%+ mutation score baseline.

---

## 14. Cross-Cutting Concerns

### 14.1 CI Safeguards (per CLAUDE.md)

Before every commit:
```bash
npm run build         # 0 errors
npm run typecheck     # 0 errors
npm run lint          # 0 errors
npm run test -- --run # All tests pass
```

After migration:
```bash
npm run test:coverage # 90%+ branch coverage
npx stryker run       # 80%+ mutation score on business logic
```

### 14.2 Code Quality Rules (per CLAUDE.md)

- [ ] No `any` types → use Zod-inferred types
- [ ] No `object` types → use `Record<string, unknown>` or specific interfaces
- [ ] All functions have explicit return types
- [ ] Max 400 lines per file
- [ ] Max 20 lines per function
- [ ] Named exports only (no default exports)
- [ ] Early returns preferred over nested ifs
- [ ] No magic strings → use `src/constants/neon.ts`
- [ ] No hardcoded text → use i18n (`useTranslations`)
- [ ] Interfaces in their own files (`src/schemas/`)

### 14.3 Accessibility

- All interactive components keyboard accessible
- `aria-disabled` + `aria-busy` on buttons
- `role="status"` on spinners for screen readers
- `role="alert"` on error messages
- `aria-hidden="true"` on decorative icons
- `prefers-reduced-motion` media query disables animations
- WCAG 2.1 AA color contrast on all text combinations

### 14.4 Responsive Breakpoints

| Breakpoint | Width | Layout Change |
|---|---|---|
| Desktop | > 1024px | Full layout, 6-col kanban, 4 stat cards |
| Tablet | 768px - 1023px | 4-col kanban, 2 stat cards |
| Mobile | < 768px | 1-col kanban, 1 stat card, full-width cards |

### 14.5 File Size Budget

| Component | Estimated Size (gzipped) |
|---|---|
| NeonButton | ~0.5 KB |
| NeonCard | ~0.3 KB |
| NeonBadge | ~0.2 KB |
| NeonSpinner | ~0.1 KB |
| NeonSidebar | ~2 KB |
| NeonKanbanBoard | ~3 KB |
| Entire neon library | ~20-25 KB |

---

## 15. Data Flow Integration: How Neon Components Connect to Backend

### 15.1 Architecture Principle: Presentational Components

**All Neon components are purely presentational** — they receive data via props and have no data-fetching logic internally. This is a deliberate architectural decision following three rules:

1. **Neon components never call `useQuery`, `useMutation`, or `apiCall`**
2. **Neon components never access TanStack Query cache directly**
3. **Neon components are "dumb"** — they accept props and render

The integration layer lives in **page components** and **feature hooks**, which:
- Call TanStack Query hooks to fetch data from the backend API
- Map the API response to Neon component props via **adapter functions**
- Handle loading/error/empty states and pass the correct props to Neon components

### 15.2 Data Flow Pipeline (Full End-to-End)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                             │
│  /api/carousels?status=completed&limit=5                                │
│  /api/documents                                                         │
│  /api/blog-posts                                                        │
│  /api/workflow/board                                                    │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ HTTP response with JSON
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    API CLIENT (src/lib/api-client.ts)                    │
│  apiCall<T>(url, schema, options) → Promise<T>                          │
│  Validates response with Zod schema before returning                    │
│  Handles auth headers, error codes, retry logic                         │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ Typed response (T)
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              QUERY OPTIONS (src/features/*/queries.ts)                   │
│  queryOptions({ queryKey: [...], queryFn: () => apiCall(...) })         │
│  Pre-configured with staleTime, gcTime, retry, refetchOnWindowFocus     │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ Query key + options
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     HOOK LAYER (src/features/*/hooks/)                   │
│  useBlogPosts(limit?) → { data, isLoading, error }                      │
│  useDocuments() → { data, isLoading, error }                            │
│  useEditorialAnalytics() → { data, loading, error }                     │
│                                                                         │
│  Wraps useQuery with domain-specific defaults                           │
│  Each hook returns TanStack Query result object                         │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ { data, isLoading, error }
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               PAGE COMPONENT (src/app/dashboard/*/page.tsx)              │
│                                                                         │
│  function DashboardPage() {                                             │
│    const { data, isLoading, error } = useBlogPosts(5);                  │
│                                                                         │
│    if (isLoading) return <NeonSkeleton variant="card" count={5} />;     │
│    if (error) return <ErrorDisplay message={error.message} />;          │
│                                                                         │
│    const featured = data?.[0];                                          │
│    const items = data?.slice(1) ?? [];                                  │
│                                                                         │
│    return (                                                             │
│      <>                                                                 │
│        {featured && <NeonBlogPostCard {...mapToCardProps(featured)} />} │
│        {items.map(item => <NeonBlogPostCard {...mapToCardProps(item)} variant="compact" />)}
│      </>                                                                │
│    );                                                                   │
│  }                                                                      │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ Props
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   NEON COMPONENT (presentational)                        │
│                                                                         │
│  function NeonBlogPostCard({ title, subtitle, niche, imageUrl, href })  │
│    // Pure rendering — no data fetching, no side effects                │
│    return <NeonCard hover as={Link} href={href}> ... </NeonCard>        │
│  }                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 15.3 Data Flow Patterns by Page

#### Pattern 1: Static Mock Data (Dashboard overview, Workflow, Personas, Rubrics, Blog posts)

These pages currently use **hardcoded mock data** from constants files. The migration replaces inline JSX with Neon components while keeping the same data:

```typescript
// BEFORE (dashboard/page.tsx — inline styles with static data)
<div style={{ background: "#0d1324", border: "..." }}>
  <div style={{ background: "rgba(0,212,255,0.12)", borderRadius: "8px" }}>
    <svg>{/* icon */}</svg>
  </div>
  <p style={{ fontSize: "13px", color: "rgba(255,255,255,0.55)" }}>Active Carousels</p>
  <p style={{ fontSize: "28px", fontWeight: 700 }}>24</p>
  <span style={{ color: "#22c55e" }}>+3 this week</span>
</div>

// AFTER — use NeonStatCard with existing mock data
import { STAT_CARDS, QUICK_ACTIONS, RECENT_ACTIVITIES, UPCOMING_SCHEDULE } from "./constants";
import { NeonStatsGrid, NeonActivityList, NeonCard } from "@/components/ui";

export default function DashboardPage() {
  const t = useTranslations("dashboard.overview");

  return (
    <>
      <NeonTopBar title="Dashboard" breadcrumb={[{ label: "Overview" }]} />
      <NeonStatsGrid cards={STAT_CARDS} />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        {QUICK_ACTIONS.map(action => (
          <NeonCard key={action.title} hover padding="md">
            <NeonIcon icon={action.icon} color={action.iconColor} />
            <h3>{action.title}</h3>
            <p>{action.description}</p>
          </NeonCard>
        ))}
      </div>
      <NeonActivityList activities={RECENT_ACTIVITIES} />
    </>
  );
}
```

**Data transformation**: Zero transformation needed — the mock data already has the shape Neon components expect (label, value, icon, etc.).

#### Pattern 2: TanStack Query → Page → Neon (Knowledge, Analytics, Chat)

For pages that fetch real API data, the page component mediates between the query hook and Neon components:

```typescript
// src/app/dashboard/knowledge/page.tsx
"use client";

import { useDocuments } from "@/features/knowledge/hooks/use-documents";
import { NeonCard, NeonBadge, NeonSpinner, NeonPagination, NeonSearchBar } from "@/components/ui";
import { mapDocumentToCardProps } from "@/features/knowledge/adapters/document-adapter";

export default function KnowledgePage() {
  const { data: documents, isLoading, error } = useDocuments();

  // ── Loading State ──
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <NeonSpinner size="lg" />
      </div>
    );
  }

  // ── Error State ──
  if (error || !documents) {
    return (
      <div className="flex items-center justify-center py-20">
        <NeonCard padding="lg">
          <p style={{ color: "#ef4444" }}>Failed to load documents</p>
        </NeonCard>
      </div>
    );
  }

  // ── Empty State ──
  if (documents.length === 0) {
    return (
      <NeonCard padding="lg">
        <p>No documents found. Upload your first document.</p>
      </NeonCard>
    );
  }

  // ── Success State ──
  return (
    <div>
      <NeonSearchBar placeholder="Search documents..." />
      <div className="grid gap-4 mt-6">
        {documents.map((doc) => (
          <NeonCard key={doc.id} hover padding="md">
            {/* card content using doc fields */}
            <h3>{doc.title}</h3>
            <NeonBadge variant={doc.status === "completed" ? "green" : "amber"}>
              {doc.status}
            </NeonBadge>
          </NeonCard>
        ))}
      </div>
      <NeonPagination total={documents.length} page={1} />
    </div>
  );
}
```

**Key rule**: The page component owns ALL states (loading, error, empty, success). Neon components only receive the relevant props for their current state.

#### Pattern 3: Adapter Functions (API Response → Neon Props)

When the backend API response shape differs from the Neon component props, use **adapter functions**:

```typescript
// src/features/knowledge/adapters/document-adapter.ts
import type { Document } from "@/schemas/knowledge";
import type { NeonCardProps } from "@/schemas/neon-card";
import type { NeonBadgeVariant } from "@/schemas/neon-badge";

/**
 * Maps a backend Document to NeonCard props.
 * Handles null/undefined fields with fallbacks.
 */
export function mapDocumentToCardProps(doc: Document): {
  cardProps: Partial<NeonCardProps>;
  badgeVariant: NeonBadgeVariant;
  badgeText: string;
} {
  return {
    cardProps: {
      hover: true,
      padding: "md",
      accent: doc.type === "pdf" ? "cyan" : "magenta",
      onClick: undefined, // page component sets this
    },
    badgeVariant: doc.status === "completed"
      ? "green"
      : doc.status === "processing"
        ? "amber"
        : "red",
    badgeText: doc.status,
  };
}
```

```typescript
// src/features/blog/adapters/blog-post-adapter.ts
import type { NeonBlogPostCardProps } from "@/schemas/neon-blog-post-card";

/**
 * Maps a backend CarouselProject to NeonBlogPostCard props.
 *
 * Backend response shape:
 * {
 *   id: string;
 *   title: string;
 *   title_en: string | null;
 *   subtitle: string | null;
 *   subtitle_en: string | null;
 *   niche: string | null;
 *   design_tokens: { images?: { hero?: string } } | null;
 *   created_at: string;
 * }
 */
export function mapProjectToBlogPostCard(
  project: CarouselProjectResponse,
  locale: string,
): NeonBlogPostCardProps {
  const imageUrl = project.design_tokens?.images?.hero ?? "";
  const title = locale === "en"
    ? (project.title_en || project.title || project.topic)
    : (project.title || project.topic);

  return {
    id: project.id,
    title,
    subtitle: (locale === "en" ? project.subtitle_en || project.subtitle : project.subtitle) ?? "",
    niche: project.niche ?? undefined,
    imageUrl: imageUrl || undefined,
    createdAt: project.created_at,
    href: `/blog/${project.id}`,
  };
}
```

#### Pattern 4: Direct Embedding (Mock Data → Neon Props)

For pages where mock data is already defined in constants, the page component directly embeds existing mock data into Neon component props without an adapter layer:

```typescript
// src/app/dashboard/workflow/page.tsx
import { NeonKanbanBoard, NeonCard, NeonBadge } from "@/components/ui";
import type { KanbanColumn } from "@/schemas/neon-kanban";

const COLUMNS: KanbanColumn[] = [
  {
    phase: "research",
    status: "Research",
    cards: [
      {
        id: "1",
        title: "DeepSeek V4 Analysis",
        description: "Research open-source LLM benchmarks...",
        phase: "research",
        phaseStatus: "awaiting_human",
        assignee: "PM",
      },
    ],
  },
  // ...
];

export default function WorkflowPage() {
  return <NeonKanbanBoard columns={COLUMNS} />;
}
```

### 15.4 Adapter File Locations

Each domain that bridges backend responses to Neon components gets an adapter file:

| Domain | Adapter File | Purpose |
|---|---|---|
| Knowledge | `src/features/knowledge/adapters/document-adapter.ts` | Document → NeonCard props |
| Blog | `src/features/blog/adapters/blog-post-adapter.ts` | CarouselProject → NeonBlogPostCard props |
| Personas | `src/features/dashboard/personas/adapters/persona-adapter.ts` | Persona → NeonPersonaCard props |
| Rubrics | `src/features/dashboard/rubrics/adapters/rubric-adapter.ts` | Rubric → NeonRubricCard props |
| Workflow | `src/features/dashboard/workflow/adapters/workflow-adapter.ts` | Workflow status → NeonKanbanBoard props |
| Calendar | `src/features/dashboard/calendar/adapters/calendar-adapter.ts` | CalendarEvent → NeonCard props |

**Adapter pattern** (each file exports a single pure function):

```typescript
export function mapXToNeonY(input: BackendType, context?: AdapterContext): NeonYProps {
  return {
    // Field-by-field mapping with null/undefined fallbacks
    prop1: input.field1 ?? fallback1,
    prop2: transform(input.field2, context),
    // ...
  };
}
```

### 15.5 State Management Matrix

| Page | Data Source | Loading State | Error State | Empty State | Neon Components Used |
|---|---|---|---|---|---|
| Dashboard | Static mock | N/A | N/A | N/A | `NeonStatsGrid`, `NeonActivityList`, `NeonCard` |
| Analytics | `useEditorialAnalytics()` | `NeonSpinner` (centered) | Error text | "No data" message | `NeonStatCard`, `NeonCard` |
| Knowledge | `useDocuments()` | `NeonSpinner` (centered) | `NeonCard` + error text | "Upload first" prompt | `NeonCard`, `NeonBadge`, `NeonSearchBar`, `NeonPagination` |
| Blog Posts | Static mock | N/A | N/A | "No posts" prompt | `NeonBlogPostCard`, `NeonCard`, `NeonBadge` |
| Workflow | Static mock | N/A | N/A | Empty columns | `NeonKanbanBoard`, `NeonCard`, `NeonBadge` |
| Personas | Static mock | N/A | N/A | "No personas" prompt | `NeonPersonaCard`, `NeonBadge`, `NeonSearchBar` |
| Rubrics | Static mock | N/A | N/A | "No rubrics" prompt | `NeonRubricCard`, `NeonBadge` |
| Chat | `useChat()` / SSE | `NeonSkeleton` | Error banner | Empty chat | `NeonButton`, `NeonInput`, `NeonCard` |
| Blog Edit | `useCarouselProject()` | `NeonSpinner` | Error text | N/A (redirect) | `NeonButton`, `NeonInput`, `NeonTextarea`, `NeonCard`, `NeonSelect` |
| Calendar | Static mock | N/A | N/A | Empty days | `NeonCard`, `NeonBadge` |
| Create | Form hooks | N/A (client-side) | Validation errors | N/A | `NeonFormField`, `NeonProgressBar`, `NeonSelect`, `NeonCard` |

### 15.6 No Backend Changes Required

Neon components accept data as props. The adapter functions transform existing backend API responses into the prop shapes Neon components expect. This means:

- **No new API endpoints** needed
- **No changes to existing API contracts**
- **No schema migrations**
- **Existing Zod validation schemas remain unchanged**
- **Existing TanStack Query configuration remains unchanged**

The only new code is:
1. Neon components (presentational)
2. Adapter functions (pure transformations)
3. Page component updates (replace inline JSX with Neon components + adapter calls)

### 15.7 Example: Full E2E Pipeline for a Real Feature

**Backend endpoint**: `GET /api/carousels?status=completed&limit=5`

**Response shape** (no changes):
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "DeepSeek V4 Analysis",
      "title_en": "DeepSeek V4 Analysis",
      "subtitle": "Análise completa da arquitetura e benchmarks",
      "subtitle_en": "Complete architecture and benchmarks analysis",
      "niche": "AI",
      "design_tokens": {
        "images": { "hero": "/api/media/hero.jpg" }
      },
      "created_at": "2026-05-27T10:00:00Z"
    }
  ]
}
```

**Query options** (`src/features/carousel/queries.ts` — untouched):
```typescript
export function carouselProjectsOptions(status?: string, limit?: number) {
  return queryOptions({
    queryKey: [...],
    queryFn: () => apiCall(API_ENDPOINTS.CAROUSEL_PROJECTS, carouselListSchema, {
      params: { status, limit },
    }),
  });
}
```

**Hook** (`src/features/blog/hooks/use-carousel-blog.ts` — untouched):
```typescript
export function useBlogPosts(limit?: number) {
  return useQuery(carouselProjectsOptions("completed", limit));
}
```

**Page component** (rewritten):
```typescript
// src/app/dashboard/blog-posts/page.tsx
"use client";

import { useTranslations } from "next-intl";
import { useBlogPosts } from "@/features/blog/hooks/use-blog-posts";
import { mapProjectToBlogPostCard } from "@/features/blog/adapters/blog-post-adapter";
import {
  NeonTopBar, NeonBlogPostCard, NeonCard, NeonBadge, NeonBadgeGroup,
  NeonSearchBar, NeonButton, NeonSpinner, NeonPagination,
} from "@/components/ui";

export default function BlogPostsPage() {
  const t = useTranslations("dashboard.blog");
  // ── Replace static mock with TanStack Query hook ──
  const { data, isLoading, error } = useBlogPosts(50);

  // ── Loading ──
  if (isLoading) {
    return (
      <div className="flex-1">
        <NeonTopBar title="Blog Posts" breadcrumb={[{ label: "all posts" }]} />
        <div className="p-6 space-y-4">
          {[1, 2, 3].map(i => <NeonSkeleton key={i} variant="rectangular" height={120} />)}
        </div>
      </div>
    );
  }

  // ── Error ──
  if (error) {
    return (
      <div className="flex-1">
        <NeonTopBar title="Blog Posts" breadcrumb={[{ label: "all posts" }]} />
        <div className="p-6">
          <NeonCard padding="md" accent="red">
            <p>Failed to load posts. Please try again.</p>
          </NeonCard>
        </div>
      </div>
    );
  }

  // ── Empty ──
  const items = data?.items ?? [];
  if (items.length === 0) {
    return (
      <div className="flex-1">
        <NeonTopBar title="Blog Posts" breadcrumb={[{ label: "all posts" }]} />
        <div className="p-6">
          <NeonCard padding="lg">
            <p>{t("noPosts")}</p>
          </NeonCard>
        </div>
      </div>
    );
  }

  // ── Success ──
  const [featured, ...rest] = items;
  return (
    <div className="flex-1">
      <NeonTopBar
        title="Blog Posts"
        breadcrumb={[{ label: "all posts" }]}
        actions={<NeonButton variant="primary" icon={<PlusIcon />}>New Post</NeonButton>}
      />
      <div className="p-6 space-y-6">
        {featured && (
          <NeonBlogPostCard {...mapProjectToBlogPostCard(featured, "en")} featured />
        )}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {rest.map(post => (
            <NeonBlogPostCard key={post.id} {...mapProjectToBlogPostCard(post, "en")} />
          ))}
        </div>
        <NeonPagination total={items.length} page={1} />
      </div>
    </div>
  );
}
```

**Adapter** (new):
```typescript
// src/features/blog/adapters/blog-post-adapter.ts
export function mapProjectToBlogPostCard(
  project: CarouselProjectResponse,
  locale: string,
): NeonBlogPostCardProps {
  return {
    id: project.id,
    title: locale === "en"
      ? (project.title_en || project.title || project.topic)
      : (project.title || project.topic),
    subtitle: truncateText(locale === "en"
      ? project.subtitle_en || project.subtitle || project.topic
      : project.subtitle || project.topic, 15),
    niche: project.niche ?? undefined,
    imageUrl: project.design_tokens?.images?.hero ?? undefined,
    createdAt: project.created_at,
    href: `/blog/${project.id}`,
  };
}
```

**Neon component** (new):
```typescript
// src/components/neon/neon-blog-post-card.tsx
import { Link } from "next/link";
import { NeonCard } from "@/components/ui/neon-card";
import { NeonBadge } from "@/components/ui/neon-badge";
import type { NeonBlogPostCardProps } from "@/schemas/neon-blog-post-card";

export function NeonBlogPostCard({
  title, subtitle, niche, imageUrl, createdAt, href, featured,
}: NeonBlogPostCardProps & { featured?: boolean }) {
  return (
    <NeonCard hover padding="md" as={Link} href={href}>
      {niche && <NeonBadge variant="magenta">{niche}</NeonBadge>}
      <h3 className={featured ? "text-lg font-bold" : "text-sm font-semibold"}>
        {title}
      </h3>
      {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
      <time className="text-xs text-dim">{new Date(createdAt).toLocaleDateString()}</time>
    </NeonCard>
  );
}
```

**Verification**: The full pipeline (backend → API client → query options → hook → page → adapter → Neon component) is tested end-to-end via:
- `npm run build` (compilation)
- Existing integration tests (API contract tests)
- New unit tests for adapter functions
- `npm run typecheck` (type safety across the entire chain)

---

## 17. Final Project File Tree (After Migration)

### 17.1 Files DELETED (19 old shadcn files)

```
src/components/ui/                ← Removed entirely
├── alert.tsx                     ← DELETE (was: <div role="alert">)
├── alert.test.tsx                ← DELETE
├── badge.tsx                     ← DELETE
├── badge.test.tsx                ← DELETE
├── button.tsx                    ← DELETE
├── button.test.tsx               ← DELETE
├── card.tsx                      ← DELETE
├── card.test.tsx                 ← DELETE
├── index.ts                      ← REPLACE with neon-only barrel exports
├── input.tsx                     ← DELETE
├── input.test.tsx                ← DELETE
├── label.tsx                     ← DELETE
├── label.test.tsx                ← DELETE
├── skeleton.tsx                  ← DELETE
├── skeleton.test.tsx             ← DELETE
├── spinner.tsx                   ← DELETE
├── spinner.test.tsx              ← DELETE
├── textarea.tsx                  ← DELETE
└── textarea.test.tsx             ← DELETE
```

### 17.2 Files CREATED (66 new files)

```
# ── Constants ──
src/constants/
└── neon.ts                       ← NEW: Neon Shell color constants (single source of truth)

# ── Zod Schemas ──
src/schemas/
├── neon-button.ts                ← NEW
├── neon-badge.ts                 ← NEW
├── neon-card.ts                  ← NEW
├── neon-form-field.ts            ← NEW
├── neon-stat-card.ts             ← NEW
├── neon-sidebar.ts               ← NEW
├── neon-kanban.ts                ← NEW
├── neon-blog-post-card.ts        ← NEW
├── neon-tab.ts                   ← NEW
└── neon-progress-bar.ts          ← NEW

# ── Atom Components (10) ──
src/components/ui/
├── neon-icon.tsx                 ← NEW
├── neon-icon.test.tsx            ← NEW
├── neon-icon.stories.tsx         ← NEW
├── neon-spinner.tsx              ← NEW
├── neon-spinner.test.tsx         ← NEW
├── neon-spinner.stories.tsx      ← NEW
├── neon-skeleton.tsx             ← NEW
├── neon-skeleton.test.tsx        ← NEW
├── neon-skeleton.stories.tsx     ← NEW
├── neon-label.tsx                ← NEW
├── neon-label.test.tsx           ← NEW
├── neon-label.stories.tsx        ← NEW
├── neon-link.tsx                 ← NEW
├── neon-link.test.tsx            ← NEW
├── neon-link.stories.tsx         ← NEW
├── neon-badge.tsx                ← NEW
├── neon-badge.test.tsx           ← NEW
├── neon-badge.stories.tsx        ← NEW
├── neon-button.tsx               ← NEW
├── neon-button.test.tsx          ← NEW
├── neon-button.stories.tsx       ← NEW
├── neon-input.tsx                ← NEW
├── neon-input.test.tsx           ← NEW
├── neon-input.stories.tsx        ← NEW
├── neon-textarea.tsx             ← NEW
├── neon-textarea.test.tsx        ← NEW
├── neon-textarea.stories.tsx     ← NEW
├── neon-select.tsx               ← NEW
├── neon-select.test.tsx          ← NEW
├── neon-select.stories.tsx       ← NEW
└── index.ts                      ← REPLACED: now exports only neon components

# ── Molecule Components (10) ──
src/components/ui/
├── neon-card.tsx                 ← NEW
├── neon-card.test.tsx            ← NEW
├── neon-card.stories.tsx         ← NEW
├── neon-form-field.tsx           ← NEW
├── neon-form-field.test.tsx      ← NEW
├── neon-form-field.stories.tsx   ← NEW
├── neon-search-bar.tsx           ← NEW
├── neon-search-bar.test.tsx      ← NEW
├── neon-search-bar.stories.tsx   ← NEW
├── neon-stat-card.tsx            ← NEW
├── neon-stat-card.test.tsx       ← NEW
├── neon-stat-card.stories.tsx    ← NEW
├── neon-progress-bar.tsx         ← NEW
├── neon-progress-bar.test.tsx    ← NEW
├── neon-progress-bar.stories.tsx ← NEW
├── neon-badge-group.tsx          ← NEW
├── neon-badge-group.test.tsx     ← NEW
├── neon-badge-group.stories.tsx  ← NEW
├── neon-toast.tsx                ← NEW
├── neon-toast.test.tsx           ← NEW
├── neon-toast.stories.tsx        ← NEW
├── neon-modal.tsx                ← NEW
├── neon-modal.test.tsx           ← NEW
├── neon-modal.stories.tsx        ← NEW
├── neon-dropdown.tsx             ← NEW
├── neon-dropdown.test.tsx        ← NEW
├── neon-dropdown.stories.tsx     ← NEW
├── neon-tab.tsx                  ← NEW (compound component)
├── neon-tab.test.tsx             ← NEW
└── neon-tab.stories.tsx          ← NEW

# ── Organism Components (12) ──
src/components/neon/
├── neon-grid-background.tsx      ← NEW
├── neon-scanline-overlay.tsx     ← NEW
├── neon-sidebar.tsx              ← NEW
├── neon-sidebar.test.tsx         ← NEW
├── neon-top-bar.tsx              ← NEW
├── neon-top-bar.test.tsx         ← NEW
├── neon-breadcrumb.tsx           ← NEW
├── neon-breadcrumb.test.tsx      ← NEW
├── neon-stats-grid.tsx           ← NEW
├── neon-stats-grid.test.tsx      ← NEW
├── neon-activity-list.tsx        ← NEW
├── neon-activity-list.test.tsx   ← NEW
├── neon-kanban-board.tsx         ← NEW
├── neon-kanban-board.test.tsx    ← NEW
├── neon-persona-card.tsx         ← NEW
├── neon-persona-card.test.tsx    ← NEW
├── neon-rubric-card.tsx          ← NEW
├── neon-rubric-card.test.tsx     ← NEW
├── neon-blog-post-card.tsx       ← NEW
├── neon-blog-post-card.test.tsx  ← NEW
├── neon-pagination.tsx           ← NEW
└── neon-pagination.test.tsx      ← NEW

# ── Adapter Functions (6) ──
src/features/
├── knowledge/adapters/
│   └── document-adapter.ts       ← NEW
├── blog/adapters/
│   └── blog-post-adapter.ts      ← NEW
├── dashboard/personas/adapters/
│   └── persona-adapter.ts        ← NEW
├── dashboard/rubrics/adapters/
│   └── rubric-adapter.ts         ← NEW
├── dashboard/workflow/adapters/
│   └── workflow-adapter.ts       ← NEW
└── dashboard/calendar/adapters/
    └── calendar-adapter.ts       ← NEW

# ── Gherkin Feature Files (10+) ──
tests/features/
├── neon-button.feature           ← NEW
├── neon-card.feature             ← NEW
├── neon-badge.feature            ← NEW
├── neon-form-field.feature       ← NEW
├── neon-stat-card.feature        ← NEW
├── neon-sidebar.feature          ← NEW
├── neon-kanban.feature           ← NEW
├── neon-blog-post-card.feature   ← NEW
├── neon-persona-card.feature     ← NEW
└── analytics-visual.feature      ← NEW

# ── Test Files (co-located in tests/unit/) ──
tests/unit/components/
├── neon-button.test.tsx          ← NEW (17 scenarios)
├── neon-card.test.tsx            ← NEW (10 scenarios)
├── neon-badge.test.tsx           ← NEW (8 scenarios)
├── neon-form-field.test.tsx      ← NEW
├── neon-stat-card.test.tsx       ← NEW
├── neon-sidebar.test.tsx         ← NEW
└── neon-kanban.test.tsx          ← NEW

# ── Storybook Stories ──
src/components/ui/
├── neon-button.stories.tsx       ← NEW
├── neon-card.stories.tsx         ← NEW
├── neon-badge.stories.tsx        ← NEW
├── neon-input.stories.tsx        ← NEW
├── neon-form-field.stories.tsx   ← NEW
├── neon-stat-card.stories.tsx    ← NEW
└── neon-sidebar.stories.tsx      ← NEW
```

### 17.3 Files MODIFIED (21 existing files)

```
# ── Core Styles ──
src/app/globals.css                ← MODIFIED: add neon CSS variables to @theme

# ── App Pages (refactored to use neon components) ──
src/app/dashboard/layout.tsx       ← MODIFIED: use NeonSidebar, NeonGridBackground, NeonScanlineOverlay
src/app/dashboard/page.tsx         ← MODIFIED: use NeonStatsGrid, NeonActivityList, NeonCard
src/app/dashboard/analytics/page.tsx ← MODIFIED: convert from shadcn to neon
src/app/dashboard/workflow/page.tsx ← MODIFIED: use NeonKanbanBoard, NeonCard
src/app/dashboard/create/page.tsx  ← MODIFIED: use NeonProgressBar, NeonFormField
src/app/dashboard/blog-posts/page.tsx ← MODIFIED: use NeonBlogPostCard, NeonTopBar
src/app/dashboard/calendar/page.tsx ← MODIFIED: use NeonCard, NeonBadge
src/app/dashboard/chat/page.tsx    ← MODIFIED: use NeonButton, NeonInput
src/app/dashboard/personas/page.tsx ← MODIFIED: use NeonPersonaCard, NeonSearchBar
src/app/dashboard/rubrics/page.tsx ← MODIFIED: use NeonRubricCard
src/app/dashboard/knowledge/page.tsx ← MODIFIED: use neon components
src/app/dashboard/blog-posts/[id]/edit/page.tsx ← MODIFIED: convert from shadcn to neon
src/app/login/page.tsx             ← MODIFIED: use NeonGridBackground, NeonFormField
src/app/(public)/layout.tsx        ← MODIFIED: use NeonGridBackground, NeonScanlineOverlay

# ── Existing Constants ──
src/app/dashboard/constants.tsx    ← MODIFIED: import from @/constants/neon
src/features/dashboard/chat/constants.ts ← MODIFIED: import from @/constants/neon

# ── Feature Components ──
src/features/knowledge/components/* ← MODIFIED: 5 files (shadcn → neon)
src/features/blog/components/*     ← MODIFIED: 7 files (shadcn → neon)
src/features/chat/components/*     ← MODIFIED: 2 files (shadcn → neon)
src/features/workflow/components/* ← MODIFIED: 2 files (Label → NeonLabel)

# ── Stryker Config ──
stryker.conf.json                  ← MODIFIED: add neon component mutate targets (after baseline)
```

### 17.4 Files UNCHANGED (173 files — all backend logic, hooks, queries, API client, tests untouched)

```
# ── All hooks (business logic) ── Unchanged
src/features/create/hooks/use-editorial-workflow.ts
src/features/knowledge/hooks/use-documents.ts
src/features/blog/hooks/use-blog-posts.ts
src/features/persona/hooks/use-personas.ts
src/features/rubrics/hooks/use-rubrics.ts
src/features/chat/hooks/use-chat.ts
... (all other hooks)

# ── All queries (TanStack Query configuration) ── Unchanged
src/features/carousel/queries.ts
src/features/knowledge/queries.ts
src/features/chat/queries.ts
... (all other queries)

# ── All API client and lib ── Unchanged
src/lib/api-client.ts
src/lib/utils.ts
src/lib/sse-client.ts
... (all lib files)

# ── All existing Zod schemas ── Unchanged
src/schemas/carousel.ts
src/schemas/chat.ts
src/schemas/knowledge.ts

# ── All providers ── Unchanged
src/components/providers/*
src/components/language-switcher.tsx

# ── All i18n ── Unchanged
src/i18n/config.ts
src/i18n/request.ts
src/i18n/locales/*.json

# ── All admin components ── Unchanged
src/components/admin/*

# ── All middleware, robots, sitemap ── Unchanged
src/middleware.ts
src/app/robots.ts
src/app/sitemap.ts

# ── Blog/Create route groups ── Unchanged (already clean)
src/app/(blog)/*
src/app/(create)/*

# ── All test infrastructure ── Unchanged
src/test/setup.ts
src/test/mocks/*
src/test/utils.tsx
src/test/fixtures/*
```

### 17.5 File Change Summary

| Metric | Count |
|--------|-------|
| Files DELETED | 19 (old shadcn components + tests) |
| Files CREATED | ~66 (neon components + schemas + adapters + stories + features) |
| Files MODIFIED | ~21 (pages + layouts + constants + feature components) |
| Files UNCHANGED | ~173 (all hooks, queries, API, lib, providers, tests) |
| **Total file delta** | **~106 new/changed + 19 deleted = net +87 files** |
| **Total source files** | **~259 → ~327** |

---

## 18. Risk Register and Mitigations

### 18.1 Risk Matrix

| # | Risk | Likelihood | Impact | Phase | Mitigation Strategy |
|---|---|---|---|---|---|
| R01 | **Visual style mismatch**: New neon component looks different from mockup | Medium | Medium | All | Compare each component against shell.css mockup; screenshot before/after; Storybook visual regression |
| R02 | **Accidental functional break**: Converting inline styles accidentally removes an onClick handler or state | Low | Critical | 1-5 | Review checklist per file; `git diff` before commit to verify ONLY style changes; pair programming review |
| R03 | **Missing import after shadcn removal**: A file still imports from `@/components/ui` after the directory is deleted | Medium | High | 6 | Phase 6.1: automated `rg` check for zero shadcn imports BEFORE deleting directory; build will also fail on missing imports |
| R04 | **CSS variable name collision**: New `--color-neon-*` vars override existing Tailwind tokens | Low | High | 0 | Namespace with `neon-` prefix; verify no overlap with existing `--color-*` vars in globals.css |
| R05 | **Zod schema drift**: Component schema becomes out of sync with component implementation | Low | Medium | 0 | Inferred types (`z.infer`) automatically stay in sync; test validates prop types match |
| R06 | **Adapter mapping failure**: Backend API response shape changes but adapter is not updated | Low | High | 1-5 | Adapter tests with mock backend responses; integration tests in CI catch API contract changes |
| R07 | **Mutation score regression**: New components lower overall Stryker score below 80% break threshold | Medium | Medium | 6 | Run Stryker incrementally — add neon components to mutate list only after 80%+ baseline confirmed on business logic |
| R08 | **Bundle size increase**: 66 new files add significant bundle weight | Low | Medium | 0 | Neon components are tree-shakeable (ES module exports); estimate ~20-25 KB total gzipped; monitor with `npm run build -- --analyze` |
| R09 | **Chromatin/Storybook build failure**: Storybook doesn't work with existing Tailwind v4 config | Medium | Low | 0 | Test Storybook install in isolation first; use `--type nextjs` framework; configure `@tailwindcss/postcss` in preview.ts if needed |
| R10 | **Hydration error**: Layout change introduces client/server mismatch | Low | Critical | 1 | Test production build NOT dev server (Turbopack has caching issues); `npm run build` then `npm start` to test hydration |
| R11 | **Incomplete migration — forgotten file**: One file still references old shadcn classes like `text-muted-foreground` or `bg-gray-50` | Medium | Medium | 6 | Run automated detection script in Phase 6.1; also check with `rg -r "import" src/` for any missed imports |
| R12 | **Reduced-motion / accessibility regression**: Animations cause vestibular issues or keyboard traps | Low | High | 0 | Add `prefers-reduced-motion` media query; test all interactive elements with keyboard-only navigation; axe-core scan in CI |

### 18.2 Mitigation by Phase

#### Phase 0 Mitigations
- **R04 (CSS collision)**: All neon variables prefixed with `--color-neon-`, `--color-bg-`, `--color-text-` — distinct from existing shadcn `--color-primary-*`, `--color-gray-*` ranges
- **R05 (Schema drift)**: Types are inferred with `z.infer<typeof schema>` — any schema change automatically updates the TypeScript type. Tests pass mock data through the Zod parser to validate
- **R08 (Bundle size)**: Run `npx next build -- --analyze` after Phase 0 to establish baseline. Compare after all phases. Target: ≤25 KB gzipped for all neon components combined
- **R09 (Storybook)**: Install Storybook on a feature branch first. If Tailwind v4 has compatibility issues, configure `postcss` in `.storybook/main.ts` manually
- **R12 (Accessibility)**: Add `@media (prefers-reduced-motion: no-preference)` to all neon keyframes. Run `axe-core` in Storybook after every component creation

#### Phase 1-5 Mitigations (per-file conversion)
- **R01 (Visual mismatch)**: Before converting a page, take a screenshot. After converting, compare visually. For small differences, tweak inline; for large, revert and debug
- **R02 (Functional break)**: Use this checklist for EVERY file conversion:
  ```
  □ Same props interface (no added/removed props)
  □ Same state management (no new useState/useEffect)
  □ Same event handlers (onClick, onSubmit preserved)
  □ Same API calls preserved
  □ Same data bindings (ternary, loop, conditional rendering)
  □ Only changed: element tags, CSS classes, inline styles
  ```
- **R10 (Hydration)**: Run `npm run build && npm start` after each major page conversion. Test the page in the production server, not dev mode

#### Phase 6 Mitigations
- **R03 (Missing import)**: Run detection script in TWO passes:
  1. `rg "@/components/ui" src/ --include="*.tsx" --include="*.ts"` — expect 0 matches
  2. `rg "components/ui" src/ --include="*.tsx" --include="*.ts" | grep -v "neon-"` — expect 0 non-neon matches
- **R07 (Mutation regression)**: Before removing old components, run Stryker on current baseline. After removal, run again — score must not drop below 80%
- **R11 (Forgotten file)**: In addition to the automated script, manually check every directory in `src/app/dashboard/` and `src/features/` by opening each file and verifying no old shadcn classes remain

### 18.3 Rollback Plan

If any phase causes a build failure or visual regression that can't be fixed within 30 minutes:

```bash
# Option A: Revert the last commit
git revert HEAD --no-edit
git push

# Option B: Reset to last known good state (if uncommitted)
git checkout -- <affected-files>

# Option C: Full phase revert (if multiple commits)
git revert HEAD~N..HEAD --no-edit  # N = commits in the phase
```

### 18.4 Verification Gate per Phase

After each phase completes, the following MUST pass before moving to the next phase:

```bash
# Gate checklist — run these commands:
echo "=== BUILD ===" && npm run build 2>&1 | tail -3
echo "=== TYPECHECK ===" && npm run typecheck 2>&1 | tail -3
echo "=== LINT ===" && npm run lint 2>&1 | tail -3
echo "=== TESTS ===" && npm run test -- --run 2>&1 | tail -3
echo "=== COVERAGE ===" && npm run test:coverage 2>&1 | grep -E "Statements|Branches"
```

Expected output:
```
=== BUILD ===
✓ Compiled successfully
=== TYPECHECK ===
(no errors)
=== LINT ===
✔ No linting errors
=== TESTS ===
 Tests: XXX passed (XXX assertions)
=== COVERAGE ===
Statements: XX%
Branches: 90%+ (minimum)
```

### 18.5 Communication Plan

If a risk materializes:
1. **Stop work on the current phase immediately**
2. Document the issue: what caused it, when it was detected, and the mitigation applied
3. If the fix is simple (< 30 min), apply it and continue
4. If the fix is complex (> 30 min), revert the phase commits and re-plan the approach
5. Notify via the `#dev-frontend` channel (or equivalent)

| Component | dashboard/ | dashboard/ | dashboard/ | dashboard/workflow | dashboard/create | dashboard/ | dashboard/ | dashboard/ | dashboard/ | dashboard/ | dashboard/ | login/ | (public)/ | (public)/ | (blog)/ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | layout | page | analytics | | | calendar | chat | blog-posts | personas | rubrics | knowledge | | layout | page | blog |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NeonButton | | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | | | ✅ | ✅ | | ✅ | |
| NeonInput | | | ✅ | | ✅ | | ✅ | ✅ | ✅ | | ✅ | ✅ | | | |
| NeonTextarea | | | | | | | ✅ | ✅ | | | ✅ | | | | |
| NeonSelect | | | | | ✅ | | | | | | | | | | |
| NeonBadge | ✅ | | | ✅ | | ✅ | | ✅ | ✅ | ✅ | | | | ✅ | ✅ |
| NeonIcon | ✅ | ✅ | | | | ✅ | ✅ | | | | | | | ✅ | |
| NeonSpinner | | | ✅ | | | | ✅ | ✅ | | | ✅ | ✅ | | | |
| NeonLabel | | | | | ✅ | | | ✅ | | | ✅ | ✅ | | | |
| NeonSkeleton | | | | | | | ✅ | | | | ✅ | | | | |
| NeonLink | ✅ | | | | | | | | | | | | ✅ | ✅ | ✅ |
| NeonCard | | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | | ✅ | |
| NeonFormField | | | | | ✅ | | | ✅ | | | ✅ | ✅ | | | |
| NeonSearchBar | | | | | | | | | ✅ | | ✅ | | | | |
| NeonStatCard | | ✅ | ✅ | | | | | | | | | | | ✅ | |
| NeonProgressBar | | | | | ✅ | | | | | | | | | | |
| NeonBadgeGroup | | | | | | | | ✅ | ✅ | ✅ | | | | ✅ | |
| NeonToast | | ✅ | | ✅ | ✅ | | ✅ | ✅ | | | ✅ | ✅ | | | |
| NeonModal | | | | | | | | ✅ | | | ✅ | | | | |
| NeonDropdown | ✅ | | | | | | | ✅ | | | | | | | |
| NeonTab | | | (future) | | | | | | | | | | | | |
| NeonGridBackground | ✅ | | | | | | | | | | | ✅ | ✅ | | |
| NeonScanlineOverlay | ✅ | | | | | | | | | | | ✅ | ✅ | | |
| NeonSidebar | ✅ | | | | | | | | | | | | | | |
| NeonTopBar | | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | | | | | |
| NeonBreadcrumb | | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | | | | | |
| NeonStatsGrid | | ✅ | ✅ | | | | | | | | | | | ✅ | |
| NeonActivityList | | ✅ | | | | | | | | | | | | | |
| NeonKanbanBoard | | | | ✅ | | | | | | | | | | | |
| NeonPersonaCard | | | | | | | | | ✅ | | | | | | |
| NeonRubricCard | | | | | | | | | | ✅ | | | | | |
| NeonBlogPostCard | | | | | | | | ✅ | | | | | | ✅ | |
| NeonPagination | | | | | | | | ✅ | | | ✅ | | | | |

---

## Timeline Summary

| Phase | Tasks | Est. Time | Dependencies |
|---|---|---|---|
| Phase 0: Foundation | 5 tasks (tokens + 10 atoms + 10 molecules + 12 organisms + Storybook) | 6-8 hours | None |
| Phase 1: Refactor Converted Pages | 7 tasks | 3-4 hours | Phase 0 |
| Phase 2: Analytics Page | 1 task | 1-2 hours | Phase 0 |
| Phase 3: Knowledge Pages | 2 tasks (5 feature files + 2 page files) | 2-3 hours | Phase 0 |
| Phase 4: Blog Edit + Errors | 2 tasks | 1-2 hours | Phase 0 |
| Phase 5: Feature Components | 3 tasks (11 files) | 3-4 hours | Phase 0 |
| Phase 6: Cleanup | 6 tasks | 2-3 hours | Phases 1-5 |

**Total**: ~18-26 hours (2-3 days focused work)
