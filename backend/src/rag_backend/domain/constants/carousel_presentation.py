"""Constants for the carousel presentation contract (hero_lower_third_v1)."""

PRESENTATION_POLICY_LEGACY_NEON_V2 = "legacy_neon_v2"
PRESENTATION_POLICY_HERO_LOWER_THIRD_V1 = "hero_lower_third_v1"

DEFAULT_PRESENTATION_POLICY_VERSION = PRESENTATION_POLICY_HERO_LOWER_THIRD_V1
LEGACY_PRESENTATION_POLICY_VERSION = PRESENTATION_POLICY_LEGACY_NEON_V2

CONTENT_KIND_FEATURES = "features"
CONTENT_KIND_STATS = "stats"
CONTENT_KIND_INSIGHT = "insight"

VALID_CONTENT_KINDS: frozenset[str] = frozenset({
    CONTENT_KIND_FEATURES,
    CONTENT_KIND_STATS,
    CONTENT_KIND_INSIGHT,
})

SUMMARY_POINT_COUNT = 3
STAT_ITEM_COUNT = 3
FEATURE_ITEM_MIN = 2
FEATURE_ITEM_MAX = 4
CLOSING_ACTION_MIN = 3
CLOSING_ACTION_MAX = 4
CANONICAL_SLIDE_COUNT = 7

ERR_ICON_NAME_NOT_ALLOWLISTED = "icon_name is not in the Lucide allowlist"
ERR_SUMMARY_POINT_COUNT = "summary_points must contain exactly 3 items"
ERR_CONTENT_KIND_INVALID = "content_kind is invalid"
ERR_FEATURES_REQUIRED = "features is required when content_kind is features"
ERR_FEATURES_COUNT = "features item count is out of range"
ERR_FEATURES_FORBIDDEN_FIELDS = (
    "stats and insight are forbidden for content_kind features"
)
ERR_STATS_REQUIRED = "stats is required when content_kind is stats"
ERR_STATS_COUNT = "stats must contain exactly 3 items"
ERR_STATS_FORBIDDEN_FIELDS = "features and insight are forbidden for content_kind stats"
ERR_INSIGHT_REQUIRED = "insight is required when content_kind is insight"
ERR_INSIGHT_FORBIDDEN_FIELDS = (
    "features and stats are forbidden for content_kind insight"
)
ERR_ACTIONS_COUNT = "actions item count is out of range"
ERR_LOCALE_SLIDE_TYPE_MISMATCH = (
    "presentation_pt and presentation_en slide_type must match"
)
ERR_SLIDE_TYPE_MISMATCH = "slide_type must match presentation copy slide_type"
ERR_SLIDE_COUNT = "slides must contain exactly 7 items"
ERR_VALID_REPORT_HAS_VIOLATIONS = "valid reports must not contain violations"
ERR_INVALID_REPORT_MISSING_VIOLATIONS = (
    "invalid reports must contain at least one violation"
)
ERR_BLOCKING_VALID_REPORT = "blocking cannot be true when validation_status is valid"

VALIDATION_STATUS_VALID = "valid"
VALIDATION_STATUS_INVALID = "invalid"

# Violation severity tiers (AE-0312). A report blocks approval only when at
# least one blocker-severity violation remains; warnings surface in the review
# panel without blocking. The code-level default for an absent severity is
# BLOCKER so a missing policy tag can never silently unblock a rule.
SEVERITY_BLOCKER = "blocker"
SEVERITY_WARNING = "warning"
DEFAULT_VIOLATION_SEVERITY = SEVERITY_BLOCKER
VALID_VIOLATION_SEVERITIES: frozenset[str] = frozenset({
    SEVERITY_BLOCKER,
    SEVERITY_WARNING,
})

DEFAULT_FEATURE_ICON_NAME = "shield-check"
DEFAULT_SUMMARY_POINT_ICON_NAME = "target"

