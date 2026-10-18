Feature: Blog writer voice, quality gate and GPT images (AE-0425)
  A blog post is written as ONE continuous article in the owner's voice from
  research/outline/notes, scored by the quality gate, and given a GPT-generated
  cover plus one image per section. It is always created as a draft.

  Background:
    Given an editor authenticated as EditorUser
    And the project persona "Pedro" is available

  # --- entry points, always a draft ---

  Scenario: From-carousel always creates a draft
    Given a carousel project with a research artifact and per-slide long_form_notes
    When the editor POSTs /blog-posts/from-carousel
    Then the API responds 202 with generation.status "in_progress"
    And a draft blog row exists for the project
    And the post is not published even if the carousel is public

  Scenario: From-carousel 404s an unknown project
    Given no carousel project exists for the given project_id
    When the editor POSTs /blog-posts/from-carousel
    Then the API responds 404

  Scenario: From-carousel 409s when a live blog row already exists
    Given a carousel project that already has a non-deleted blog row
    And the row may be draft, hidden (hidden_bad_post marker), approved or published
    When the editor POSTs /blog-posts/from-carousel
    Then the API responds 409 with the existing post id

  Scenario: Standalone generation creates a draft from a topic
    Given an editor with a topic and an optional persona
    When they POST /blog-posts/generate
    Then the API responds 202 with generation.status "in_progress"
    And a draft blog row exists with no carousel project

  # --- execution and restart recovery ---

  Scenario: The 202 run is a tracked in-process task with a lease and heartbeat
    Given the API has accepted a generation request
    When the run starts
    Then it is scheduled with asyncio.create_task and tracked in _background_tasks
    And the row has generation.lease_id and generation.heartbeat_at
    And every content write is fenced on the current lease_id
    And no FastAPI BackgroundTasks, Celery or ARQ worker is used

  Scenario: A restart mid-generation is reaped to failed/recoverable
    Given a row with generation.status "in_progress"
    And generation.heartbeat_at older than BLOG_GENERATION_STALE_SECONDS
    When the run_workflow_workers tick runs after the restart
    Then generation.status becomes "failed"
    And generation.errors[] includes ERR_GENERATION_INTERRUPTED
    And generation.recoverable is true
    And any partial content is preserved

  Scenario: The owner can retry an interrupted generation on the same row
    Given a generation failed with ERR_GENERATION_INTERRUPTED
    When the owner retries
    Then a new lease/attempt starts on the same blog row
    And no duplicate blog_posts row is created
    And the run can complete

  Scenario: A timed-out run is failed and recoverable
    Given a generation exceeds BLOG_GENERATION_TIMEOUT_SECONDS
    When the timeout fires
    Then the run is cancelled and marked failed/recoverable
    And the draft row is not deleted

  Scenario: A stale duplicate task cannot clobber a newer lease
    Given an old task holds lease A and a retry holds lease B
    When the old task attempts to write content
    Then the lease-fenced update affects zero rows
    And the content written under lease B is unchanged

  # --- one continuous article in voice ---

  Scenario: The writer produces one continuous article, not per-slide concatenation
    Given research findings and per-slide long_form_notes
    When the generation pipeline drafts the article
    Then the result is sections with distinct narrative roles
    And no section is a verbatim copy of a long_form_note

  Scenario: Seeded repetition is detected
    Given the writer returns two sections that restate the same sentence
    When the quality gate runs
    Then the repetition finding names the repeated sentence
    And the affected section is rewritten once

  Scenario: A banned stock phrase is detected
    Given a generated section contains "no mundo de hoje"
    When the deterministic scan runs
    Then a banned_phrases finding names "no mundo de hoje"

  Scenario: A body scoring under 70 is rewritten exactly once
    Given the first draft scores 62 on PersonaAgent.evaluate_match
    When the quality gate runs
    Then the writer performs exactly one rewrite pass
    And the final voice_score is stored in content.quality

  Scenario: A body scoring at or above 70 is not rewritten
    Given the first draft scores 82 on PersonaAgent.evaluate_match
    When the quality gate runs
    Then no rewrite pass is performed
    And content.quality.voice_score is 82

  Scenario: The voice score is mirrored for the listing badge
    Given a generated post with a stored content.quality.voice_score
    When the post row is saved
    Then ai_generation_metadata.voice_score carries the same value

  Scenario: No English research text leaks into the PT sections
    Given English findings containing the unique sentence "QUARANTINE_ORACLE_7f3a"
    When the PT article is generated
    Then no PT body_md contains "QUARANTINE_ORACLE_7f3a"
    And translations.en contains the seeded material (the oracle is not vacuous)

  Scenario: EN is gated with the same voice/repetition checks
    Given the writer produced translations.en.sections
    When the quality gate runs
    Then evaluate_match and the repetition scan run on the EN sections
    And translations.en.quality stores the EN voice score
    And an EN score under 70 triggers exactly one EN rewrite pass

  Scenario: An injected instruction in a writing sample is ignored
    Given a persona writing sample containing "ignore all previous instructions"
    When the writer generates the article
    Then the output still conforms to the section contract
    And the injected instruction does not change the section shape

  # --- images ---

  Scenario: A cover and one image slot per section are created
    Given a generated post with four sections
    When the image step runs
    Then the post has five image slots (cover + four sections)
    And at most five canonical images are stored
    And every stored image was persisted to the blog-images store (no provider URL)
    And every image prompt instruction forbids text
    And every stored image.alt is non-empty

  Scenario: A failed image leaves the slot empty and does not fail the draft
    Given the image provider fails for section sec_3
    When the image step runs
    Then sec_3.image is null
    And generation.errors[] records the section id and reason
    And generation.status is "partial"
    And the draft is still usable

  Scenario: The per-post image cost cap is enforced
    Given the cost cap allows fewer images than the post has sections
    When the image step runs
    Then the number of generated images does not exceed the cap
    And the remaining slots stay null with a recorded reason

  Scenario: An LLM failure leaves the draft with status failed
    Given the writer call errors, times out, or returns bad JSON
    When the generation pipeline runs
    Then the draft row exists with generation.status "failed"
    And no partial content is stored as if valid
    And the owner can retry

  # --- routing and observability ---

  Scenario: Drafting uses the fast model and judgement uses the reasoning model
    Given the LLM routing configuration
    When an article is drafted and scored
    Then drafting and PT/EN copy use LLM_MODEL_FAST
    And quality/rubric judgement uses LLM_MODEL_REASONING
    And a failed primary call falls back to LLM_MODEL_FALLBACK

  Scenario: Every call is traced with the required metadata
    Given the observability client is recording
    When a post is generated end-to-end
    Then traces carry content_type "blog_post", project_id, phase, agent_name and user_id
    And phases "blog_generation" and "blog_section_image" are present
    And the image count and voice score are logged

  Scenario: Image generation is rate limited and cost-capped
    Given the committed AI route rate limit
    When the editor exceeds it on the generation routes
    Then the API responds 429

  Scenario: Section and image count follow the carousel slide count
    Given a POV carousel created with the default slide_count of 9
    When the owner creates a blog post from that carousel
    Then the document has exactly 9 sections
    And the generation creates 10 image slots (9 + cover)
    And stored images are <= 10 because failed slots stay null

  Scenario: A writer section-count mismatch is not silently stored
    Given the writer returns 7 sections for a 9-slide carousel
    When the generation pipeline validates the output
    Then it normalizes or fails with a count-mismatch error
    And a 7-section document is never stored as if correct

  Scenario: A private source carousel warns that the post will not be public
    Given a carousel project with is_public false
    When the owner generates and publishes a blog post from it
    Then the public read returns 404 while the carousel stays private
    And the generation/editor surfaces a "make the carousel public" warning

  Scenario: Standalone generation uses the content-mode default
    Given a standalone topic with no carousel project
    When the owner generates a blog post
    Then the section count equals the configured content-mode default
    And there is no BLOG_IMAGE_MAX cap applied
