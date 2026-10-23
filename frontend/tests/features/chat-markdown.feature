Feature: Chat replies render markdown safely
  As a visitor reading the Alter-Ego's replies
  I want headings, bold text, lists, code and links rendered, not shown as raw markers
  So that replies are readable and links work without exposing me to unsafe content

  Scenario: Assistant replies render markdown formatting
    When the reply contains "##", "**" and "-" markdown
    Then it shows a heading, bold text and a list without the markers

  Scenario: Code blocks keep their text in a preformatted block
    When the reply contains a fenced code block
    Then the code shows in a preformatted block without the fences

  Scenario: Links are clickable and safe
    When the reply contains a markdown link
    Then an http(s) link opens in a new tab with rel "noopener noreferrer nofollow"
    And a javascript: link is shown as plain text

  Scenario: Raw HTML and images are never rendered
    When the reply contains raw HTML or a markdown image
    Then no HTML element or image from the reply is rendered

  Scenario: Visitor messages stay plain text
    When I type markdown in my own message
    Then my message shows exactly as I typed it
