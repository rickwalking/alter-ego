Feature: Repost worker: render, notify, expire and publish (AE-0629)

  Scenario: The render command
    Given a draft with hook "Sua IA aprova o próprio código ruim." for 2.5 s and a 1-6.5 s trim
    Then ffmpeg trims, scales and pads to 1080x1920 at 30 fps, encodes H.264/AAC with a bitrate cap
    And draws each hook line from a text file with expansion disabled until t=2.5

  Scenario: A pending draft is rendered and sent to the owner
    Given a pending draft with no preview
    When the worker ticks
    Then the preview, cover and original cover are written
    And the owner receives the cover, the video and the prompt with four buttons
    And the draft stores preview_ready_at and the prompt's message id

  Scenario: A preview too large for Telegram is sent as a link
    Given a rendered preview over 49 MB
    Then the prompt carries the preview link instead of the video

  Scenario: A failed render ends the draft without messaging the owner
    When the download, ffmpeg or the duration check fails
    Then the draft is failed with the render error code and a readable error_message, and no prompt is sent

  Scenario: An unanswered draft expires after 12 hours
    Given a pending draft past expires_at
    When the worker ticks
    Then the draft is expired and the prompt says so

  Scenario: An approved draft publishes only once publish_at has passed
    Given an approved draft with publish_at in the future
    When the worker ticks
    Then no container is created
    When publish_at has passed
    Then a REELS container is created with the preview URL, caption, cover URL, share_to_feed and collaborators
    And the draft is processing

  Scenario: The original cover is used when the owner chose it
    Given an approved draft with cover_choice "original"
    Then the container's cover_url is the original cover file

  Scenario: A finished container is published
    Given a processing draft whose container reports FINISHED
    When the worker ticks
    Then media_publish is called, the permalink is read and the draft is published
    And the owner is told the new permalink

  Scenario: A container error or timeout fails the draft
    When the container reports ERROR, or stays IN_PROGRESS for more than 30 minutes
    Then the draft is failed with "container_error" or "container_timeout" and the owner is told

  Scenario: A transient Graph error is retried on the next tick
    When creating the container fails with a transient error
    Then the draft stays approved

  Scenario: Public files are served only for a live repost
    When Graph fetches /r/{id}/preview.mp4 of a pending, approved or published repost
    Then the file is served as video/mp4
    But an unknown file name, an unknown id, a rejected or expired repost answers 404
    And every answer, 200 or 404, carries Cache-Control no-store so a CDN never keeps a stale 404 or a dead file
