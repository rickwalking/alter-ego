# Implementation Plan: Neon Shell Design System Integration

> **NOTE**: This file has been superseded by the detailed step-by-step plan at
> `docs/plans/neon-shell-migration-complete.md`
> See that file for the complete migration strategy, reusable component architecture, risk management, and orphan code cleanup procedure.

## Overview
This plan implements the production-hardened redesign mockups from `frontend/public/redesign/` into the actual Next.js application, applying the Neon Shell design system consistently across **dashboard, calendar, workflow board, and create carousel** pages.

**KEY CONSTRAINT - VISUAL-ONLY IMPLEMENTATION**: This is a **visual-only implementation**. No business logic, API contracts, data structures, or functionality should change. All modifications are cosmetic styling changes using the existing Neon Shell design system. Any deviation from this principle is a **critical failure**.

## Styling Strategy: Tailwind CSS v4 + Neon Shell Tokens

This project uses **Tailwind CSS v4** (not v3) as its primary styling mechanism. Key facts:

### Tailwind v4 Specifics
- **No `tailwind.config.ts`** — Tailwind v4 uses CSS-based configuration via `@theme` directive in `globals.css`
- **PostCSS plugin**: `@tailwindcss/postcss` (not the old `tailwindcss` package)
- **All tokens defined in `frontend/src/app/globals.css`** using `@theme {}` block:
  - Custom colors: `primary-*`, `success`, `warning`, `error`, `info`, `gray-*`, `brand-*`
  - Semantic tokens: `background`, `foreground`, `card`, `popover`, `muted`, `accent`, `border`, `ring`, etc.
  - Font families: `Inter` (sans), `JetBrains Mono` (mono) via CSS variables
  - Border radius: `sm`, `md`, `lg`, `xl`, `2xl`
  - Animations: `fade-in`, `slide-up`, `slide-down`
- **No `@tailwind` directives** — Uses `@import "tailwindcss"` instead

### Shell.css Status
- **shell.css is NOT imported in the app** — it lives at `frontend/public/redesign/shell.css` as a **static mockup reference only**
- The Neon Shell visual identity (cyan/magenta/amber/teal accents, grid backgrounds, scanlines) must be recreated using Tailwind utilities
- Use `cn()` utility from `@/lib/utils` (wraps `clsx` + `tailwind-merge`) for conditional class merging

### Implementation Approach
1. **Tailwind utilities** for all layout, spacing, typography, and colors
2. **Custom CSS in globals.css** (via `@theme` or `@layer`) for complex Neon Shell effects (scanline overlay, grid background, glows)
3. **`cn()` utility** for combining conditional Tailwind classes
4. **Existing Tailwind tokens** for colors (use `bg-card`/`text-muted-foreground` etc. instead of raw hex values from shell.css)
5. **No inline `<style>` blocks** in components — all CSS goes in globals.css
6. **No shell.css import** — the mockup CSS is reference material only

### Color Mapping: Shell.css → Tailwind Tokens

| Shell CSS Token | Tailwind Equivalent | Notes |
|----------------|---------------------|-------|
| `--bg-deep: #060a12` | `bg-gray-950` | Closest match |
| `--bg-surface: #0a0f1e` | `bg-gray-950` (slightly lighter) | May need custom token |
| `--bg-card: #0d1324` | `bg-card` | Maps to `var(--color-card)` |
| `--bg-elevated: #111a30` | `bg-gray-900` | Close match |
| `--cyan: #00d4ff` | `text-primary-400` (approx) | Custom token needed for exact match |
| `--magenta: #ff2770` | No existing match | Custom token needed |
| `--amber: #f59e0b` | `text-warning` (approx) | Close to `warning` |
| `--teal: #0ac5a8` | No existing match | Custom token needed |
| `--text: rgba(255,255,255,0.88)` | `text-foreground` / `text-gray-50` | |
| `--text-muted: rgba(255,255,255,0.55)` | `text-muted-foreground` | |
| `--text-dim: rgba(255,255,255,0.3)` | `text-gray-400` | Close match |

