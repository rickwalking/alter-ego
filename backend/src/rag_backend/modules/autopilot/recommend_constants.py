"""Recommended publish slots for the Telegram picker.

Each candidate slot (a São Paulo day and a whole hour) gets a score that
blends three signals, each normalised to 0..1:

- **audience**: Instagram ``online_followers`` (followers online per UTC hour),
  min-max normalised over the hours Graph returned;
- **performance**: the engagement of our published posts in the same
  (weekday, hour) bucket, shrunk by ``n / (n + SHRINKAGE_POSTS)`` so a handful
  of posts barely moves it;
- **prior**: the editorial plan (POV: Tue/Thu 12:00; otherwise the slots 12:00, 18:00
  and 21:00).

Audience outranks the prior on its own; performance needs many posts (shrinkage) before
it does. The prior strength covers the plan's own slot and the default slots for a POV
run. The picker offers whole hours, São Paulo time, and stars the days whose best slot
scores within a set share of the best day. The audience comes from ``GET /{ig-user-
id}/insights?metric=online_followers&period=lifetime``, read at most once per the
refresh interval.
"""

from __future__ import annotations

WEIGHT_PRIOR = 0.3
WEIGHT_AUDIENCE = 0.4
WEIGHT_PERFORMANCE = 0.5
SHRINKAGE_POSTS = 5
PRIOR_PLAN = 1.0
PRIOR_SECONDARY = 0.5

CANDIDATE_HOURS: tuple[int, ...] = tuple(range(8, 23))
PICKER_DAYS = 7
TOP_TIMES_PER_DAY = 4
DAY_BUTTONS_PER_ROW = 3
STARRED_DAY_SHARE = 0.95
MAX_STARRED_DAYS = 3
HOURS_PER_DAY = 24

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

GRAPH_PATH_USER_INSIGHTS = "/{ig_user_id}/insights"
METRIC_ONLINE_FOLLOWERS = "online_followers"
FIELD_PERIOD = "period"
PERIOD_LIFETIME = "lifetime"
AUDIENCE_HTTP_TIMEOUT_SECONDS = 10.0
AUDIENCE_TTL_HOURS = 24
TABLE_AUDIENCE_HOURS = "instagram_audience_hours"
PERFORMANCE_POST_LIMIT = 200

LOG_AUDIENCE_FETCH_FAILED = "autopilot_audience_fetch_failed"
LOG_AUDIENCE_SAVE_FAILED = "autopilot_audience_save_failed"
