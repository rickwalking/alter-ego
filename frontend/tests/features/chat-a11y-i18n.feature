Feature: Chat accessibility and localization
  As a keyboard or screen-reader user, or a Portuguese speaker
  I want the chat to announce replies, keep my focus and speak my language
  So that I can use the chat without a mouse, without sight, and in Portuguese

  Scenario: Replies are announced to screen readers once
    Given the message list is a labelled log
    When a reply streams in
    Then a polite live region says the Alter-Ego is typing
    And when it finishes the live region reads the reply once

  Scenario: Loading a conversation's history announces nothing
    Given I open a conversation that already has replies
    Then the live region stays silent

  Scenario: A long reply is announced as plain text, cut short
    When a reply with markdown and more than 280 characters finishes
    Then the live region reads it without markdown markers or extra spaces
    And links and images are read by their text, never their address
    And it stops at 280 characters followed by an ellipsis

  Scenario: The message box has a label and a visible focus ring
    Then the message box has an accessible name
    And it shows a focus outline instead of removing it

  Scenario: Focus stays in the message box after sending
    When I send a message with Enter, or with the Send button while I was typing in the message box
    Then the message box stays enabled and focused while the reply streams
    And a tap on Send when the message box was not focused does not focus it (no keyboard pops up on a phone)

  Scenario: The log and the announcer are separate
    Then the polite status announcer sits next to the conversation log, not inside it

  Scenario: The public chat has a main landmark and a skip link
    When I open /chat
    Then the conversation area is the page's main landmark
    And a skip link jumps to it

  Scenario: The chat UI speaks the visitor's language
    Then every chat label comes from the translations
    And each English chat string has a Portuguese translation
    And with the Portuguese locale the header, message box and typing label are in Portuguese