**Decision**: For Phase 1, use existing Tailwind semantic tokens (`bg-card`, `text-foreground`, `text-muted-foreground`, `border`). Add Neon Shell accent colors (`cyan`, `magenta`, `teal`) as CSS custom properties in globals.css when needed for exact visual matching.

## Current State
- ✅ Design mockups created and hardened in `/frontend/public/redesign/`
- ✅ Shell CSS design system extracted in `shell.css` (reference only — not imported)
- ✅ Tailwind CSS v4 confirmed as primary styling mechanism
- ✅ `cn()` utility confirmed in `src/lib/utils.ts`
- ✅ Real data structures validated from backend models
- ⏳ Next.js components need visual updates to match mockups

## Priority Order
1. **Dashboard** (First - establishes design system baseline)
2. **Calendar** (Content scheduling view)
3. **Workflow Board** (Kanban pipeline view)
4. **Create Carousel** (Form interface)

---

## Dashboard Implementation (PRIORITY: HIGH)

### Target Component
- **File**: `frontend/src/app/(dashboard)/page/page.tsx` (create as App Router index page in `(dashboard)/page/` directory)
- **Mockup**: `frontend/public/redesign/dashboard.html`
- **Approach**: Use Tailwind CSS v4 utilities + `cn()` for all styling. shell.css classes serve as visual reference only.

### Data Structure (static for visual-only implementation)
```typescript
interface DashboardStats {
  activeCarousels: number;
  publishedPosts: number;
  processing: number;
  scheduled: number;
}

interface ActivityItem {
  id: string;
  title: string;
  description: string;
  timeAgo: string;
  type: 'carousel_published' | 'blog_draft' | 'workflow_approved' | 'persona_created' | 'scheduled';
}
```

### Visual Components to Implement

All components use **Tailwind CSS v4 utility classes** and **`cn()`** for conditional styling. No shell.css classes will be referenced in the actual components.

#### 1. Stats Grid (4 cards)
```typescript
interface StatCardProps {
  label: string;
  value: string;
  change?: { value: string; trend: 'up' | 'down' };
  icon: React.ReactNode;
}
```

#### 2. Quick Actions (3 cards)
```typescript
interface QuickActionCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
}
```

#### 3. Recent Activity (left column)
```typescript
interface ActivityListProps {
  activities: ActivityItem[];
}
```

#### 4. Upcoming Schedule (right column)
```typescript
interface ScheduleListProps {
  activities: ActivityItem[];
}
```

### Acceptance Criteria
- [ ] Stats grid displays 4 cards with correct icons and colors
- [ ] Quick actions show 3 cards with hover effects (border highlight, shadow)
- [ ] Recent activity shows list with colored dots and timestamps
- [ ] Upcoming schedule shows scheduled items in same format
- [ ] Responsive grid: 2 cols desktop, 1 col mobile
- [ ] Focus-visible on all interactive elements (2px cyan outline)
- [ ] Text overflow protection applied to all text containers
- [ ] No functional changes to existing data or APIs
- [ ] All stat values render correctly from existing data source
- [ ] Activity items preserve existing time formatting

### Gherkin Scenarios for QA Agent

