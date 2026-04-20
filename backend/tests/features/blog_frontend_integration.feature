Feature: Dynamic Blog Post Rendering from Backend API

  Background:
    Given the backend API is running
    And there is at least one completed carousel project

  Scenario: Blog index shows carousel posts from API
    Given completed carousel projects exist in the backend
    When the user navigates to /blog
    Then the page displays a list of blog posts
    And each post card shows the title, niche badge, and date

  Scenario: Blog post page renders markdown content from API
    Given a carousel project with bilingual blog content (pt-BR and en)
    When the user navigates to /blog/{id}
    Then the page fetches blog content from /api/carousels/{id}/blog/pt
    And the page fetches design tokens from /api/carousels/{id}/design
    And the markdown content is rendered with theme-aware styling

  Scenario: Design tokens are applied as CSS custom properties
    Given a carousel project with cybersecurity theme
    When the blog post page loads
    Then CSS custom properties are set on the wrapper div
    And --blog-primary is set to #ef4444
    And --blog-accent is set to #00d4ff
    And --blog-bg is set to #0a0e17

  Scenario: Hero image is loaded from API
    Given a carousel project with generated output files
    When the blog post page loads
    Then the hero image src points to /api/carousels/{id}/images/hero

  Scenario: Blog post without content shows not found
    Given a carousel project ID that does not exist
    When the user navigates to /blog/{id}
    Then the page shows a 404 not found page

  Scenario: Empty blog index shows empty state message
    Given no completed carousel projects exist
    When the user navigates to /blog
    Then the page displays "No blog posts yet" message

  Scenario: Badge label comes from design tokens
    Given a carousel project with "Cybersecurity" niche
    When the blog post page loads
    Then the badge displays "Cybersecurity" from design.layout.badge_label

  Scenario: Typography from design tokens is applied
    Given a carousel project with design tokens
    When the blog post page loads
    Then headings use font_family_heading from design token
    And body text uses font_family_body from design token
    And the badge uses font_family_badge from design token