# Accessibility Documentation

## Overview

This project implements WCAG 2.1 Level AA accessibility standards to ensure the AI chatbot interface is usable by people with disabilities, including those who use screen readers or keyboard-only navigation.

## ARIA Patterns Implemented

### Chat Interface

The chat interface (`frontend/src/components/ChatInterface.tsx`) implements several ARIA patterns:

#### Live Region for Messages
```tsx
<ScrollArea
  role="log"
  aria-live="polite"
  aria-busy={isLoading}
  aria-label="Chat messages"
>
```

- `role="log"`: Identifies the message container as a log of messages
- `aria-live="polite"`: Announces new messages to screen readers without interrupting
- `aria-busy`: Indicates when the chat is loading/processing
- `aria-label`: Provides a descriptive name for the messages area

#### Input Field
```tsx
<Input
  aria-label="Message input"
  aria-describedby="message-input-description"
  aria-invalid={!!error}
/>
```

- `aria-label`: Labels the input for screen readers
- `aria-describedby`: Links to help text explaining the input's purpose
- `aria-invalid`: Indicates validation errors

#### Send Button
```tsx
<Button aria-label="Send message">
```

- `aria-label`: Provides clear button purpose for screen readers

#### Screen Reader Help Text
```tsx
<span id="message-input-description" className="sr-only">
  Type your message and press Enter or click Send to send it to the AI assistant
</span>
```

- `.sr-only` class: Visually hidden but available to screen readers
- Provides contextual help for input field usage

## Keyboard Navigation

### Supported Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Tab | Navigate between interactive elements (input → send button) |
| Enter | Send message (when focused on input field) |
| Escape | Clear input field and dismiss errors |
| Shift+Tab | Navigate backwards through interactive elements |

### Navigation Order

1. Message input field
2. Send button
3. (Messages in ScrollArea are read-only, announced via live region)

### Focus Management

- Focus indicators are visible on all interactive elements
- Focus outline meets WCAG 2.1 AA contrast requirements (3:1 minimum)
- Custom glass design maintains focus visibility against dark background (#0a0a0f)

## WCAG 2.1 Compliance

### Level A Criteria

**1.3.1 Info and Relationships**
- ✅ Proper semantic HTML structure
- ✅ ARIA roles and labels where semantic HTML insufficient
- ✅ Form labels associated with inputs

**2.1.1 Keyboard**
- ✅ All functionality available via keyboard
- ✅ No keyboard traps
- ✅ Logical tab order

**4.1.2 Name, Role, Value**
- ✅ All UI components have accessible names (via aria-label)
- ✅ Roles communicated to assistive technologies
- ✅ States and properties exposed (aria-busy, aria-invalid)

### Level AA Criteria

**2.4.7 Focus Visible**
- ✅ Focus indicators visible on all interactive elements
- ✅ 3:1 contrast ratio maintained

**3.2.4 Consistent Identification**
- ✅ Input labeled consistently as "Message input"
- ✅ Button labeled consistently as "Send message"

**4.1.3 Status Messages**
- ✅ ARIA live regions announce new messages
- ✅ Error messages announced to screen readers
- ✅ Loading states communicated via aria-busy

## Screen Reader Testing

### Recommended Tools

- **NVDA** (Windows, free): https://www.nvaccess.org/
- **JAWS** (Windows, commercial): https://www.freedomscientific.com/products/software/jaws/
- **VoiceOver** (macOS/iOS, built-in): System Preferences → Accessibility → VoiceOver

### Testing Procedure

1. **Navigate to Application**
   - Open application in browser
   - Enable screen reader
   - Verify page title is announced

2. **Test Message Input**
   - Tab to message input
   - Verify "Message input" label is read
   - Verify help text is read: "Type your message and press Enter or click Send..."
   - Type a message
   - Press Enter or Tab to Send button

3. **Test Message Sending**
   - Activate Send button
   - Verify loading state announced ("busy")
   - Verify new message announced when received
   - Verify message content is read

4. **Test Error Handling**
   - Trigger an error (e.g., backend unavailable)
   - Verify error message is announced
   - Verify aria-invalid state on input

5. **Test Keyboard Navigation**
   - Use Tab/Shift+Tab to navigate
   - Verify focus order is logical
   - Test Enter key to send
   - Test Escape key to clear

### Expected Behavior

- Input field announced as: "Message input, edit text. Type your message and press Enter or click Send to send it to the AI assistant"
- Send button announced as: "Send message, button"
- New messages announced as they appear
- Loading state: "Chat messages, busy"
- Error state: "Message input, invalid, edit text"

## Automated Testing

### axe DevTools

Install the axe DevTools browser extension:
- Chrome/Edge: https://chrome.google.com/webstore
- Firefox: https://addons.mozilla.org/firefox

### Running Audits

1. Open the application in browser
2. Open DevTools (F12)
3. Navigate to "axe DevTools" tab
4. Click "Scan ALL of my page"
5. Review results

### Target Metrics

- ✅ 0 critical issues
- ✅ 0 serious issues
- ⚠️ Minor/moderate issues acceptable if documented

### Known Issues

None currently. All critical and serious accessibility issues have been addressed.

## Implementation Notes

### CSS Classes

**`.sr-only`** - Screen reader only text
```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

### Focus Indicators

All interactive elements use browser default focus outlines, which are ensured to have sufficient contrast against the dark background (#0a0a0f) of the glass design system.

## Future Improvements

1. **Skip Navigation Link**: Add "Skip to chat" link for keyboard users
2. **Message History Navigation**: Allow arrow key navigation through messages
3. **Voice Input**: Add voice-to-text support for hands-free interaction
4. **High Contrast Mode**: Support Windows High Contrast Mode
5. **Reduced Motion**: Respect `prefers-reduced-motion` for animations

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [WebAIM Screen Reader Testing](https://webaim.org/articles/screenreader_testing/)
- [axe DevTools Documentation](https://www.deque.com/axe/devtools/)

## Maintenance

When adding new features:
1. Ensure all interactive elements have accessible names
2. Test with keyboard navigation
3. Run axe DevTools audit
4. Test with at least one screen reader
5. Update this documentation with new patterns

---

**Last Updated**: 2025-11-03
**WCAG Level**: AA
**Testing Status**: Manual and automated testing complete
