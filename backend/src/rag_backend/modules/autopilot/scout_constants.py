"""Scout-failure notice limits (QA r1 S-W3).

Kept beside ``constants.py`` so neither file exceeds the 400-line limit.
Delivered scout failures are recorded as outbox rows of their own event
type, so the Telegram dispatcher (which only reads run aggregates) never
sends them a second time.

Concurrent scout-failed POSTs serialize the cap read and record with an advisory lock
keyed by “APSF” (autopilot scout failure).
"""

EVENT_TYPE_SCOUT_FAILED = "content.autopilot.scout_failed"
AGGREGATE_TYPE_AUTOPILOT_SCOUT = "autopilot_scout"
PAYLOAD_SCOUT_REASON = "reason"
SCOUT_FAILURES_PER_DAY = 3
SCOUT_FAILURE_WINDOW_HOURS = 24
DETAIL_SCOUT_DAILY_CAP = "scout_failure_daily_cap"
DETAIL_SCOUT_DUPLICATE = "scout_failure_duplicate"
SCOUT_SUPPRESSED_DETAILS = (DETAIL_SCOUT_DAILY_CAP, DETAIL_SCOUT_DUPLICATE)
SCOUT_FAILURE_LOCK_KEY = 0x41505346