VIOLATION_SLIDE_COUNT_INVALID = "slide_count_invalid"
VIOLATION_SLIDE_TYPE_INVALID = "slide_type_invalid"
VIOLATION_HEADING_EMPTY = "heading_empty"
VIOLATION_HEADING_NOT_SENTENCE_CASE_EN = "heading_not_sentence_case_en"
VIOLATION_HEADING_NOT_SENTENCE_CASE_PT = "heading_not_sentence_case_pt"
VIOLATION_BODY_NOT_SENTENCE_CASE_PT = "body_not_sentence_case_pt"
# AE-0366: EN body sentence case + a non-empty copy area under the heading.
VIOLATION_BODY_NOT_SENTENCE_CASE_EN = "body_not_sentence_case_en"
VIOLATION_BODY_EMPTY = "body_empty"
# AE-0366 quality rubric: objective structure/markup/translation checks.
VIOLATION_CLOSING_ACTIONS_MISSING = "closing_actions_missing"
VIOLATION_SUMMARY_POINTS_MISSING = "summary_points_missing"
VIOLATION_TRANSLATION_NOT_ENGLISH = "translation_not_english"
VIOLATION_EMPHASIS_MARKUP_INVALID = "emphasis_markup_invalid"
# AE-0436: the per-locale emphasis convention (AE-0403/AE-0414) — PT ``**…**``,
# EN ``<strong>…</strong>`` — is a gate rule, not just an editor hint: a field
# written with the other locale's markup is a blocker the deterministic repair
# normalizes at write time.
VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH = "emphasis_markup_locale_mismatch"
# Minimum complete items (title + body) the rubric requires per slide type.
MIN_CLOSING_ACTIONS = 3
MIN_SUMMARY_POINTS = 3
MIN_CONTENT_FEATURES_WITHOUT_BODY = 3
# EN copy identical to PT copy is "not translated" only past this length, so a
# brand-only heading ("Argon") that is legitimately the same is not flagged.
MIN_UNTRANSLATED_COMPARE_CHARS = 12
VIOLATION_PROPER_NOUN_CASING = "proper_noun_casing"
# AE-0401: copy-hygiene rules (prod carousel 98a2e2f0: a fenced JSON blob, an
# HTML tag and a Markdown heading became visible slide copy).
VIOLATION_STRUCTURED_PAYLOAD_IN_COPY = "structured_payload_in_copy"
VIOLATION_MARKUP_LEAK = "markup_leak"
VIOLATION_EMPHASIS_UNBALANCED = "emphasis_unbalanced"
VIOLATION_ASSISTANT_CHATTER = "assistant_chatter"
VIOLATION_PLACEHOLDER_TEXT = "placeholder_text"
VIOLATION_ENCODING_GARBLED = "encoding_garbled"
VIOLATION_COPY_TRUNCATED = "copy_truncated"
VIOLATION_BODY_TOO_SHORT = "body_too_short"
VIOLATION_WRONG_LANGUAGE = "wrong_language"
VIOLATION_REPEATED_TEXT = "repeated_text"
# An item title cut mid-phrase, its rest pushed into the item body.
VIOLATION_STRUCTURED_ITEM_SPLIT = "structured_item_split"
# A content slide body needs at least this many words (unless its features
# carry the copy); a field is judged for its language from this many words.
MIN_CONTENT_BODY_WORDS = 8
MIN_LANGUAGE_CHECK_WORDS = 4
# Other-language marker words needed before copy reads as the wrong language.
MIN_WRONG_LANGUAGE_MARKERS = 2
# A sentence counts as repeated only from this many words.
MIN_REPEATED_SENTENCE_WORDS = 3
VIOLATION_VISIBLE_EMOJI_FORBIDDEN = "visible_emoji_forbidden"
VIOLATION_DASH_PUNCTUATION_FORBIDDEN = "dash_punctuation_forbidden"
VIOLATION_BODY_TOO_LONG = "body_too_long"
VIOLATION_COPY_TOO_MANY_LINES = "copy_too_many_lines"
VIOLATION_HEADING_TOO_LONG = "heading_too_long"
VIOLATION_STRUCTURED_EXTRA_MISSING = "structured_extra_missing"
VIOLATION_STRUCTURED_EXTRA_SHAPE_MISMATCH = "structured_extra_shape_mismatch"
VIOLATION_HEADING_REPEATED_IN_BODY = "heading_repeated_in_body"
VIOLATION_DRAFTING_SCAFFOLD_PRESENT = "drafting_scaffold_present"
VIOLATION_SLIDE_PARSE_FAILED = "slide_parse_failed"
VIOLATION_TRANSLATION_MISSING = "translation_missing"
VIOLATION_TRANSLATION_SHAPE_MISMATCH = "translation_shape_mismatch"
VIOLATION_ICON_NAME_NOT_ALLOWLISTED = "icon_name_not_allowlisted"

