# Story 2.1: UX Design Alignment

Status: backlog

## Story

As a user,
I want the frontend UI to match the original UX design specifications,
so that I experience the intended liquid glass morphism aesthetic with proper hover effects, animations, and visual polish.

## Acceptance Criteria

1. ChatInterface is wrapped in Card component with glass-card styling matching LandingPage structure
2. Glass cards display shimmer animation overlay using ::before pseudo-element
3. Glass cards display ambient gradient glow border on hover using ::after pseudo-element
4. Buttons have ripple animation on hover with expanding circle effect (::before pseudo-element)
5. Buttons are visibly larger with padding increased to match UX specs (0.85rem 2rem)
6. Input focus state matches UX design with enhanced glow and transform
7. All hover effects match ux-liquid-glass-themes.html Cyber Purple theme specifications
8. Visual comparison between implementation and UX design file confirms alignment

## Tasks / Subtasks

- [ ] **Wrap ChatInterface in Card Component** (AC: #1)
  - [ ] Import Card, CardContent from @/components/ui/card
  - [ ] Wrap chat messages and input area in Card component
  - [ ] Apply glass-card className to Card
  - [ ] Adjust internal layout and spacing to work within Card
  - [ ] Test responsive behavior with Card wrapper

- [ ] **Implement Glass Card Shimmer Animation** (AC: #2)
  - [ ] Update .glass-card::before in index.css with shimmer overlay
  - [ ] Add linear gradient (45deg, transparent 30%, rgba(255,255,255,0.05) 50%, transparent 70%)
  - [ ] Set position absolute, full width/height coverage
  - [ ] Apply shimmer animation (8s linear infinite)
  - [ ] Set pointer-events: none to prevent interaction interference
  - [ ] Verify shimmer appears on all .glass-card elements

- [ ] **Implement Glass Card Ambient Glow Border** (AC: #3)
  - [ ] Add .glass-card::after in index.css with gradient border effect
  - [ ] Create gradient: linear-gradient(135deg, rgba(167,139,250,0.3) 0%, rgba(6,182,212,0.3) 100%)
  - [ ] Use mask-composite to create border-only effect
  - [ ] Set opacity: 0 by default, opacity: 1 on hover
  - [ ] Add transition for smooth fade-in (0.5s ease)
  - [ ] Test glow appears on hover without flickering

- [ ] **Implement Button Ripple Effect** (AC: #4)
  - [ ] Update .glass-button-primary::before in index.css
  - [ ] Add ripple circle starting at center (width: 0, height: 0)
  - [ ] Set background: rgba(255,255,255,0.3)
  - [ ] Add transform: translate(-50%, -50%)
  - [ ] On hover, expand to width: 300px, height: 300px
  - [ ] Add transition: width 0.6s ease, height 0.6s ease
  - [ ] Test ripple animation on button hover

- [ ] **Increase Button Size** (AC: #5)
  - [ ] Update .btn class in index.css to padding: 0.85rem 2rem
  - [ ] Update .glass-button-primary padding if needed
  - [ ] Verify Send button in ChatInterface uses updated sizing
  - [ ] Test button size on desktop and mobile viewports
  - [ ] Confirm button text remains centered

- [ ] **Enhance Input Focus Effects** (AC: #6)
  - [ ] Update .glass-input:focus in index.css
  - [ ] Match UX design: border-color: #c4b5fd (Cyber Purple accent)
  - [ ] Update box-shadow to match UX: 0 8px 32px rgba(139,92,246,0.4), 0 0 60px rgba(139,92,246,0.3)
  - [ ] Verify transform: translateY(-2px) is applied
  - [ ] Test focus state with keyboard navigation (Tab key)
  - [ ] Ensure focus ring is visible for accessibility

- [ ] **Update Sweep Animation on Glass Cards** (AC: #7)
  - [ ] Review existing .glass-card:hover::before animation
  - [ ] Match UX design sweep: left: -100% to left: 100%
  - [ ] Verify transition: left 0.6s ease
  - [ ] Test sweep animation triggers on hover
  - [ ] Ensure animation doesn't interfere with content

- [ ] **Visual Comparison & Verification** (AC: #8)
  - [ ] Open ux-liquid-glass-themes.html in browser (Cyber Purple theme)
  - [ ] Open running application side-by-side
  - [ ] Compare card hover effects (shimmer, glow, sweep)
  - [ ] Compare button hover effects (ripple, scale, glow)
  - [ ] Compare input focus effects (glow, border, transform)
  - [ ] Take screenshots documenting alignment
  - [ ] Document any remaining minor differences

## Dev Notes

### UX Design Reference

**File:** `/docs/ux-liquid-glass-themes.html`
**Theme:** Cyber Purple (Theme 1)
**Key Sections:**
- Lines 129-191: .theme-card styles (shimmer, glow border, hover effects)
- Lines 334-371: .glass-card styles (background, hover, sweep animation)
- Lines 393-440: .btn styles (ripple effect, hover transform)
- Lines 526-550: .glass-input styles (focus state, glow, transform)

### Components to Modify

**Priority 1: ChatInterface Component**
- File: `frontend/src/components/ChatInterface.tsx`
- Current structure: Direct div wrapper without Card component
- Required: Wrap in Card component like LandingPage pattern
- Maintain ARIA attributes added in Story 3

**Priority 2: CSS Utilities (index.css)**
- File: `frontend/src/index.css`
- Lines 91-108: .glass-card (add ::before shimmer, ::after glow)
- Lines 110-136: .glass-input (enhance focus state)
- Lines 138-166: .glass-button-primary (add ::before ripple)
- Lines 393-404: .btn base class (increase padding)

**Priority 3: Visual Verification**
- Compare with ux-liquid-glass-themes.html Theme 1 (Cyber Purple)
- Focus on hover interactions and animations
- Ensure all effects work without JavaScript (CSS only)

### Color Values from UX Design (Cyber Purple)

**Primary Colors:**
- Primary: `#8b5cf6`
- Accent: `#c4b5fd`
- Background: `#0a0a0f`

**Glass Effect Values:**
- Card background: `rgba(255, 255, 255, 0.04)`
- Card backdrop-filter: `blur(30px) saturate(180%)`
- Card border: `1.5px solid rgba(255, 255, 255, 0.12)`
- Hover border: `rgba(255, 255, 255, 0.2)`

**Shadow/Glow Values:**
- Card shadow: `0 8px 32px rgba(0, 0, 0, 0.3)`
- Hover shadow: `0 12px 48px rgba(0, 0, 0, 0.4)`
- Purple glow: `0 0 40px rgba(139, 92, 246, 0.4)`
- Hover purple glow: `0 0 60px rgba(139, 92, 246, 0.5)`

### Animation Specifications

**Shimmer (lines 24-27 in UX):**
```css
@keyframes shimmer {
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
}
```

**Card ::before Shimmer Overlay (lines 143-159):**
```css
.theme-card::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(
    45deg,
    transparent 30%,
    rgba(255, 255, 255, 0.05) 50%,
    transparent 70%
  );
  animation: shimmer 8s linear infinite;
  pointer-events: none;
}
```

**Card ::after Glow Border (lines 162-178, 189-191):**
```css
.theme-card::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 32px;
  padding: 2px;
  background: linear-gradient(135deg,
    rgba(167, 139, 250, 0.3) 0%,
    rgba(6, 182, 212, 0.3) 100%);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.5s ease;
  z-index: -1;
}

.theme-card:hover::after {
  opacity: 1;
}
```

**Button Ripple (lines 407-423):**
```css
.btn::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  transition: width 0.6s ease, height 0.6s ease;
}

.btn:hover::before {
  width: 300px;
  height: 300px;
}
```

### Testing Strategy

**Visual Testing:**
1. Open ux-liquid-glass-themes.html in browser
2. Open application in adjacent window
3. Test each hover effect side-by-side:
   - Card shimmer animation (should be subtle, continuous)
   - Card glow border on hover (should fade in smoothly)
   - Button ripple on hover (should expand from center)
   - Input focus glow (should be prominent purple)

**Responsive Testing:**
- Test on desktop (1920x1080)
- Test on tablet (768px width)
- Test on mobile (375px width)
- Verify animations don't impact performance

**Accessibility Testing:**
- Verify animations respect prefers-reduced-motion
- Ensure hover effects don't interfere with ARIA attributes from Story 3
- Test keyboard navigation still works with new Card wrapper
- Confirm focus indicators remain visible

### Learnings from Story 3

**From Story 3 (Accessibility Improvements - Status: done)**

**Key Points:**
- ChatInterface already has comprehensive ARIA labels (aria-label, aria-describedby, aria-live, aria-busy)
- Wrapping in Card must preserve all ARIA attributes
- ScrollArea component already has role="log" and aria-live="polite"
- Screen reader-only help text uses .sr-only class (must not conflict with new animations)
- Focus indicators must remain visible (3:1 contrast ratio minimum)

**Files to Preserve:**
- `frontend/src/components/ChatInterface.tsx` - Keep all ARIA attributes intact
- `frontend/src/index.css` - .sr-only utility must not be affected by new animations

**Important:** Test with screen reader after changes to ensure ARIA functionality not broken by Card wrapper.

[Source: stories/story-project-improvements-3.md#Completion-Notes]

### Browser Compatibility

**Target Browsers:**
- Chrome 120+ ✓
- Firefox 120+ ✓
- Safari 17+ ✓
- Edge 120+ ✓

**CSS Features Used:**
- backdrop-filter (full support in all modern browsers)
- mask-composite (needs -webkit- prefix for Safari)
- ::before/::after pseudo-elements (universal support)
- CSS animations (universal support)

### Performance Considerations

- Backdrop-filter is GPU-accelerated (minimal performance impact)
- Animations use transform (GPU-accelerated)
- Shimmer animation is continuous but lightweight
- Ripple effect only triggers on hover
- Consider adding `will-change` for hover transforms if performance issues arise

### References

**UX Design File:**
- Location: `/docs/ux-liquid-glass-themes.html`
- Theme: Cyber Purple (Theme 1, lines 730-796)
- Components: Live working examples with hover effects

**CSS Specifications:**
- Glassmorphism: https://css-tricks.com/glassmorphism-css/
- mask-composite: https://developer.mozilla.org/en-US/docs/Web/CSS/mask-composite
- backdrop-filter: https://developer.mozilla.org/en-US/docs/Web/CSS/backdrop-filter

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

<!-- Model name will be added by dev agent -->

### Debug Log References

<!-- Any debug logs or issues will be documented here -->

### Completion Notes List

<!-- Dev agent will add completion notes here -->

### File List

<!-- Modified files will be listed here by dev agent -->
