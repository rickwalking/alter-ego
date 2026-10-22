@AE-0452 @frontend @i18n
Feature: Labels and errors follow the visitor's language
  Components that already translate their text also translate their
  accessible labels and error messages, so a Portuguese visitor never gets an
  English-only label or alert.

  Scenario: The knowledge upload labels come from the translations
    When the knowledge upload area renders a picked file and an upload in progress
    Then the drop area, file input, remove button and progress labels are translated

  Scenario: The mobile menu button label comes from the translations
    When the mobile navigation renders
    Then the menu button's label is translated

  Scenario: A failed voice score shows a translated error
    Given scoring a text against the persona voice fails
    When the owner scores a text
    Then the translated "voice scoring failed" message is shown
