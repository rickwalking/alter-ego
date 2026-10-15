Feature: POV layouts, photo library, pov_editorial images and Radar IA v7 (AE-0376, ADR-0021)

  # --- Layouts ----------------------------------------------------------------

  Scenario: Hook slide uses the owner's photo
    Given a POV project with a hook photo
    When slide 1 is rendered
    Then the slide shows the photo and the hook and no generated artwork

  Scenario: Hook slide without a photo
    Given a POV project without a hook photo
    When slide 1 is rendered
    Then the slide shows only the hook on the solid background

  Scenario: Layout by role
    Given a 9-slide POV deck
    When it is rendered
    Then slide 1 is hook_face, slides 2-3 are statement, slide 7 is insight_quote, slide 8 is save_checklist and slide 9 is cta_follow
    And the point slides keep the format's layout

  Scenario: Radar IA decks keep today's layouts
    Given a Radar IA deck
    When it is rendered
    Then no POV layout is used

  Scenario: Save checklist shows 3 to 5 items
    Given a save slide with 6 summary points
    When it is rendered
    Then the checklist shows the first 5

  Scenario: CTA by goal
    Given a POV project with cta_goal "comment"
    When the last slide is rendered
    Then it shows "Discorda? Me diz nos comentários."
    And the website is shown once, small

  # --- Images -----------------------------------------------------------------

  Scenario: Only point slides get artwork
    Given a POV project with image preset pov_editorial and 9 slides
    When the image phase picks its slides
    Then artwork is requested only for the 3 point slides

  Scenario: Radar IA v4 skips the news and verdict artwork
    Given a Radar IA project stamped hero_lower_third_v4
    When the image phase picks its slides
    Then artwork is requested for the hook and impact slides only

  Scenario: Legacy decks keep the slide-type rule
    Given a project stamped hero_lower_third_v3
    When the image phase picks its slides
    Then every intro, summary, content and closing slide with a prompt gets artwork

  Scenario: The Radar IA scout never picks the POV preset
    Then pov_editorial is not a scout image style

  # --- Photo library ------------------------------------------------------------

  Scenario: Transparent photos keep their transparency
    Given a PNG with an alpha channel
    When it is uploaded
    Then the stored WebP keeps the alpha channel

  Scenario: Photo library is owner scoped
    Given two users with uploaded hook photos
    When the first user lists hook photos
    Then only their photos are returned
    And the second user's photo image answers 403

  Scenario: Slide-1 photo for a POV carousel
    Given an owner's hook photo and a POV carousel
    When the owner sets it as the slide-1 photo
    Then the project stores it and the photo is staged where the slides render

  Scenario: Exported slides find staged assets
    Given slide HTML that references "images/" and "assets/" files
    When it is exported from a language folder
    Then both paths point one level up

  # --- Radar IA v7 ----------------------------------------------------------------

  Scenario: Radar IA v4 uses v7 prompts and hooks
    Given a news_analysis project stamped hero_lower_third_v4
    When the outline is generated
    Then the v7 outline prompt with the angle rule and roles is used
    And slide 1 carries 5 hook candidates from the sources only
    And slides are drafted with the v7 content prompt by role
