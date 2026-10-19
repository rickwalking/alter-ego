# PARTIALLY SUPERSEDED by ADR-0025 / AE-0422 + AE-0423.
#
# RETIRED (kept for history, no longer the contract):
#   * "Duplicate H1 Removal" — v2 stores no leading "# <title>"; the renderer
#     renders the title once and never strips an H1. See blog_sections_ae0423.
#   * "Section-to-Slide Image Mapping" — the blog no longer maps carousel slides
#     to H2 sections (blog_image_map is dead for the blog). See
#     blog_no_carousel_slides_ae0422.feature and blog_sections_ae0423.feature.
#
# STILL VALID: the markdown cleanup scenarios (code fences, stray HTML, entities,
# whitespace) now apply per section `body_md` rather than to one flat body.

Feature: Section body markdown renders cleanly (AE-0422/AE-0423; supersedes parts of the v1 cleanup)
  Visitor-facing clarity: no duplicate titles, no code artifacts, no HTML
  fragments. Post-v2 this applies per section `body_md`; the body never starts
  with a leading H1 and images are the section's own.

  Background:
    Given a blog post detail page at /blog/{id}
    And the BlogPostContent component renders v2 sections with design tokens

  # ---------------------------------------------------------------------------
  # RETIRED — Duplicate H1 Removal (v2 stores no leading H1)
  # ---------------------------------------------------------------------------

  # Scenario: Blog post strips leading H1 to prevent duplicate title
  #   (retired: v2 body_md never contains a leading H1)
  #
  # Scenario: Blog post strips leading H1 with subtitle separator
  #   (retired: v2 body_md never contains a leading H1)

  Scenario: The title is rendered exactly once from the post title
    Given the post title is "Kimi K2.6: 300 Agents"
    And no section body_md starts with "# "
    When the BlogPostContent renders
    Then the page contains exactly one H1 with "Kimi K2.6: 300 Agents"
    And no section renders an H1

  Scenario: Section H2 and H3 headings are preserved
    Given a section body_md contains "## Section One\n\n### Subsection"
    When the BlogPostContent renders
    Then an H2 heading "Section One" is present
    And an H3 heading "Subsection" is present

  # ---------------------------------------------------------------------------
  # Backtick Artifact Removal (still valid, now per section body)
  # ---------------------------------------------------------------------------

  Scenario: Backtick-wrapped duplicate paragraphs are not rendered
    Given a section body_md contains:
      """
      `A Moonshot AI acaba de lançar o Kimi K2.6...`
      A Moonshot AI acaba de lançar o Kimi K2.6...
      """
    When the BlogPostContent renders
    Then only one paragraph with the text appears
    And no inline code block contains the duplicated text

  Scenario: Legitimate inline code is preserved
    Given a section body_md contains "Use `npm install` to add the package"
    When the BlogPostContent renders
    Then an inline code element contains "npm install"

  Scenario: Legitimate code fences are preserved
    Given a section body_md contains:
      """
      ```python
      def hello():
          pass
      ```
      """
    When the BlogPostContent renders
    Then a code block contains "def hello():"

  # ---------------------------------------------------------------------------
  # HTML Fragment Artifact Removal (still valid)
  # ---------------------------------------------------------------------------

  Scenario: Unclosed HTML tags are stripped
    Given a section body_md contains 'Arquitetura que Torna Sessões de 12 Horas Possíveis" />'
    When the BlogPostContent renders
    Then the text does not contain '" />'

  Scenario: Empty image tags are stripped
    Given a section body_md contains '<img alt="section" />\n\nReal paragraph'
    When the BlogPostContent renders
    Then the paragraph "Real paragraph" is rendered
    And no broken image element is visible

  Scenario: HTML entities are decoded or removed
    Given a section body_md contains "Text &amp; More"
    When the BlogPostContent renders
    Then the rendered text is "Text & More"

  # ---------------------------------------------------------------------------
  # Whitespace Normalization (still valid)
  # ---------------------------------------------------------------------------

  Scenario: Excessive whitespace lines are collapsed
    Given a section body_md contains "Hello\n\n\n\n\nWorld"
    When the BlogPostContent renders
    Then the visual gap between paragraphs is consistent
    And no more than two consecutive blank lines exist in the DOM

  # ---------------------------------------------------------------------------
  # RETIRED — Section-to-Slide Image Mapping (blog_image_map is dead for the blog)
  # ---------------------------------------------------------------------------

  # Scenario: Each H2 section gets the correct slide image
  #   (retired: blog no longer maps carousel slides to sections)
  #
  # Scenario: Sections without mapping get no image
  #   (retired: sections use their own blog.v2 image, never a mapped slide)

  Scenario: A section renders its own image, not a mapped carousel slide
    Given a section with its own image url and non-empty alt
    When the BlogPostContent renders
    Then the section shows that image with its stored alt
    And no image src contains "/slide-images/"

  # ---------------------------------------------------------------------------
  # Edge Cases (updated for v2 sections)
  # ---------------------------------------------------------------------------

  Scenario Outline: Content cleanup handles malformed section markdown
    Given a section body_md equals <input>
    When the BlogPostContent renders
    Then the rendered output contains <expected>

    Examples:
      | input | expected |
      | "`Paragraph`\nParagraph" | "Paragraph" |
      | "## Heading\n<img src=\"x\" />\nText" | "Text" |
      | "## A\n\n\n\n## B" | "A" and "B" as separate headings |

  Scenario: A post with no cover still renders content
    Given the post cover is null
    When the blog post page loads
    Then a neutral default hero is shown
    And the article content is still visible

  Scenario: A post with missing design tokens uses the fallback theme
    Given the design endpoint returns 404
    When the blog post page loads
    Then FALLBACK_DESIGN_TOKENS are applied
    And the page renders with the default theme
