Feature: Carousel Content Generation Template Constraints
  As a content pipeline
  I want the LLM to produce clean, well-structured blog markdown
  So that the frontend renders it without artifacts or duplication

  Background:
    Given the content generation template is loaded
    And a carousel project with topic "Kimi K2.6 Launch" and niche "AI"

  # ---------------------------------------------------------------------------
  # Prompt Constraints
  # ---------------------------------------------------------------------------

  Scenario: Template instructs LLM to omit title from markdown body
    When the content prompt is built
    Then the prompt contains "do NOT include the title as the first H1"
    And the prompt contains "the frontend renders the title separately"

  Scenario: Template instructs LLM to avoid backtick-wrapping paragraphs
    When the content prompt is built
    Then the prompt contains "do NOT wrap entire paragraphs in backticks"
    And the prompt contains "use backticks only for inline code and code fences"

  Scenario: Template instructs LLM to avoid HTML tags
    When the content prompt is built
    Then the prompt contains "do NOT emit HTML tags"
    And the prompt contains "use pure Markdown only"

  # ---------------------------------------------------------------------------
  # Post-Generation Cleanup
  # ---------------------------------------------------------------------------

  Scenario: Cleanup strips leading H1 before persistence
    Given the LLM returns blog_pt starting with "# Title\n\nBody"
    When the post-generation cleanup runs in the content node
    Then blog_markdown persisted is "Body"

  Scenario: Cleanup strips leading H1 with subtitle
    Given the LLM returns blog_en starting with "# Title: Subtitle\n\nBody"
    When the post-generation cleanup runs
    Then blog_translations["en"] persisted is "Body"
    And title_en is extracted as "Title"
    And subtitle_en is extracted as "Subtitle"

  Scenario: Cleanup removes backtick-wrapped duplicates
    Given the LLM returns:
      """
      Body paragraph.
      `Body paragraph.`
      More text.
      """
    When the post-generation cleanup runs
    Then the persisted markdown contains "Body paragraph." exactly once

  Scenario: Cleanup removes HTML fragment artifacts
    Given the LLM returns "Text\n<img alt=\"x\" />\nMore text"
    When the post-generation cleanup runs
    Then the persisted markdown does not contain "<img"

  # ---------------------------------------------------------------------------
  # Design Token Generation
  # ---------------------------------------------------------------------------

  Scenario: Template sets badge_label to project niche
    When the design prompt is built
    Then the prompt contains "badge_label should reflect the niche: AI"

  Scenario: Pipeline persists niche-aware badge_label
    Given the LLM returns design tokens with layout.badge_label "CARROSSEL"
    And the project niche is "Cybersecurity"
    When the design node normalizes tokens
    Then the persisted badge_label is "Cybersecurity"

  # ---------------------------------------------------------------------------
  # Mutation Tests
  # ---------------------------------------------------------------------------

  Scenario Outline: Cleanup handles LLM mutation outputs
    Given the raw LLM output equals <raw>
    When cleanup runs
    Then the cleaned output equals <cleaned>

    Examples:
      | raw | cleaned |
      | "# T\n\n`P`\nP\n\n## S" | "P\n\n## S" |
      | "# T: S\n\nBody" | "Body" |
      | "Text\n<br/>\nMore" | "Text\n\nMore" |
      | "# T\n\n\n\n\nBody" | "Body" |
      | "`Code` is inline\n`Code` is inline" | "`Code` is inline" |

  Scenario: Empty cleanup input returns empty string
    Given the raw LLM output is ""
    When cleanup runs
    Then the cleaned output is ""

  Scenario: Cleanup input with only H1 returns empty string
    Given the raw LLM output is "# Title Only"
    When cleanup runs
    Then the cleaned output is ""
