Feature: The scout supplies a repost's source video (AE-0641)
  Instagram's API hands out a 360p copy of an old Reel. When Pedro has the
  original take, the scout uploads it and the repost renders from it. Every
  other rule still applies, and nothing publishes without Pedro's approval.

  Background:
    Given the autopilot API key is configured

  Scenario: An H.264 portrait video is stored and gets an asset_id
    When the scout posts a 1080x1920 H.264 file of 86 s to /api/autopilot/assets/video
    Then the answer is 201 with asset_id, kind "video", width, height, duration_s and size_bytes
    And the file is kept under output/reposts/sources

  Scenario Outline: An unusable upload is refused and not kept
    When the scout posts <upload>
    Then the answer is <status> "<code>"
    And no file is left behind

    Examples:
      | upload                         | status | code                     |
      | no file part                   | 400    | source_file_missing      |
      | a file over 200 MB             | 413    | source_too_large         |
      | a file ffprobe cannot read     | 422    | source_not_video         |
      | an HEVC video                  | 422    | source_codec_unsupported |
      | a landscape or 480 px video    | 422    | source_not_portrait      |
      | a 2 s or 200 s video           | 422    | source_duration_invalid  |

  Scenario: Uploads no draft used within 24 hours are swept
    Given an upload from 25 hours ago that no draft used
    When the scout uploads another video
    Then the old file and its row are deleted
    But an upload a draft used is kept

  Scenario: A draft names the upload as its source
    Given a fresh unused upload
    When the scout posts a repost draft with source_asset_id
    Then the answer is 202 "pending_approval"
    And the upload is claimed by the draft
    And the final length is checked against the upload's duration

  Scenario: An upload makes a Reel without a Graph video repostable
    Given a Reel whose video Graph withholds
    When the scout posts a draft with a fresh upload as source_asset_id
    Then the draft is accepted

  Scenario Outline: A bad source_asset_id is refused
    When the scout posts a draft whose source_asset_id is <source>
    Then the answer is 422 "source_asset_invalid"

    Examples:
      | source                           |
      | unknown                          |
      | already used by another draft    |
      | older than 24 hours              |
      | taken by a draft created at once |

  Scenario: The request hash covers the source
    Then a draft with source_asset_id hashes differently from one without
    And a draft without it hashes exactly as before

  Scenario: The worker renders from the upload
    Given a pending draft with an upload
    When the worker renders it
    Then ffmpeg reads the upload, not the Graph video
    And the upload is deleted once the preview is rendered

  Scenario: A missing upload fails the render
    Given a pending draft whose upload file is gone
    When the worker renders it
    Then the draft fails with "source_unavailable"

  Scenario: nginx lets a 200 MB upload through to the backend
    Then both nginx configs have a /api/autopilot/assets/video location with a 210m body limit
