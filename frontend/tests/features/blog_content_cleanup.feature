Feature: Blog Post Content Cleanup and Rendering
  As a visitor
  I want blog posts to render cleanly without duplicate titles, code artifacts, or HTML fragments
  So that I can read the content without visual noise

  Background:
    Given a blog post detail page at /blog/{id}
    And the BlogPostContent component renders markdown with design tokens

  # ---------------------------------------------------------------------------
  # Duplicate H1 Removal
  # ---------------------------------------------------------------------------

  Scenario: Blog post strips leading H1 to prevent duplicate title
    Given the markdown contains "# Kimi K2.6: 300 Agents\n\nA Moonshot AI..."
    And the blog title is "Kimi K2.6: 300 Agents"
    When the BlogPostContent renders
    Then the page contains exactly one H1 with "Kimi K2.6: 300 Agents"
    And the markdown body does not render an additional H1

  Scenario: Blog post strips leading H1 with subtitle separator
    Given the markdown contains "# Title: Subtitle\n\nBody text"
    And the blog title is "Title"
    When the BlogPostContent renders
    Then the subtitle "Subtitle" is rendered once in the header
    And the body starts with "Body text"

  Scenario: Blog post preserves H2 and H3 headings
    Given the markdown contains "## Section One\n\n### Subsection"
    When the BlogPostContent renders
    Then an H2 heading "Section One" is present
    And an H3 heading "Subsection" is present

  # ---------------------------------------------------------------------------
  # Backtick Artifact Removal
  # ---------------------------------------------------------------------------

  Scenario: Backtick-wrapped duplicate paragraphs are not rendered
    Given the markdown contains:
      """
      `A Moonshot AI acaba de lançar o Kimi K2.6...`
      A Moonshot AI acaba de lançar o Kimi K2.6...
      """
    When the BlogPostContent renders
    Then only one paragraph with the text appears
    And no inline code block contains the duplicated text

  Scenario: Legitimate inline code is preserved
    Given the markdown contains "Use `npm install` to add the package"
    When the BlogPostContent renders
    Then an inline code element contains "npm install"

  Scenario: Legitimate code fences are preserved
    Given the markdown contains:
      """
      ```python
      def hello():
          pass
      ```
      """
    When the BlogPostContent renders
    Then a code block contains "def hello():"

  # ---------------------------------------------------------------------------
  # HTML Fragment Artifact Removal
  # ---------------------------------------------------------------------------

  Scenario: Unclosed HTML tags are stripped
    Given the markdown contains 'Arquitetura que Torna Sessões de 12 Horas Possíveis" />'
    When the BlogPostContent renders
    Then the text does not contain '" />'

  Scenario: Empty image tags are stripped
    Given the markdown contains '<img alt="section" />\n\nReal paragraph'
    When the BlogPostContent renders
    Then the paragraph "Real paragraph" is rendered
    And no broken image element is visible

  Scenario: HTML entities are decoded or removed
    Given the markdown contains "Text &amp; More"
    When the BlogPostContent renders
    Then the rendered text is "Text & More"

  # ---------------------------------------------------------------------------
  # Whitespace Normalization
  # ---------------------------------------------------------------------------

  Scenario: Excessive whitespace lines are collapsed
    Given the markdown contains "Hello\n\n\n\n\nWorld"
    When the BlogPostContent renders
    Then the visual gap between paragraphs is consistent
    And no more than two consecutive blank lines exist in the DOM

  # ---------------------------------------------------------------------------
  # Section-to-Slide Image Mapping
  # ---------------------------------------------------------------------------

  Scenario: Each H2 section gets the correct slide image
    Given the design tokens contain a blog_image_map with 3 entries
    And the slide images array has 4 items
    When the BlogPostContent renders
    Then each H2 section after the first displays the mapped slide image
    And the intro section has no slide image

  Scenario: Sections without mapping get no image
    Given a section heading does not exist in blog_image_map
    When the BlogPostContent renders
    Then that section has no slide image

  # ---------------------------------------------------------------------------
  # Edge Cases & Mutations
  # ---------------------------------------------------------------------------

  Scenario Outline: Content cleanup handles malformed markdown
    Given the raw markdown equals <input>
    When the BlogPostContent renders
    Then the rendered output contains <expected>

    Examples:
      | input | expected |
      | "# Title\n`Paragraph`\nParagraph" | "Paragraph" |
      | "## Heading\n<img src=\"x\" />\nText" | "Text" |
      | "# A\n\n\n\n# B" | "A" and "B" as separate sections |
      | "# Title: Sub\n\nBody" | "Body" as first paragraph |

  Scenario: Blog post without hero image still renders content
    Given design.images.hero is empty
    When the blog post page loads
    Then the BlogPostHero component is not rendered
    And the article content is still visible

  Scenario: Blog post with missing design tokens uses fallback
    Given the design endpoint returns 404
    When the blog post page loads
    Then FALLBACK_DESIGN_TOKENS are applied
    And the page renders with default blue/orange theme