```gherkin
Feature: Dashboard Visual Update

  Scenario Outline: Stats grid displays correctly
    Given the dashboard page is loaded
    When I view the stats section
    Then I see exactly 4 stat cards
    And each card has an icon with color "<color>"
    And the stat value displays as "<value>"
    And the label displays as "<label>"

    Examples:
      | color  | value   | label          |
      | cyan   | 24      | Active Carousels |
      | magenta | 87     | Published Posts |
      | teal   | 6      | Processing    |
      | amber  | 11     | Scheduled     |

  Scenario: Quick actions show hover effects
    Given I am on the dashboard page
    When I hover over a quick action card
    Then the card border highlights in cyan
    And a subtle shadow appears
    And the card transforms up 2px
    And I can still click the card

  Scenario: Activity list shows recent events
    Given the dashboard page is loaded
    When I view the recent activity section
    Then I see activity items with colored dots
    And each item has title, description, and timestamp
    And activity items are vertically stacked
    And the first item has a green dot

  Scenario: Responsive layout works on mobile
    Given I am on the dashboard page
    When I resize the viewport to 768px width
    Then the grid becomes single column
    And all content remains readable
    And stat cards stack vertically

  Scenario: Focus-visible states work correctly
    Given I am on the dashboard page
    When I tab to the search input
    Then a 2px cyan outline appears
    And the outline is offset by 2px
    And the outline has 4px border-radius

  Scenario: Stats data remains functional
    Given the dashboard page is loaded
    When I view the active carousels stat
    Then the value displays statically
    And the stat does not update on interaction
    And no API requests are made
```

### Safeguards Against Functional Changes
```typescript
// SAFEGUARD 1: Data source unchanged - only styling changes
// Existing component:
const statCards = [
  { label: 'Active Carousels', value: stats.activeCarousels, ... },
  // ... existing data binding
];

// New implementation must preserve:
// - All data binding expressions
// - All event handlers (onClick, etc.)
// - All API calls
// Only change: CSS classes, colors, spacing

// SAFEGUARD 2: Visual regression testing
// Before committing, run:
// npm run test:visual -- --grep=Dashboard
// This ensures no layout shifts or broken functionality

// SAFEGUARD 3: Code review checklist
// - [ ] No prop changes to existing components
// - [ ] No state changes
// - [ ] No API call changes
// - [ ] Only CSS class additions/modifications
// - [ ] No TypeScript type changes
```

### Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Stats data source changes | High | Medium | Extract all stats to constant, verify data shape before styling |
| Activity list API changes | Medium | Low | Wrap activity data in separate component, test with mock data |
| Icon set changes | Low | Low | Use inline SVG icons from mockup, replace immediately if needed |
| Responsive breakpoints differ | Low | Medium | Test on actual devices, not just browser dev tools |
| Color contrast fails WCAG AA | High | Low | Run contrast checker on all text combinations |
| Layout shift breaks existing UI | Medium | Medium | Test in staging environment before deploying |

---

## Calendar Implementation

### Target Component
- **File**: `frontend/src/features/workflow/components/content-calendar-view.tsx`
- **Mockup**: `frontend/public/redesign/calendar.html`

### Data Structure (from `ContentCalendarService`)
```typescript
interface CalendarEvent {
  id: string;
  content_type: "carousel" | "blog_post";
  title: string;
  status: string;
  event_date: string; // ISO format
  phase?: string;
  phase_status?: string;
}
```

### Acceptance Criteria
- [ ] 7-day calendar grid with month navigation
- [ ] Calendar events show content type badge (carousel/blog)
- [ ] Status badges display (published/awaiting_human/in_progress)
- [ ] Phase labels on events
- [ ] Legend for content types and statuses
- [ ] Responsive grid layout
- [ ] Focus-visible states on all interactive elements
- [ ] No functional changes to calendar logic

### Gherkin Scenarios for QA Agent

```gherkin
Feature: Calendar Visual Update

  Scenario: Calendar grid displays correctly
    Given I am on the calendar page
    When I view the calendar grid
    Then I see 7 day headers (Sun-Sat)
    And the grid spans all days
    And today's date is highlighted

  Scenario: Calendar events display with badges
    Given I am on the calendar page
    When I view events on a day
    Then I see content type badges (carousel/blog)
    And status badges (published/awaiting_human)
    And phase labels are visible

  Scenario: Legend shows all categories
    Given I am on the calendar page
    When I view the legend section
    Then I see color indicators for content types
    And color indicators for statuses
    And legend items are clickable

  Scenario: Responsive calendar works on mobile
    Given I am on the calendar page
    When I resize to mobile viewport
    Then the calendar remains readable
    And events are not cut off
```

---

## Workflow Board Implementation