ARTIFACT_BUILD_STATUS_STAGING = "staging"
ARTIFACT_BUILD_STATUS_READY = "ready"
ARTIFACT_BUILD_STATUS_ACTIVE = "active"
ARTIFACT_BUILD_STATUS_FAILED = "failed"
ARTIFACT_BUILD_STATUS_SUPERSEDED = "superseded"

VALID_ARTIFACT_BUILD_STATUSES: frozenset[str] = frozenset({
    ARTIFACT_BUILD_STATUS_STAGING,
    ARTIFACT_BUILD_STATUS_READY,
    ARTIFACT_BUILD_STATUS_ACTIVE,
    ARTIFACT_BUILD_STATUS_FAILED,
    ARTIFACT_BUILD_STATUS_SUPERSEDED,
})

CREATOR_ASSET_MEDIA_TYPE_WEBP = "image/webp"

LEGACY_STRUCTURED_EXTRA_KEYS: tuple[str, ...] = (
    "features",
    "stats",
    "insight",
    "summary_points",
    "tldr_strip",
)

LUCIDE_ICON_ALLOWLIST: frozenset[str] = frozenset({
    "book-open",
    "brain",
    "chart-column",
    "eye",
    "flask-conical",
    "message-circle",
    "newspaper",
    "shield-check",
    "target",
    "wrench",
})

MIGRATION_DOWNGRADE_BLOCKED_MESSAGE = (
    "Cannot downgrade carousel presentation contract migration while projects "
    "use presentation_policy_version='hero_lower_third_v1'. Regenerate or "
    "reassign those projects before downgrading."
)

