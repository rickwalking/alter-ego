Feature: Blog v1 dead code and blog_image_map are removed (AE-0428)

  Scenario: Carousel design payload has no blog image map
    Given a carousel with design tokens
    When the client fetches /api/carousels/{id}/design
    Then the response images object has no blog_image_map key
    And the blog public payload never reads that key

  Scenario: No v1 symbol survives in the code trees
    Given the cleanup is complete
    When the static guard scans backend/src and frontend/src (code files only)
    Then it finds no blog_image_map reference
    And it finds no v1 markdown-builder symbol
    And the carousel content prompt YAML may still mention blog_image_map (excluded, see Decision Log)

  Scenario: The guard fires on a seeded violation
    Given a temporary *.py/*.ts/*.tsx source file that reintroduces blog_image_map
    When the static guard runs
    Then it exits non-zero and names the offending file

  Scenario: Live editorial distribution helpers and columns are preserved
    Given blog_composition.py, editorial_distribution_blog.py and the carousel_projects.blog_markdown
      columns are used by the carousel editorial distribution pack
    When the cleanup is complete
    Then those helpers and columns still exist
    And the distribution pack tests still pass
