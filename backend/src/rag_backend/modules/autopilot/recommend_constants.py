"""Recommended publish slots for the Telegram picker (AE-0404).

Each candidate slot (a São Paulo day and a whole hour) gets a score that
blends three signals, each normalised to 0..1:

- **audience**: Instagram ``online_followers`` (followers online per UTC hour),
  min-max normalised over the hours Graph returned;
- **performance**: the engagement of our published posts in the same
  (weekday, hour) bucket, shrunk by ``n / (n + SHRINKAGE_POSTS)`` so a handful
  of posts barely moves it;
- **prior**: the editorial plan (POV: Tue/Thu 12:00; otherwise the AE-0370
  slots 12:00, 18:00 and 21:00).
"""

from __future__ import annotations

# Blend weights. Audience outranks the prior on its own; performance needs
# many posts (shrinkage) before it outranks the prior.
WEIGHT_PRIOR = 0.3
WEIGHT_AUDIENCE = 0.4
WEIGHT_PERFORMANCE = 0.5
SHRINKAGE_POSTS = 5
# Prior strength: the plan's own slot, and the default slots for a POV run.
PRIOR_PLAN = 1.0
PRIOR_SECONDARY = 0.5

# Whole hours offered by the picker, São Paulo time.
CANDIDATE_HOURS: tuple[int, ...] = tuple(range(8, 23))
PICKER_DAYS = 7
TOP_TIMES_PER_DAY = 4
DAY_BUTTONS_PER_ROW = 3
# Days whose best slot scores within this share of the best day get a star.
STARRED_DAY_SHARE = 0.95
MAX_STARRED_DAYS = 3
HOURS_PER_DAY = 24

# Reason codes, and the text shown in the picker and the confirmation.
REASON_AUDIENCE = "audience"
REASON_PERFORMANCE = "performance"
REASON_POV_PLAN = "pov_plan"
REASON_DEFAULT_SLOT = "default_slot"
REASON_ALTERNATIVE = "alternative"
TEXT_REASON_AUDIENCE = "⭐ seus seguidores mais online"
TEXT_REASON_PERFORMANCE = "⭐ melhor engajamento ({posts} posts)"
TEXT_REASON_POV_PLAN = "padrão do plano POV"
TEXT_REASON_DEFAULT_SLOT = "horário padrão"
TEXT_REASON_ALTERNATIVE = "horário alternativo"
STAR = "⭐"
DAY_LABEL_FORMAT = "{weekday} {date}"
DAY_DATE_FORMAT = "%d/%m"
WEEKDAY_ABBREVIATIONS: tuple[str, ...] = (
    "Seg",
    "Ter",
    "Qua",
    "Qui",
    "Sex",
    "Sáb",
    "Dom",
)

# Graph: ``GET /{ig-user-id}/insights?metric=online_followers&period=lifetime``.
GRAPH_PATH_USER_INSIGHTS = "/{ig_user_id}/insights"
METRIC_ONLINE_FOLLOWERS = "online_followers"
FIELD_PERIOD = "period"
PERIOD_LIFETIME = "lifetime"
AUDIENCE_HTTP_TIMEOUT_SECONDS = 10.0
# The audience is read from Graph at most once per this many hours.
AUDIENCE_TTL_HOURS = 24
TABLE_AUDIENCE_HOURS = "instagram_audience_hours"
# Published posts read for the performance signal.
PERFORMANCE_POST_LIMIT = 200

LOG_AUDIENCE_FETCH_FAILED = "autopilot_audience_fetch_failed"
LOG_AUDIENCE_SAVE_FAILED = "autopilot_audience_save_failed"
