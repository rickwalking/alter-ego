/** Carousel creation form field identifiers. */
export const CREATE_FORM_FIELDS = {
  TOPIC: "topic",
  AUDIENCE: "audience",
  NICHE: "niche",
  THEME: "theme",
} as const;

/** Available carousel themes. */
export const CAROUSEL_THEMES = {
  CYBERSECURITY: "cybersecurity",
  AI_COMPETITION: "ai_competition",
  DEVELOPER_SKILLS: "developer_skills",
  SOURCE_CODE: "source_code",
  SOCIAL_ENGINEERING: "social_engineering",
  AUTO: "auto",
} as const;

/** Theme display labels for i18n keys (relative to "create" namespace). */
export const THEME_LABEL_KEYS = {
  cybersecurity: "themes.cybersecurity",
  ai_competition: "themes.ai_competition",
  developer_skills: "themes.developer_skills",
  source_code: "themes.source_code",
  social_engineering: "themes.social_engineering",
  auto: "themes.auto",
} as const;

/** Pipeline phase display order. */
export const PIPELINE_PHASES = [
  "researching",
  "drafting",
  "designing",
  "generating_images",
  "exporting",
  "completed",
] as const;

/** Status polling interval in milliseconds. */
export const STATUS_POLL_INTERVAL = 2000;

/**
 * How long a phase can go without a backend status update before the UI
 * surfaces a "stalled — retrying" warning. The Anthropic SDK retries on
 * `UnexpectedEof` silently, so a static phase past this threshold is a
 * good signal that something is wrong upstream.
 */
export const STALLED_THRESHOLD_MS = 30_000;

/** Navigation route for create page. */
export const CREATE_ROUTE = "/create";

/** Route pattern for create workspace. */
export const CREATE_WORKSPACE_ROUTE = (id: string) => `/create/${id}`;
