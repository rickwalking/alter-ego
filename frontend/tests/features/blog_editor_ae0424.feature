Feature: Blog section editor, images, versions and publish (AE-0424)
  The blog editor edits a v2 document as section cards with per-section and
  cover image controls, rewrites a section in the persona voice, shows the
  voice score, guards unsaved changes, appends a version snapshot on save, and
  offers PT/EN content buttons, review actions, Publish/Unpublish and scheduling.

  Background:
    Given the owner is logged in as "Pedro"
    And the post is a v2 document under edit

  # --- section editing ---

  Scenario: Editing a section heading and body persists it
    Given the post has sections sec_1 and sec_2
    When the owner edits sec_1's heading and body and saves
    Then the stored sec_1 heading and body_md are updated
    And sec_2 is unchanged

  Scenario: Adding a section inserts a new stable id
    Given the post has two sections
    When the owner adds a section and saves
    Then content.sections has three entries
    And the new section has a fresh sec_<uuid4> id

  Scenario: Deleting a section removes it without touching the others
    Given the post has three sections
    When the owner deletes the middle section and saves
    Then content.sections has two entries
    And the remaining sections keep their ids and order

  Scenario: Reordering sections keeps each section's own image
    Given two sections each with its own image
    When the owner swaps their order and saves
    Then the stored order is swapped
    And each image stays attached to its own section id

  # --- images ---

  Scenario: Generating a section image stores url, alt and prompt
    Given a section with heading "O que aconteceu"
    When the owner clicks generate on that section's image slot
    Then the provider bytes are persisted to the blog-images store
    And the section image is stored with the canonical url, model "gpt-image-2" and a prompt
    And its alt defaults to the heading (non-empty)

  Scenario: Regenerating uses an edited prompt
    Given a section with an existing image
    When the owner edits the prompt and regenerates
    Then the new image replaces the old one
    And the stored prompt is the edited prompt

  Scenario: Removing a section image clears the slot
    Given a section with an image
    When the owner removes the image and saves
    Then the section image is null

  Scenario: Editing alt and caption persists
    Given a section with an image
    When the owner sets alt "Gráfico de custos" and a caption and saves
    Then the stored image alt and caption are updated

  Scenario: An empty alt is rejected
    Given a section image slot
    When the owner clears the alt and saves
    Then a validation error is shown
    And the save is not applied

  Scenario: A failed image generation shows a visible retry
    Given the image provider fails
    When the owner clicks generate on a section image
    Then an error is shown on that slot
    And a retry control is available
    And the rest of the document is editable

  # --- cover ---

  Scenario: The cover can be generated, regenerated and removed
    Given the post has no cover
    When the owner generates the cover
    Then the cover is stored
    When the owner regenerates the cover
    Then the cover is replaced
    When the owner removes the cover and saves
    Then content.cover is null

  Scenario: Saving keeps featured_image_url equal to cover.url
    Given the post has a cover with url "https://cdn/c.jpg"
    When the owner saves the post
    Then featured_image_url equals "https://cdn/c.jpg"

  # --- voice ---

  Scenario: Rewrite this section in my voice replaces only that section
    Given the persona "Pedro's Professional Voice" is bound
    When the owner clicks "Rewrite this section in my voice" on sec_1
    Then only sec_1.body_md is replaced
    And the other sections are unchanged

  Scenario: The voice score is shown from content.quality
    Given content.quality.voice_score is 82
    Then the editor shows a voice score of 82 with its breakdown

  # --- versions and unsaved guard ---

  Scenario: Saving appends a version snapshot visible in the sidebar
    Given the post has no saved versions
    When the owner saves a change
    Then the version sidebar lists one new version

  Scenario: Restoring a version loads it into the editor
    Given the post has two saved versions
    When the owner restores version 1
    Then the editor shows version 1's content
    And a new version records the restore

  Scenario: Leaving with unsaved changes is guarded
    Given the owner changed a section but did not save
    When the owner navigates away or closes the tab
    Then a leave-confirmation is shown
    And the change is not silently lost

  Scenario: A concurrent save conflict is surfaced
    Given the post is at lock version 2
    And another tab saved first (server lock version 3)
    When the owner saves with If-Match 2
    Then a conflict message is shown
    And the owner's unsaved text is preserved in the editor

  Scenario: Typing during an in-flight save is kept
    Given the owner clicked Save
    When the owner keeps typing before the save answers
    Then the new text stays in the editor as unsaved changes

  Scenario: A save that races our own image generation is retried
    Given an image generation finishes while a save is in flight
    When the save gets a 409 because of that generation
    Then the save is retried once on the new lock version
    And no conflict message is shown

  Scenario: Review controls wait for a running slot action
    Given an image, rewrite or translation is running
    Then the submit/approve/publish/schedule controls are disabled

  Scenario: An exhausted image budget is explained on the slot
    Given the post used its whole image budget
    When the owner clicks generate on a slot
    Then the slot shows the budget message

  # --- publish ---

  Scenario: Publish turns an approved post into a published post
    Given an approved post with at least one non-empty section
    When the owner clicks Publish
    Then the post status is "published"
    And it becomes visible at /blog/{id}

  Scenario: Publishing a draft is blocked by the status guard
    Given a valid draft with at least one non-empty section
    When the owner clicks Publish
    Then the status-guard error is shown
    And the post stays "draft"
    And the editor offers the review flow instead

  Scenario: Publishing an approved empty document is rejected
    Given an approved post whose sections all have empty bodies
    When the owner clicks Publish
    Then a validation message is shown
    And the post stays "approved"

  Scenario: Unpublish returns the post to draft and 404s publicly
    Given a published post
    When the owner clicks Unpublish
    Then the post status is "draft"
    And /blog/{id} returns not-found

  Scenario: Editor copy is localized
    Given the pt locale
    Then the section, image, version and publish controls use pt messages

  # --- language buttons (owner revision) ---

  Scenario: PT/EN buttons switch the edited document
    Given the post has a PT document and an EN translation
    When the owner clicks "EN" in the editor header
    Then the EN cover and sections are shown and editable
    And the PT document is unchanged

  Scenario: Editing the EN document never mutates PT
    Given the editor is showing EN
    When the owner edits an EN section and saves
    Then only content.translations.en is changed
    And the PT cover and sections are byte-identical

  Scenario: A missing EN translation is read-only with a generate action
    Given the post has no content.translations.en
    When the owner clicks "EN"
    Then the EN tab is read-only
    And a "Generate EN translation" action is shown

  # Public PT/EN content-switch scenarios live in blog_sections_ae0423.feature (AE-0423 owns the public render).

  # --- review + scheduled publish (owner revision) ---

  Scenario: Submit for review moves the post to under review
    Given a draft post and a reviewer
    When the owner submits it for review
    Then the post status is "under_review"

  Scenario: Approve moves the post to approved
    Given an under-review post
    When the reviewer approves it
    Then the post status is "approved"

  Scenario: Reject returns the post to draft with a reason
    Given an under-review post
    When the reviewer rejects it with a reason
    Then the post status is "draft"
    And the reason is stored in editor_comments

  Scenario: Scheduling publishes at the chosen time
    Given an approved post
    When the owner schedules a future publication
    Then scheduled_publish_at is stored
    And the due-post sweep publishes it at that time

  Scenario: Scheduling in the past is rejected
    Given an approved post
    When the owner schedules a timestamp before the minimum lead time
    Then a validation error is shown
    And the post stays "approved"

  Scenario: Cancelling a schedule leaves the post approved
    Given an approved scheduled post
    When the owner clicks "Cancel schedule"
    Then scheduled_publish_at is null
    And the post stays "approved"

  Scenario: Editing after approval resets to draft and clears the schedule
    Given an approved or scheduled post
    When the owner edits content and saves
    Then the post status becomes "draft"
    And scheduled_publish_at is null
    And the review controls are shown again

  Scenario: Self-review is allowed for the single author
    Given BLOG_ALLOW_SELF_REVIEW is true
    And the owner is the only editor
    When the owner submits and approves their own post
    Then the post reaches "approved"

  Scenario: Self-review is rejected when disabled
    Given BLOG_ALLOW_SELF_REVIEW is false
    And the owner is the author
    When the owner submits their own post for review
    Then a 400 self-review error is shown
    And the post stays "draft"

  Scenario: Publish now auto-approves when self-review is enabled
    Given BLOG_ALLOW_SELF_REVIEW is true
    And a valid draft
    When the owner clicks "Publish now"
    Then the post is submitted and self-approved in the same request flow
    And the post status is "published"

  Scenario: A non-migrated row shows a blocking migration banner
    Given a legacy-markdown row whose save fails with InvalidBlogDocumentError
    When the editor attempts a content write
    Then a blocking "migration pending" banner is shown with the API error
    And the editor does not parse the legacy markdown itself
    And no partial content is saved
