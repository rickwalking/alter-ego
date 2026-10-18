# SUPERSEDED by ADR-0025 / AE-0422 and rewritten in place.
#
# The "raw background art instead of rendered slides" contract below is OBSOLETE:
# the public blog body no longer reads carousel design for images at all. Blog
# images are now the post's OWN generated images (blog.v2, AE-0423/AE-0425) and
# the public page never emits a /slide-images/ URL. The scenarios below are kept
# (not deleted) to record the retired contract and are replaced by
# blog_no_carousel_slides_ae0422.feature.
#
# Historical contract (RETIRED):
#
# Feature: Blog uses clean background art instead of carousel slides with text overlay
#   As a blog visitor
#   I want to see clean background art in blog posts
#   So that the content is visually clean and professional
#
#   Background:
#     Given a completed carousel with design_tokens containing both slides and rendered_slides_pt
#
#   Scenario: Blog post page uses raw slides, not rendered slides
#     When the blog post page renders
#     Then slideImageUrls are built from design.images.slides only
#     And rendered_slides_pt is never used
#
#   Scenario: Blog post page still works when rendered_slides are absent
#     Given design_tokens has no rendered_slides_pt
#     When the blog post page renders
#     Then slideImageUrls are built from design.images.slides
#
#   Scenario: Blog post hero image uses design.images.hero
#     When the blog post page renders
#     Then heroImageUrl uses design.images.hero

Feature: Blog no longer derives images from carousel slides (supersedes the retired contract above)
  A blog post owns its images (blog.v2); carousel design is not read for blog
  body images. This feature replaces the retired raw-vs-rendered slide contract.

  Background:
    Given a published carousel-origin blog post

  Scenario: The blog body never uses a rendered carousel slide
    Given the carousel design exposes rendered_slides_pt
    When the blog post page renders
    Then no image src contains "/slide-images/"
    And rendered_slides_pt is never read

  Scenario: The blog body never uses raw carousel slide art either
    Given the carousel design exposes images.slides and images.hero
    When the blog post page renders
    Then no blog body image is built from design.images.slides
    And the hero is the post's own cover, not design.images.hero

  Scenario: A post still renders when the carousel design is absent
    Given design_tokens is missing
    When the blog post page renders
    Then the post's own cover and section images still render
    And the default theme is applied