### Target Component
- **File**: `frontend/src/features/workflow/components/workflow-kanban-board.tsx`
- **Mockup**: `frontend/public/redesign/workflow.html`

### Data Structure (from `CarouselWorkflow` constants)
```typescript
interface WorkflowCard {
  id: string;
  title: string;
  description: string;
  phase: string;
  phase_status: string;
  assignee?: string;
}

interface WorkflowColumn {
  phase: string;
  status: string;
}
```

### Acceptance Criteria
- [ ] 6-column Kanban board (brief excluded - auto-validated)
- [ ] Columns: Research → Outline → Content → Design → Images → Final Review
- [ ] Approval gate badges with correct colors
- [ ] Phase badges on cards
- [ ] Card hover states with border highlight
- [ ] Responsive grid (6 → 4 → 2 → 1 cols)
- [ ] Focus-visible support
- [ ] No functional changes to workflow logic

### Gherkin Scenarios for QA Agent

```gherkin
Feature: Workflow Board Visual Update

  Scenario: Kanban board shows 6 columns
    Given I am on the workflow board page
    When I view the board
    Then I see exactly 6 columns
    And column headers are uppercase
    And column counts are displayed

  Scenario: Approval badges show correct colors
    Given I am on the workflow board page
    When I view a card with status "pending"
    Then the badge is orange
    And I view a card with status "approved"
    Then the badge is green

  Scenario: Cards have hover effects
    Given I am on the workflow board page
    When I hover over a card
    Then the border highlights in cyan
    And the background lightens
    And the card does not lose focus

  Scenario: Responsive columns work correctly
    Given I am on the workflow board page
    When I resize to 1200px width
    Then I see 4 columns
    When I resize to 800px width
    Then I see 2 columns
    When I resize to 500px width
    Then I see 1 column
```

---

## Create Carousel Implementation

### Target Components
- **File**: `frontend/src/features/create/components/topic-form.tsx`
- **Mockup**: `frontend/public/redesign/create.html`

### Form Fields (5 fields, already implemented)
1. Topic (max 500 chars)
2. Audience (max 500 chars)
3. Brief/Niche (max 200 chars)
4. Theme (enum: auto, cybersecurity, ai_competition, developer_skills, source_code, social_engineering)
5. Image Preset (model + style combo)

### Acceptance Criteria
- [ ] 7-step progress bar displays correctly
- [ ] Left panel shows 3 form sections
- [ ] Right sidebar shows project summary and generation report
- [ ] Select inputs are visible with proper styling
- [ ] Form validation displays char limits
- [ ] Generation report shows 6 phase artifacts
- [ ] No functional changes to form submission

### Gherkin Scenarios for QA Agent

```gherkin
Feature: Create Carousel Visual Update

  Scenario: Form fields display correctly
    Given I am on the create carousel page
    When I view the form
    Then I see 5 input fields
    And each field has a label with max length indicator
    And the topic field allows 500 characters

  Scenario: Progress bar shows workflow steps
    Given I am on the create carousel page
    When I view the progress bar
    Then I see 7 steps (Brief to Publish)
    And the first step is marked as active
    And subsequent steps are marked as pending

  Scenario: Select inputs are visible
    Given I am on the create carousel page
    When I view the theme select dropdown
    Then the dropdown is clearly visible
    And the dropdown has a cyan border
    And I can click to open the options

  Scenario: Generation report shows artifacts
    Given I am on the create carousel page
    When I view the generation report panel
    Then I see 6 phase artifacts
    And each artifact has a status indicator
    And the status is displayed as "pending"
```

---

## Phase 1: Design System Integration

### Tasks

#### Task 1.1: Analyze Existing Design System
- [ ] Read `shell.css` to understand current tokens
- [ ] Read `frontend/tailwind.config.ts` to understand current setup
- [ ] Identify conflicts or overlaps
- [ ] Document current design tokens

**Acceptance Criteria**:
- [ ] Complete inventory of existing design tokens
- [ ] List of conflicts between shell.css and Tailwind
- [ ] Recommended migration strategy

