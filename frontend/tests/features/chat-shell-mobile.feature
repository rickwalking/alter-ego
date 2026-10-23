Feature: Chat shell and mobile fit
  As a visitor on the public chat, often on a phone
  I want the site header, a chat that fits my screen and honest controls
  So that /chat is not a dead end and works with my thumb and keyboard

  Scenario: The public chat has the site header
    When I open /chat
    Then I see the site header with the home link, the navigation and the language switcher
    And the chat header has no empty left gutter
    And "New chat" stays on one line

  Scenario: The chat fits the mobile viewport above the browser bars and home indicator
    Then the page fills the dynamic viewport height (dvh), not 100vh
    And the composer keeps clear of the home indicator (safe-area inset)
    And the message box uses a 16px font so iOS does not zoom on focus

  Scenario: Touch targets are at least 44 pixels
    Then Send, New chat and the conversations toggle are at least 44px tall

  Scenario: The mobile conversation drawer is opaque and above the menu button
    When I open the conversations drawer on a phone
    Then its background is solid
    And it sits above the dashboard menu button

  Scenario: No fake notifications
    Then the chat header has no notifications bell or unread dot

  Scenario: Visitors' messages do not carry the owner's initials
    When a visitor sends a message
    Then their message shows a neutral person icon, not "PM"
