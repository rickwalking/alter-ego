Feature: Telegram "Fix issues" button repairs carousel content deterministically (AE-0367)

  A carousel can reach the owner's Telegram review with quality issues: a
  heading that starts lowercase, a slide that renders only its title, an EN
  slide that is still Portuguese, or mangled <strong> tags. The owner taps
  "🛠 Fix issues" instead of editing by hand or regenerating a whole phase. The
  webhook only queues the fix; the worker tick repairs the persisted slides and
  the workflow presentation copy, re-renders, and sends a fresh review.

  Background:
    Given an autopilot run awaiting the owner at final review
    And its carousel is stamped with presentation policy hero_lower_third_v3

  Scenario: The review message lists the issues and offers the fix
    Given slide 5's heading starts lowercase and slide 4 has no body or features
    When the review message is built
    Then it lists "Slide 5: heading starts lowercase" and "Slide 4: no body or features"
    And it lists at most 5 issue lines
    And the keyboard has Approve, Rework, Reject and "🛠 Fix issues"

  Scenario: A clean carousel offers no fix button
    Given every slide passes the content-quality rules
    When the review message is built
    Then it lists no issue lines
    And the keyboard has only Approve, Rework and Reject

  Scenario: Happy path: the owner taps Fix issues
    Given slide 5's heading starts lowercase and "argon" is lowercase where the outline says "Argon"
    And slide 4 has no body or features but its outline has 3 key points
    When the owner taps "🛠 Fix issues"
    Then the run moves from awaiting_owner to reworking with reason owner_autofix
    And the old keyboard message reads "Superseded by fixed version"
    And the webhook does not run the repair itself
    When the worker tick runs
    Then the persisted slide 5 heading starts uppercase and reads "Argon"
    And slide 4 renders 3 features built from its key points with allowed icons
    And the carousel is re-rendered without regenerating hero images
    And a new album and a fresh review keyboard are sent
    And the run is awaiting_owner again

  Scenario: Nothing to fix
    Given every slide passes the content-quality rules
    When the owner taps "🛠 Fix issues"
    Then the owner is told "Nothing to fix"
    And the run stays awaiting_owner and no fix is queued

  Scenario: Partial fix: issues that need a rework remain
    Given slide 3's body is too long and slide 5's heading starts lowercase
    When the owner taps "🛠 Fix issues" and the worker tick runs
    Then slide 5 is fixed
    And the new review message still lists the slide 3 issue
    And the keyboard offers Rework

  Scenario: Double tap fixes once
    When the owner taps "🛠 Fix issues" twice
    Then the fix is queued once
    And the second tap is answered "already handled"
    And the repair runs once on the worker tick

  Scenario: A non-owner tap is ignored
    When a stranger taps "🛠 Fix issues"
    Then the run stays awaiting_owner
    And nothing is queued and no reply is sent

  Scenario: EN re-translation fails
    Given slide 6's EN copy is the Portuguese copy pasted as-is
    And the translation model fails on every attempt
    When the owner taps "🛠 Fix issues" and the worker tick runs
    Then the model is called at most twice for the EN fields only
    And slide 6 keeps its current EN copy
    And the new review message lists "Slide 6 EN: not translated"