#### Task 1.2: Extract Shell CSS to Tailwind
- [ ] Create custom color palette in Tailwind config
- [ ] Extract spacing tokens
- [ ] Extract typography scale
- [ ] Add custom components as Tailwind utilities

**Acceptance Criteria**:
- [ ] All shell.css colors available in Tailwind
- [ ] All shell.css spacing tokens available in Tailwind
- [ ] Custom components defined as Tailwind utilities
- [ ] shell.css preserved as fallback

#### Task 1.3: Update Global Styles
- [ ] Apply text overflow protection globally
- [ ] Add focus-visible styles
- [ ] Add flex overflow protection
- [ ] Add reduced-motion guards

**Acceptance Criteria**:
- [ ] All text containers have overflow protection
- [ ] Focus-visible styles work on all interactive elements
- [ ] Flex containers have overflow protection
- [ ] Reduced motion respected for accessibility

### Acceptance Criteria for Phase 1
- [ ] Design system tokens extracted to Tailwind
- [ ] No breaking changes to existing components
- [ ] shell.css preserved for non-Tailwind elements
- [ ] All global hardening styles applied
- [ ] QA agent can validate visual consistency

### Gherkin Scenarios for QA Agent (Phase 1)

```gherkin
Feature: Design System Integration

  Scenario: Color palette is available in Tailwind
    Given the tailwind config is updated
    When I inspect the cyan color
    Then the color is available as a utility class
    And the color matches the shell.css definition

  Scenario: Focus-visible works on all elements
    Given I am on any page
    When I tab to an interactive element
    Then a 2px cyan outline appears
    And the outline is offset by 2px

  Scenario: Text overflow is handled correctly
    Given I am on a page with long text
    When the text exceeds container width
    Then the text wraps correctly
    And no horizontal scroll appears

  Scenario: Reduced motion is respected
    Given I disable animations in browser settings
    When I view animated elements
    Then animations are disabled
    And transitions are removed
```

### Risks & Mitigations (Phase 1)

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tailwind config conflicts | High | Test all color tokens in isolation before merging |
| Breaking changes to components | High | Create separate branch, test each component individually |
| Performance regression | Medium | Run Lighthouse before and after |
| CSS specificity issues | Medium | Use CSS custom properties, not direct overrides |

---

## Safeguards Against Functional Changes

### Code Review Checklist
```markdown
- [ ] No prop changes to existing components
- [ ] No state changes
- [ ] No API call changes
- [ ] Only CSS class additions/modifications
- [ ] No TypeScript type changes
- [ ] All data bindings preserved
- [ ] All event handlers preserved
- [ ] No new dependencies
- [ ] No backend changes
```

### Automated Checks
```bash
# Before each commit:
npm run typecheck     # No type errors
npm run lint          # No linting errors
npm run test          # All tests pass
npm run test:visual   # Visual regression tests pass

# After implementation:
npm run build         # No build errors
npm run build:watch   # Verify running correctly
```

### Manual Testing Checklist
- [ ] Test on Chrome, Firefox, Safari
- [ ] Test on mobile (iOS Safari, Chrome Mobile)
- [ ] Test with screen reader
- [ ] Test keyboard navigation
- [ ] Test with high contrast mode

---

## Timeline Estimate

| Phase | Tasks | Estimated Time | Dependencies |
|-------|-------|----------------|--------------|
| Phase 1: Design System Integration | 3 tasks | 4-5 hours | None |
| Dashboard Implementation | 4 tasks | 4-5 hours | Phase 1 |
| Calendar Implementation | 3 tasks | 3-4 hours | Dashboard |
| Workflow Board Implementation | 3 tasks | 3-4 hours | Dashboard |
| Create Carousel Implementation | 4 tasks | 4-5 hours | Dashboard |
| Hardening & Accessibility | 3 tasks | 2-3 hours | All implementations |
| Testing & QA | 2 tasks | 3-4 hours | All implementations |