__all__ = [
    "ARTIFACT_BUILD_STATUS_ACTIVE",
    "ARTIFACT_BUILD_STATUS_FAILED",
    "ARTIFACT_BUILD_STATUS_READY",
    "ARTIFACT_BUILD_STATUS_STAGING",
    "ARTIFACT_BUILD_STATUS_SUPERSEDED",
    "CANONICAL_SLIDE_COUNT",
    "CLOSING_ACTION_MAX",
    "CLOSING_ACTION_MIN",
    "CONTENT_KIND_FEATURES",
    "CONTENT_KIND_INSIGHT",
    "CONTENT_KIND_STATS",
    "CREATOR_ASSET_MEDIA_TYPE_WEBP",
    "DEFAULT_FEATURE_ICON_NAME",
    "DEFAULT_PRESENTATION_POLICY_VERSION",
    "DEFAULT_SUMMARY_POINT_ICON_NAME",
    "DEFAULT_VIOLATION_SEVERITY",
    "ERR_ACTIONS_COUNT",
    "ERR_BLOCKING_VALID_REPORT",
    "ERR_CONTENT_KIND_INVALID",
    "ERR_FEATURES_COUNT",
    "ERR_FEATURES_FORBIDDEN_FIELDS",
    "ERR_FEATURES_REQUIRED",
    "ERR_ICON_NAME_NOT_ALLOWLISTED",
    "ERR_INSIGHT_FORBIDDEN_FIELDS",
    "ERR_INSIGHT_REQUIRED",
    "ERR_INVALID_REPORT_MISSING_VIOLATIONS",
    "ERR_LOCALE_SLIDE_TYPE_MISMATCH",
    "ERR_SLIDE_COUNT",
    "ERR_SLIDE_TYPE_MISMATCH",
    "ERR_STATS_COUNT",
    "ERR_STATS_FORBIDDEN_FIELDS",
    "ERR_STATS_REQUIRED",
    "ERR_SUMMARY_POINT_COUNT",
    "ERR_VALID_REPORT_HAS_VIOLATIONS",
    "FEATURE_ITEM_MAX",
    "FEATURE_ITEM_MIN",
    "LEGACY_PRESENTATION_POLICY_VERSION",
    "LEGACY_STRUCTURED_EXTRA_KEYS",
    "LUCIDE_ICON_ALLOWLIST",
    "MIGRATION_DOWNGRADE_BLOCKED_MESSAGE",
    "MIN_CLOSING_ACTIONS",
    "MIN_CONTENT_BODY_WORDS",
    "MIN_CONTENT_FEATURES_WITHOUT_BODY",
    "MIN_LANGUAGE_CHECK_WORDS",
    "MIN_REPEATED_SENTENCE_WORDS",
    "MIN_SUMMARY_POINTS",
    "MIN_UNTRANSLATED_COMPARE_CHARS",
    "MIN_WRONG_LANGUAGE_MARKERS",
    "PRESENTATION_POLICY_HERO_LOWER_THIRD_V1",
    "PRESENTATION_POLICY_LEGACY_NEON_V2",
    "SEVERITY_BLOCKER",
    "SEVERITY_WARNING",
    "STAT_ITEM_COUNT",
    "SUMMARY_POINT_COUNT",
    "VALIDATION_STATUS_INVALID",
    "VALIDATION_STATUS_VALID",
    "VALID_ARTIFACT_BUILD_STATUSES",
    "VALID_CONTENT_KINDS",
    "VALID_VIOLATION_SEVERITIES",
    "VIOLATION_ASSISTANT_CHATTER",
    "VIOLATION_BODY_EMPTY",
    "VIOLATION_BODY_NOT_SENTENCE_CASE_EN",
    "VIOLATION_BODY_NOT_SENTENCE_CASE_PT",
    "VIOLATION_BODY_TOO_LONG",
    "VIOLATION_BODY_TOO_SHORT",
    "VIOLATION_CLOSING_ACTIONS_MISSING",
    "VIOLATION_COPY_TOO_MANY_LINES",
    "VIOLATION_COPY_TRUNCATED",
    "VIOLATION_DASH_PUNCTUATION_FORBIDDEN",
    "VIOLATION_DRAFTING_SCAFFOLD_PRESENT",
    "VIOLATION_EMPHASIS_MARKUP_INVALID",
    "VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH",
    "VIOLATION_EMPHASIS_UNBALANCED",
    "VIOLATION_ENCODING_GARBLED",
    "VIOLATION_HEADING_EMPTY",
    "VIOLATION_HEADING_NOT_SENTENCE_CASE_EN",
    "VIOLATION_HEADING_NOT_SENTENCE_CASE_PT",
    "VIOLATION_HEADING_REPEATED_IN_BODY",
    "VIOLATION_HEADING_TOO_LONG",
    "VIOLATION_ICON_NAME_NOT_ALLOWLISTED",
    "VIOLATION_MARKUP_LEAK",
    "VIOLATION_PLACEHOLDER_TEXT",
    "VIOLATION_PROPER_NOUN_CASING",
    "VIOLATION_REPEATED_TEXT",
    "VIOLATION_SLIDE_COUNT_INVALID",
    "VIOLATION_SLIDE_PARSE_FAILED",
    "VIOLATION_SLIDE_TYPE_INVALID",
    "VIOLATION_STRUCTURED_EXTRA_MISSING",
    "VIOLATION_STRUCTURED_EXTRA_SHAPE_MISMATCH",
    "VIOLATION_STRUCTURED_ITEM_SPLIT",
    "VIOLATION_STRUCTURED_PAYLOAD_IN_COPY",
    "VIOLATION_SUMMARY_POINTS_MISSING",
    "VIOLATION_TRANSLATION_MISSING",
    "VIOLATION_TRANSLATION_NOT_ENGLISH",
    "VIOLATION_TRANSLATION_SHAPE_MISMATCH",
    "VIOLATION_VISIBLE_EMOJI_FORBIDDEN",
    "VIOLATION_WRONG_LANGUAGE",
]
