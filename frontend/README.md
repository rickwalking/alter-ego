# Alter Ego - AI Personal Chatbot

AI-powered chatbot interface built with React 19, TypeScript, and Vite, featuring liquid glass morphism design and WCAG 2.1 AA accessibility compliance.

## Features

- 🤖 Real-time AI chat interface
- ✅ Client-side input validation with character count
- ⏱️ Rate limiting to prevent message spam
- ♿ WCAG 2.1 Level AA accessible
- ⌨️ Full keyboard navigation support
- 🎨 Liquid glass morphism design
- 📱 Responsive mobile/desktop layout
- 🧪 Storybook component documentation

## Accessibility

This application implements WCAG 2.1 Level AA accessibility standards:

- **Screen Reader Support**: ARIA labels, live regions, and semantic HTML
- **Keyboard Navigation**: Tab, Enter, and Escape key support
- **Focus Indicators**: Visible focus outlines meeting contrast requirements
- **Error Handling**: Clear error messages announced to assistive technologies

For detailed accessibility information, see [../docs/accessibility.md](../docs/accessibility.md).

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Tab | Navigate between elements |
| Enter | Send message |
| Escape | Clear input field |

## Input Validation & Rate Limiting

The chat interface includes client-side validation to ensure message quality and prevent spam. All validation is performed client-side without backend API calls.

### Character Limit

- **Maximum Length**: 5000 characters
- **Counter Display**: Shows current character count in format "X / 5000 characters"
- **Real-time Updates**: Counter updates on every keystroke
- **Visual Feedback**:
  - Normal (0-4500 chars): Muted gray text
  - Warning (4501-5000 chars): Amber text
  - Error (>5000 chars): Red text with bold styling
- **Error Message**: "Message too long (X/5000 characters)" when limit exceeded
- **Send Prevention**: Send button disabled when message exceeds limit

### Rate Limiting

- **Minimum Interval**: 1 second (1000ms) between messages
- **Client-Side Only**: No backend enforcement, prevents accidental rapid clicks
- **Countdown Timer**: Displays "Wait X.Xs" on send button when rate limit active
- **Visual Feedback**: Send button disabled during countdown period
- **Reset**: Timer resets after each successful message send

### Validation Error Display

- **Position**: Below input field, left-aligned
- **Styling**: Glass morphism error variant (red tint with backdrop blur)
- **Accessibility**: Errors announced to screen readers via aria-invalid and aria-describedby
- **Auto-clear**: Errors automatically clear when validation passes

### Send Button Behavior

The send button is disabled when any of the following conditions are true:

1. Message is empty or only whitespace
2. Message exceeds 5000 characters
3. Rate limit is active (less than 1 second since last send)
4. Backend API request is in progress (loading state)

## Development

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
