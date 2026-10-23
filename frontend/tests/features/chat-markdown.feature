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
    Then an http(s) or mailto link opens in a new tab with rel "noopener noreferrer nofollow"
    And a web link shows its host next to it, unless its text already names the host
    And same-site links and anchors are clickable and stay in the same tab
    And a javascript: link is shown as plain text

  Scenario: Unsafe or empty links stay readable text
    When the reply contains a javascript:, data: or vbscript: link in any case or entity-encoded, an autolink or a
      reference-style link to one, a link with no target, or an unsafe link around an image
    Then none of them is clickable
    And the link text, or the target when only an image was inside, is shown as plain text

  Scenario: Raw HTML and images are never rendered
    When the reply contains raw HTML or a markdown image
    Then no HTML element or image from the reply is rendered

  Scenario: Visitor messages stay plain text
    When I type markdown in my own message
    Then my message shows exactly as I typed it

  Scenario: A reply the renderer cannot take shows as plain text
    When a reply is nested deeper than 20 list or quote levels, is longer than 20000 characters, or fails to render
    Then it shows as plain text and the rest of the chat keeps working

  Scenario: A streamed token re-renders only the reply it extends
    Given earlier replies are on screen
    When a new reply streams in
    Then the earlier replies are not parsed again
