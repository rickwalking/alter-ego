/** Carousel creation form field identifiers. */
export const CREATE_FORM_FIELDS = {
  TOPIC: "topic",
  AUDIENCE: "audience",
  NICHE: "niche",
  THEME: "theme",
  IMAGE_PRESET: "image_preset",
} as const;

/** Image generation providers. */
export const IMAGE_MODELS = {
  GEMINI: "gemini",
  OPENAI: "openai",
} as const;

/** Image style presets. */
export const IMAGE_STYLES = {
  COMIC_NEON: "comic_neon",
  CINEMATIC: "cinematic",
  HYPERREAL: "hyperreal",
  NEO_ANIME: "neo_anime",
} as const;

/**
 * The compound (model, style) presets exposed in the UI. Only combos
 * the backend registers are selectable here — the API rejects anything
 * else with 422, so keeping the frontend list narrow prevents dead ends.
 */
export const IMAGE_PRESETS = [
  {
    value: "gemini__comic_neon",
    model: IMAGE_MODELS.GEMINI,
    style: IMAGE_STYLES.COMIC_NEON,
    labelKey: "imagePresets.gemini_comic_neon",
  },
  {
    value: "openai__hyperreal",
    model: IMAGE_MODELS.OPENAI,
    style: IMAGE_STYLES.HYPERREAL,
    labelKey: "imagePresets.openai_hyperreal",
  },
  {
    value: "openai__cinematic",
    model: IMAGE_MODELS.OPENAI,
    style: IMAGE_STYLES.CINEMATIC,
    labelKey: "imagePresets.openai_cinematic",
  },
  {
    value: "openai__neo_anime",
    model: IMAGE_MODELS.OPENAI,
    style: IMAGE_STYLES.NEO_ANIME,
    labelKey: "imagePresets.openai_neo_anime",
  },
] as const;

export const DEFAULT_IMAGE_PRESET = IMAGE_PRESETS[0].value;

/** Phase 5 per-slide image-generation lifecycle. */
export const SLIDE_GENERATION_STATUS = {
  PENDING: "pending",
  IN_FLIGHT: "in_flight",
  DONE: "done",
  FAILED: "failed",
} as const;

export type SlideGenerationStatus =
  (typeof SLIDE_GENERATION_STATUS)[keyof typeof SLIDE_GENERATION_STATUS];

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
