# Carousel Editorial Publish Fixes
# Traceability: docs/plans/carousel-editorial-publish-fixes.md

Feature: Seven-slide editorial outline contract
  As an editor
  I want carousels capped at seven slides
  So that output matches the legacy pipeline structure

  Scenario: Outline normalization trims excess slides
    Given an outline with 10 slides
    When the outline is normalized for editorial workflow
    Then the outline should contain exactly 7 slides
    And slide 1 should have type "intro"
    And slide 7 should have type "cta"

Feature: Editorial distribution pack
  As an editor
  I want captions and bilingual blog copy after content
  So that the publish workspace is ready for distribution

  Scenario: Blog markdown separates PT and EN when translations exist
    Given slide drafts with Portuguese body text
    And English translations for each slide
    When the distribution pack builds blog translations
    Then blog_pt should differ from blog_en when EN text is provided

Feature: Workflow board published column
  As an editor
  I want published carousels on the Kanban board
  So that I can find completed work

  Scenario: Kanban columns include published phase
    Given the workflow board API columns list
    Then the last column phase should be "published"
