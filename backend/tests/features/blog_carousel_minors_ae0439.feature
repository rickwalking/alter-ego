Feature: Blog and carousel minors from the 2026-10-19 QA wave (AE-0439)
  Evidence: ~/alter-ego-qa/2026-10-19-qa-full/REPORT.md (F-07, F-12, F-13,
  F-14) and the orchestrator queue follow-ups for PR #154 (AE-0433) and
  #155 (AE-0434): a Radar IA create never persisted slide_count (F-07), a
  0-10 persona judge answer was stored raw (F-12), the workflow state
  exposed container image paths (F-13), anonymous draft blog image 404s
  were cached at the edge (F-14), other missing images still reported
  image_decode_timeout (#155a), content-generation scoring had no fallback
  judge (#154A), a stale passing score was trusted after an unscored
  rewrite (#154B) and the wait check was loose (#154C).

  Background:
    Given a Radar IA carousel project with 7 slides
    And the owner persona

  Scenario: A Radar IA create without slide_count stores 7
    Given a create request without slide_count
    When the content-mode fields are resolved
    Then the stored slide_count is 7

  Scenario: An explicit Radar IA slide_count of 8 is kept
    Given a create request with slide_count 8
    When the content-mode fields are resolved
    Then the stored slide_count is 8

  Scenario: A blog from a 7-slide deck without a stored slide_count gets 7 sections
    Given a carousel whose slide_count is null
    And the carousel has 7 slide rows
    When the blog resolves the section count
    Then the count is 7, not the slides_config size of 6

  Scenario: Stored persona scores are on 0-100 even for a raw 0-10 judge answer
    Given the persona judge answers 8.5 overall with sub-scores under 10
    When the content phase stores the slide's score
    Then the stored overall is 85
    And the stored sub-scores are on 0-100

  Scenario: A stored raw 0-10 row still reads on 0-100
    Given a persona_scores entry with overall 8.5
    When the lowest overall is read
    Then the score is 85

  Scenario: The workflow state maps image_assets to owner preview URLs
    Given workflow state image_assets hold container paths
    When the workflow state response is built
    Then image_assets are /api/carousels/{id}/preview/images/{file} URLs
    And a value that is already a URL passes through

  Scenario: An anonymous draft blog image 404 is never cached
    Given a draft blog post with a stored image
    When an anonymous visitor requests the image file
    Then the response is 404
    And its Cache-Control is no-store

  Scenario: A missing image reports image_load_failed, not a decode timeout
    Given an export page whose image file is missing
    When the image decode check runs
    Then the report says image_load_failed
    And never image_decode_timeout

  Scenario: A real decode timeout still reports image_decode_timeout
    Given an export page whose image decode stalls
    When the image decode check runs
    Then the report says image_decode_timeout

  Scenario: The content-generation judge retries on the queue's next model
    Given the fast role's queue has two models
    And the persona judge times out on the first model
    And the next model of the queue scores the text 80
    When the content phase scores a slide
    Then the second call goes to the next model of the queue
    And the slide's stored score is 80

  Scenario: A passing gate with pending re-scores waits instead of approving
    Given slide 3 is marked rescore_pending with a stale passing score 80
    And the gate re-read passes
    And the persona judge gives no score on any model
    When the runner ticks
    Then the run is not approved and stays generating
    And no autopilot_slide_autofix_escalated is logged

  Scenario: A pending slide that scores again clears its marker
    Given slide 3 is marked rescore_pending with a stale passing score 80
    And the gate re-read passes
    And the persona judge now scores slide 3's current text 82
    When the runner ticks
    Then slide 3's stored score is 82 without the pending marker
    And the gate is approved

  Scenario: A wait fires only when the voice floor is the sole failure
    Given the gate also fails on a forbidden phrase
    And slide 3 is marked rescore_pending
    When the runner ticks
    Then the run escalates instead of waiting
