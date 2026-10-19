Feature: Export never references artwork the images phase did not make (AE-0434)

  # Prod 2026-10-19, carousel 5344b6c6 (Radar IA hero_lower_third_v4, 7 slides):
  # the images phase illustrated slides 1, 3, 4 and 5 (image_scope.artwork_slides)
  # but the template pointed slides 2 (news summary) and 6 (verdict) at
  # images/slide_2.jpg and images/slide_6.jpg, so the final export failed with a
  # misleading image_decode_timeout.

  Background:
    Given a Radar IA project stamped "hero_lower_third_v4" with 7 slides
    And the slides of carousel 5344b6c6: intro, summary, content, content, content, closing (features), cta

  # --- Happy paths -------------------------------------------------------------

  Scenario: Summary and closing slides without images export
    Given the images phase wrote images for slides 1, 3, 4 and 5 only
    When the carousel HTML is rendered and the export preflight runs
    Then the HTML references artwork only for slides 1, 3, 4 and 5
    And slides 2 and 6 render a gradient artwork region without an image
    And the export preflight passes

  Scenario Outline: The images phase and the template agree on artwork slides
    Given a Radar IA "hero_lower_third_v4" deck of <count> slides with an image prompt on every slide
    When the images phase plans its slides and the template renders the deck in "<language>"
    Then the slides with an artwork image in the HTML are exactly the slides the images phase planned

    Examples:
      | count | language |
      | 7     | pt       |
      | 8     | pt       |
      | 7     | en       |

  # --- Edge cases --------------------------------------------------------------

  Scenario: Fixed contracts keep artwork on every lower-third slide
    Given a project stamped "hero_lower_third_v3" with 7 slides
    When the carousel HTML is rendered
    Then slides 1 to 6 reference images/slide_N.jpg

  Scenario: An owner-chosen GrokBot cover still renders on a slide without planned artwork
    Given a lower-third slide outside the artwork set with an explicit cover image
    When the slide is rendered
    Then the slide shows the cover image

  Scenario: Remote artwork is not checked on disk
    Given an HTML whose slide artwork is an absolute URL
    When the export preflight runs
    Then no artwork violation is reported

  # --- Failures ----------------------------------------------------------------

  Scenario: A missing artwork file fails the preflight with a clear reason
    Given an HTML whose slides 2 and 6 reference images that do not exist
    When the export preflight runs
    Then the export fails with "export_preflight_failed: slide_artwork_missing: slide_2, slide_6"
    And the report lists a blocking "slide_artwork_missing" violation for slides 2 and 6

  Scenario: The missing-artwork check runs before Playwright
    Given an HTML whose slide 2 references an image that does not exist
    When the slides are exported
    Then the export fails with "slide_artwork_missing: slide_2"
    And no browser is launched
