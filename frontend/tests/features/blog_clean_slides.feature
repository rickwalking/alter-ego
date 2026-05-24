Feature: Blog uses clean background art instead of carousel slides with text overlay
  As a blog visitor
  I want to see clean background art in blog posts
  So that the content is visually clean and professional

  Background:
    Given a completed carousel with design_tokens containing both slides and rendered_slides_pt

  Scenario: Blog post page uses raw slides, not rendered slides
    When the blog post page renders
    Then slideImageUrls are built from design.images.slides only
    And rendered_slides_pt is never used

  Scenario: Blog post page still works when rendered_slides are absent
    Given design_tokens has no rendered_slides_pt
    When the blog post page renders
    Then slideImageUrls are built from design.images.slides

  Scenario: Blog post hero image uses design.images.hero
    When the blog post page renders
    Then heroImageUrl uses design.images.hero
