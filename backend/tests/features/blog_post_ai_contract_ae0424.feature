Feature: Blog AI contract, section rewrite and versions on save (AE-0424)
  The blog AI endpoints return plain, validated results (never a fenced JSON
  envelope), a single section can be rewritten in the owner's voice, and every
  save appends a version snapshot so history and restore work.

  Background:
    Given an editor authenticated as EditorUser

  # --- ai-suggest strict JSON ---

  Scenario: A clean JSON envelope is returned as plain suggested_text
    Given the model returns {"suggestion_type":"improve","suggested_text":"Sharper lede"}
    When the editor POSTs /blog-posts/{id}/ai-suggest
    Then the response suggested_text is "Sharper lede"
    And no code fence appears anywhere in the response text

  Scenario: A fenced JSON envelope is unwrapped
    Given the model returns "```json\n{\"suggested_text\":\"Sharper lede\"}\n```"
    When the editor POSTs /blog-posts/{id}/ai-suggest
    Then the response suggested_text is "Sharper lede"
    And the response contains no "```" characters

  Scenario: A nested envelope is unwrapped once
    Given the model returns {"suggested_text":"{\"suggested_text\":\"Inner\"}"}
    When the editor POSTs /blog-posts/{id}/ai-suggest
    Then the response suggested_text is "Inner"

  Scenario: Non-JSON model output degrades to the raw text
    Given the model returns "Just improve it, please"
    When the editor POSTs /blog-posts/{id}/ai-suggest
    Then the response suggested_text is "Just improve it, please"
    And no error is raised

  Scenario: An empty model response is handled
    Given the model returns an empty string
    When the editor POSTs /blog-posts/{id}/ai-suggest
    Then the response suggested_text is empty
    And no fenced envelope is returned

  # --- rewrite one section in voice ---

  Scenario: Rewriting a section replaces only that section's body
    Given a v2 post whose section sec_1 has a generic body
    And the project persona is available
    When the editor POSTs /blog-posts/{id}/sections/sec_1/rewrite
    Then only sec_1.body_md is replaced with the persona-enforced text
    And the other sections are byte-identical

  Scenario: Rewriting a section without a persona uses the default persona
    Given a v2 post and no explicit persona_id on the request
    When the editor POSTs /blog-posts/{id}/sections/sec_1/rewrite
    Then PersonaAgent.enforce runs with the project/default persona
    And the response returns the updated section

  Scenario: Rewriting an unknown section returns 404
    Given a v2 post with section sec_1
    When the editor POSTs /blog-posts/{id}/sections/sec_unknown/rewrite
    Then the API responds 404

  # --- version snapshot on save ---

  Scenario: Every PUT appends a version snapshot in the save transaction
    Given a draft v2 post with no version history
    When the editor PUTs a changed document with the current If-Match
    Then version_history has exactly one new entry
    And the entry snapshots the title and content
    And the snapshot is written in the same transaction as the content update

  Scenario: Version history accumulates across saves
    Given a draft v2 post that has been saved twice
    When the editor GETs /blog-posts/{id}/versions
    Then it lists two versions in order

  Scenario: Stale If-Match still conflicts (AE-0296 unchanged)
    Given a draft v2 post at lock_version 2
    When the editor PUTs with If-Match 1
    Then the API responds 409 with detail "version_conflict"
    And no version snapshot is appended

  Scenario: A version can be restored
    Given a v2 post with two saved versions
    When the editor POSTs /blog-posts/{id}/restore-version/1
    Then the content matches version 1
    And a new snapshot records the restore

  # --- publish guard (existing workflow is authoritative) ---

  Scenario: Publishing a draft is rejected by the status guard
    Given a draft v2 post with a non-empty section
    When the editor POSTs /blog-posts/{id}/publish with the current If-Match
    Then the API responds with the existing status-guard error (400/409)
    And the post stays "draft"

  Scenario: Publishing an approved post with a valid section succeeds
    Given an approved v2 post with at least one non-empty section
    When the editor POSTs /blog-posts/{id}/publish with the current If-Match
    Then the API responds 200 with status "published"
    And published_at is set

  Scenario: Publishing an approved empty document is rejected
    Given an approved v2 post whose sections all have empty body_md
    When the editor POSTs /blog-posts/{id}/publish with the current If-Match
    Then the API responds 422
    And the post stays "approved"

  Scenario: Every content-mutating route enforces If-Match
    Given a v2 post at lock_version 2
    When the editor POSTs a section image/rewrite request with If-Match 1
    Then the API responds 409 with detail "version_conflict"

  Scenario: Generated images are persisted before they are stored
    Given the image provider returns a short-lived URL
    When the editor generates a section image
    Then the bytes are stored in the blog-images store
    And the document stores the canonical url, never the provider url

  # --- review + scheduled publish (existing workflow) ---

  Scenario: Submit review moves a draft to under_review
    Given a draft v2 post and a distinct reviewer
    When the editor POSTs /blog-posts/{id}/submit-review?reviewer_id=...
    Then the post status is "under_review"

  Scenario: Submit review rejects the author when self-review is disabled
    Given BLOG_ALLOW_SELF_REVIEW is false
    And the author is the only candidate reviewer
    When the editor POSTs /blog-posts/{id}/submit-review?reviewer_id=<author>
    Then the API responds 400 with ERR_SELF_REVIEW
    And the post stays "draft"

  Scenario: Self-review stores the author as reviewer when enabled
    Given BLOG_ALLOW_SELF_REVIEW is true
    When the author submits their own post for review
    Then the post status is "under_review"
    And reviewer_id is the author

  Scenario: Approve moves under_review to approved
    Given an under_review post assigned to reviewer R
    When R approves it
    Then the post status is "approved"

  Scenario: Reject returns an under_review post to draft with a reason
    Given an under_review post assigned to reviewer R
    When R rejects it with a reason
    Then the post status is "draft"
    And the reason is stored in editor_comments

  Scenario: Scheduling requires approved and a future timestamp
    Given an approved post
    When the owner schedules a timestamp beyond MIN_SCHEDULE_LEAD_SECONDS
    Then scheduled_publish_at is stored
    But scheduling a draft is rejected by the status guard

  Scenario: Cancelling a schedule leaves the post approved
    Given an approved scheduled post
    When the owner DELETEs /blog-posts/{id}/schedule
    Then scheduled_publish_at is null
    And the status is still "approved"

  Scenario: Editing after approval resets the post to draft and clears the schedule
    Given an approved or scheduled post
    When the owner PUTs changed content with the current If-Match
    Then the status becomes "draft"
    And scheduled_publish_at is null
    And the due-post sweep no longer publishes it

  # --- shared slot-write contract (review fixes; reused by AE-0425) ---

  Scenario: A save during image generation keeps both changes
    Given a v2 post at lock_version 2
    And the editor requests a section image with If-Match 2
    When another write commits while the provider runs (lock_version 3)
    Then the image is applied onto the latest document by section id
    And the API responds 200 at lock_version 4 with both changes

  Scenario: A section deleted during generation leaves no orphan file
    Given a section image generation is running
    When the section is deleted before the image is stored
    Then the API responds 404
    And the generated file is deleted from the blog-images store

  Scenario: The per-post image budget is enforced before spend
    Given a post that already generated BLOG_IMAGE_COST_CAP images
    When the editor requests another image
    Then the API responds 429 "blog_image_budget_exhausted"
    And the provider is not called

  Scenario: Stored files follow the real image type
    Given the provider returns PNG bytes
    When the image is stored
    Then the file is named .png and served as image/png

  Scenario: Draft images are private
    Given a draft post with a generated image
    When an anonymous visitor or another editor requests the image
    Then the API responds 404
    And the author gets it with "Cache-Control: private, no-store"
    And after publish anyone gets it with a revalidated public cache

  Scenario: Unreferenced image files are pruned
    Given an image no version snapshot or content references any more
    When the next content write commits
    Then that file is deleted from the store

  # --- version history (review fixes) ---

  Scenario: A version entry keeps the state before the write
    Given an AI-written draft
    When the owner saves an edit
    Then the version entry holds the original AI draft
    And the post response carries no version_history (GET /versions serves it)

  Scenario: Version history is bounded
    Given more than BLOG_VERSION_HISTORY_MAX saves
    Then the first entry (the original draft) and the newest entries are kept

  # --- publish guards on every path (review fixes) ---

  Scenario: An unpublishable post cannot be submitted, scheduled or swept
    Given an approved post whose sections are all empty
    When it is submitted for review, scheduled, or reached by the due-post sweep
    Then submit and schedule respond 422
    And the sweep does not publish it and clears its schedule

  Scenario: Status transitions bump lock_version
    Given a draft at lock_version 2
    When it is submitted and approved
    Then lock_version is 4
    And a save prepared at lock_version 2 responds 409

  # --- rewrite + suggest output (review fixes) ---

  Scenario: The rewrite output keeps its markdown
    Given the persona rewrite contains a link and parentheses
    Then the stored body keeps them (no input sanitizer on model output)
    And a rewrite longer than the section limit is rejected with 422

  Scenario: Prose before the fenced JSON is still unwrapped
    Given the model returns "Here you go:" followed by a fenced JSON envelope
    When the editor POSTs /blog-posts/{id}/ai-suggest
    Then the response suggested_text is the envelope's text

  # --- review round 2 ---

  Scenario: A save between image generation and its write keeps the image
    Given an image file is on disk and its slot write waits on the row lock
    When a save commits and prunes unreferenced files
    Then the pending file is kept (inside the prune grace window)
    And the image write stores a URL that serves 200

  Scenario: The cutover rollback stash is a reference
    Given ai_generation_metadata.blog_v2_cutover.featured_image_url names a stored file
    When any content write prunes the store
    Then that file is kept

  Scenario: The image budget is reserved before the spend
    Given a post one image below BLOG_IMAGE_COST_CAP
    When two image requests run in parallel
    Then exactly one is generated and the other responds 429
    And a reservation whose write fails stays counted

  Scenario: Transitions run under the row lock
    Given a slot write just reset an under-review post to draft
    When the reviewer approves it
    Then the approve sees the draft status and responds 400