**Total**: 23-27 hours (3-4 days part-time)

---

## Next Steps

1. **Review the detailed plan at `docs/plans/neon-shell-migration-complete.md`**
2. **Create worktree from `feat/design-hardening` branch**
3. **Start with Phase 0 (Design Token Infrastructure)**
4. **Implement phases sequentially**
5. **QA agent validates each phase**
6. **Final hardening pass**

---

## Full Plan Reference
See `docs/plans/neon-shell-migration-complete.md` for the COMPLETE plan including:

### Architecture
- ✅ **Atomic Design** (10 Atoms → 10 Molecules → 12 Organisms → 4 Templates)
- ✅ **Compound Component pattern** (NeonTabs, NeonSelect via Context API)
- ✅ **CVA** (`class-variance-authority`) for variant management
- ✅ **CSS Custom Properties** + **TypeScript Constants** dual theming

### Specifications
- ✅ **Zod schemas** per component in `src/schemas/` (NeonButtonProps, NeonBadgeProps, NeonCardProps, NeonKanbanProps, etc.)
- ✅ **Full props interfaces** with TypeScript types inferred from Zod
- ✅ **Component usage map** — every component mapped to every page
- ✅ **Dependency graph** — which components compose which

### Testing
- ✅ **Gherkin `.feature` files** per component (NeonButton: 17 scenarios)
- ✅ **Test implementation** with Gherkin-style `describe`/`it` patterns
- ✅ **Edge cases** per component (disabled+loading, empty states, boundary values, ref forwarding)
- ✅ **Mutation testing levels** (NeonButton: 90%, NeonCard: 85%, NeonKanbanBoard: 75%)
- ✅ **Stryker config** updates with component mutations added after baseline

### Migration Steps
- ✅ **7 phases** with acceptance criteria per task
- ✅ **Bottom-up conversion** — atoms → molecules → organisms → pages
- ✅ **Zero functional changes** — visual-only rule with checklist per file
- ✅ **Where each component is used** — detailed per-page matrix

### Cleanup
- ✅ **Orphan code detection script** (bash)
- ✅ **Complete deletion inventory** (19 old component files)
- ✅ **Test mock removal** procedure
- ✅ **Color constant consolidation** plan
- ✅ **CI safeguards** per CLAUDE.md rules

---

## Appendix A: Mockup File Locations

| Page | Mockup File | Shell.css |
|------|-------------|-----------|
| Dashboard | `frontend/public/redesign/dashboard.html` | `frontend/public/redesign/shell.css` |
| Calendar | `frontend/public/redesign/calendar.html` | `frontend/public/redesign/shell.css` |
| Workflow Board | `frontend/public/redesign/workflow.html` | `frontend/public/redesign/shell.css` |
| Create Carousel | `frontend/public/redesign/create.html` | `frontend/public/redesign/shell.css` |

## Appendix B: Real Component Locations

| Page | Real Component | Data Source |
|------|----------------|-------------|
| Dashboard | `frontend/src/app/(dashboard)/page.tsx` | Dashboard API |
| Calendar | `frontend/src/features/workflow/components/content-calendar-view.tsx` | `ContentCalendarService` |
| Workflow Board | `frontend/src/features/workflow/components/workflow-kanban-board.tsx` | Workflow state |
| Create Carousel | `frontend/src/features/create/components/topic-form.tsx` | Form constants |

## Appendix C: Design System Colors

```css
--bg-deep: #060a12;
--bg-surface: #0a0f1e;
--bg-card: #0d1324;
--bg-elevated: #111a30;
--cyan: #00d4ff;
--cyan-dim: rgba(0,212,255,0.15);
--magenta: #ff2770;
--magenta-dim: rgba(255,39,112,0.15);
--amber: #f59e0b;
--teal: #0ac5a8;
--purple: #a855f7;
--text: rgba(255,255,255,0.88);
--text-muted: rgba(255,255,255,0.55);
--text-dim: rgba(255,255,255,0.3);
```
