Feature: Public blog body never renders carousel slides (AE-0422)
  A blog post must display editorial content, not Instagram cards with baked-in
  text. This supersedes the "raw slides" contract of blog_clean_slides.feature:
  before AE-0423 the blog body carries NO carousel image at all.

  Background:
    Given a published carousel-origin blog post

  Scenario: No rendered carousel slide appears in the body
    Given the carousel design exposes rendered_slides_pt
    When an anonymous visitor opens /blog/{id}
    Then no image in the article body has a src containing "/slide-images/"
    And the article body renders only text sections

  Scenario: A section with no image renders text only
    Given a section whose image is absent
    When the blog page renders
    Then that section shows its heading and body text
    And no placeholder broken image is shown

  Scenario: Theme still comes from the carousel design
    Given the carousel design exposes colors and typography
    When the blog page renders
    Then the section headings use the design typography
    And no image URL is taken from the design

  Scenario: Standalone post with no design tokens uses the default theme
    Given a standalone blog post with no carousel project
    When the blog page renders
    Then the default public theme is applied
    And the article content is visible

  Scenario: The title is rendered exactly once
    Given the stored legacy markdown starts with "# <title>"
    When the blog page renders
    Then the page contains exactly one H1 with the post title

  Scenario: Every published carousel-origin post is selected for hiding
    Given a published carousel-origin row with a long, apparently healthy body
    When the hide-all criteria are evaluated
    Then the row is selected for hiding

  Scenario: A published standalone post is not selected for hiding
    Given a published post whose origin is "standalone"
    When the hide-all criteria are evaluated
    Then the row is not selected

  Scenario: An already-draft carousel-origin post is not re-hidden
    Given a carousel-origin row whose status is "draft"
    When the hide-all criteria are evaluated
    Then the row is not selected

  Scenario: A design payload with blog_image_map is ignored
    Given the carousel design payload still contains blog_image_map
    When the public blog page renders the post
    Then the body does not map any image positionally
    And no carousel slide image is shown
