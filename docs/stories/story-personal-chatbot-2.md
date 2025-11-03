# Story: Frontend Chat Interface

Status: Ready-for-dev

## Story

As a recruiter,
I want an intuitive chat interface on a landing page,
so that I can interact with the AI chatbot and learn about the candidate's background.

## Acceptance Criteria

1. React TypeScript application runs on localhost:5173 with Vite dev server
2. Shadcn UI component library installed and configured
3. Landing page displays project introduction with Card component
4. Chat interface displays message history with ScrollArea component
5. Users can type and send messages using Input and Button components
6. Messages display with Avatar components for user/AI distinction
7. API client successfully communicates with backend at localhost:8000
8. Loading state displays while waiting for AI response
9. Error messages display when backend is unavailable
10. Application is responsive on mobile (375px+) and desktop
11. Tailwind CSS properly configured and styling applied
12. Auto-scroll to latest message when new message arrives

## Tasks / Subtasks

- [ ] **Frontend Project Setup** (AC: #1, #11)
  - [ ] Create frontend directory
  - [ ] Run `npm create vite` with React TypeScript template
  - [ ] Install and configure Tailwind CSS
  - [ ] Install PostCSS and Autoprefixer
  - [ ] Configure tailwind.config.js

- [ ] **Shadcn UI Setup** (AC: #2)
  - [ ] Run `npx shadcn@latest init`
  - [ ] Select: Default style, Neutral colors, CSS variables: yes
  - [ ] Add button component
  - [ ] Add card component
  - [ ] Add input component
  - [ ] Add scroll-area component
  - [ ] Add avatar component
  - [ ] Create src/lib/utils.ts with cn() helper

- [ ] **Storybook Setup** (AC: #2)
  - [ ] Run `npx storybook@latest init`
  - [ ] Verify Storybook configured for React + Vite
  - [ ] Create stories for all Shadcn UI components (Button, Card, Input, ScrollArea, Avatar)
  - [ ] Test Storybook runs on localhost:6006
  - [ ] Verify all component variants display correctly in Storybook

- [ ] **TypeScript Types** (AC: #7)
  - [ ] Create src/types/index.ts
  - [ ] Define Message interface { id, content, role, timestamp }
  - [ ] Define ChatRequest type
  - [ ] Define ChatResponse type

- [ ] **API Client** (AC: #7, #9)
  - [ ] Install axios
  - [ ] Create src/services/api.ts
  - [ ] Set up axios instance with base URL from env
  - [ ] Implement sendMessage(message: string) function
  - [ ] Add error handling wrapper
  - [ ] Configure timeout (30000ms)

- [ ] **Landing Page Component** (AC: #3, #10)
  - [ ] Create src/components/LandingPage.tsx
  - [ ] Use Card component for hero section
  - [ ] Add project title and description
  - [ ] Add introduction text
  - [ ] Apply Tailwind responsive layout
  - [ ] Test on mobile and desktop viewports

- [ ] **Chat Interface Component** (AC: #4, #5, #6, #8, #12)
  - [ ] Create src/components/ChatInterface.tsx
  - [ ] Set up message state with useState hook
  - [ ] Implement ScrollArea for message container
  - [ ] Map messages with Avatar components
  - [ ] Create Input field for user message
  - [ ] Create Button for send action
  - [ ] Implement send message handler
  - [ ] Add loading state during API call
  - [ ] Add error state display
  - [ ] Implement auto-scroll to bottom on new messages
  - [ ] Style with Tailwind CSS

- [ ] **Main App** (AC: #1)
  - [ ] Create src/App.tsx
  - [ ] Combine LandingPage and ChatInterface
  - [ ] Apply main layout with Tailwind grid/flex
  - [ ] Update src/main.tsx entry point

- [ ] **Environment Configuration** (AC: #7)
  - [ ] Create .env.example with VITE_API_BASE_URL
  - [ ] Create .env with localhost:8000 URL
  - [ ] Update vite.config.ts if needed

- [ ] **Testing and Validation** (AC: #8, #9, #10, #12)
  - [ ] Start backend on localhost:8000
  - [ ] Start frontend with `npm run dev`
  - [ ] Test sending messages and receiving responses
  - [ ] Test loading state displays correctly
  - [ ] Test error state when backend is down
  - [ ] Test responsive design on mobile (375px)
  - [ ] Test responsive design on desktop
  - [ ] Verify auto-scroll behavior
  - [ ] Verify no CORS errors in console
  - [ ] Test all Shadcn UI components render correctly

## Dev Notes

### Technical Summary

Build a modern React TypeScript frontend using Vite as the build tool and Shadcn UI for a professional component library. The application features a landing page with project introduction and an embedded chat interface. Uses Tailwind CSS for styling, with reusable components organized in a library structure. API client handles communication with the FastAPI backend.

### Project Structure Notes

- Files to modify:
  - [CREATE] frontend/public/index.html
  - [CREATE] frontend/src/App.tsx
  - [CREATE] frontend/src/main.tsx
  - [CREATE] frontend/src/components/ui/button.tsx
  - [CREATE] frontend/src/components/ui/card.tsx
  - [CREATE] frontend/src/components/ui/input.tsx
  - [CREATE] frontend/src/components/ui/scroll-area.tsx
  - [CREATE] frontend/src/components/ui/avatar.tsx
  - [CREATE] frontend/src/components/LandingPage.tsx
  - [CREATE] frontend/src/components/ChatInterface.tsx
  - [CREATE] frontend/src/lib/utils.ts
  - [CREATE] frontend/src/services/api.ts
  - [CREATE] frontend/src/types/index.ts
  - [CREATE] frontend/components.json
  - [CREATE] frontend/package.json
  - [CREATE] frontend/tsconfig.json
  - [CREATE] frontend/tailwind.config.js
  - [CREATE] frontend/postcss.config.js
  - [CREATE] frontend/vite.config.ts
  - [CREATE] frontend/.env.example

- Expected test locations: Manual browser testing, no automated tests for MVP
- Estimated effort: 5 story points (1 week)

### References

- **Tech Spec:** See tech-spec.md sections:
  - Source Tree Structure (frontend files)
  - Technical Approach (Frontend Strategy, Data Flow)
  - Implementation Stack (Frontend)
  - Technical Details (Frontend API Client, React Components)
  - Development Setup (Frontend Setup)
  - Implementation Guide (Phase 3, Phase 4)
  - Testing Approach (Frontend Testing, Integration Testing)

## Dev Agent Record

### Context Reference

- docs/stories/story-personal-chatbot-2.context.xml

### Agent Model Used

<!-- Will be populated during dev-story execution -->

### Debug Log References

<!-- Will be populated during dev-story execution -->

### Completion Notes List

<!-- Will be populated during dev-story execution -->

### File List

<!-- Will be populated during dev-story execution -->
