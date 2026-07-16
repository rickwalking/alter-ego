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
  FLAT_EDITORIAL: "flat_editorial",
} as const;

/**
 * The compound (model, style) presets exposed in the UI. Only combos
 * the backend registers are selectable here — the API rejects anything
 * else with 422, so keeping the frontend list narrow prevents dead ends.
 */
export const IMAGE_PRESETS = [
  {
    // AE-0308: comic neon re-routed to OpenAI — prod has no Gemini key.
    value: "openai__comic_neon",
    model: IMAGE_MODELS.OPENAI,
    style: IMAGE_STYLES.COMIC_NEON,
    labelKey: "imagePresets.openai_comic_neon",
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
  {
    value: "openai__flat_editorial",
    model: IMAGE_MODELS.OPENAI,
    style: IMAGE_STYLES.FLAT_EDITORIAL,
    labelKey: "imagePresets.openai_flat_editorial",
  },
] as const;

export const DEFAULT_IMAGE_PRESET = IMAGE_PRESETS[0].value;

/** The light/editorial preset value — recommended for light themes. */
export const FLAT_EDITORIAL_PRESET = "openai__flat_editorial";

/** Phase 5 per-slide image-generation lifecycle. */
export const SLIDE_GENERATION_STATUS = {
  PENDING: "pending",
  IN_FLIGHT: "in_flight",
  DONE: "done",
  FAILED: "failed",
} as const;

export type SlideGenerationStatus =
  (typeof SLIDE_GENERATION_STATUS)[keyof typeof SLIDE_GENERATION_STATUS];

// Theme keys, labels, and the light-theme set are no longer hardcoded here
// (AE-0271). The create-page theme dropdown renders the live union of root +
// custom palettes from `GET /api/palettes`, and each palette's light/dark mode
// drives the flat-editorial nudge. The only FE-only theme value is the `"auto"`
// sentinel — see `AUTO_THEME_VALUE` in `app/dashboard/create/theme-options.ts`.

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

/** Template definition with name, description, icon, and backend strategy name. */
export interface CreateTemplate {
  readonly icon: string;
  readonly name: string;
  readonly desc: string;
  readonly strategy: string;
}

export const CREATE_TEMPLATES: readonly CreateTemplate[] = [
  {
    icon: "📊",
    name: "Analysis",
    desc: "Deep dive with data",
    strategy: "stat_card_grid",
  },
  {
    icon: "⚖️",
    name: "Comparison",
    desc: "Side by side",
    strategy: "feature_grid",
  },
  {
    icon: "📚",
    name: "Tutorial",
    desc: "Step by step",
    strategy: "numbered_list",
  },
  {
    icon: "📰",
    name: "News Flash",
    desc: "Quick update",
    strategy: "intro_hero",
  },
  {
    icon: "🧠",
    name: "Deep Dive",
    desc: "Comprehensive",
    strategy: "insight_quote",
  },
  {
    icon: "🎯",
    name: "Listicle",
    desc: "Top N format",
    strategy: "hero_content",
  },
] as const;

/** Navigation route for create page (neon dashboard). */
export const CREATE_ROUTE = "/dashboard/create";

/** Route pattern for create workspace (neon dashboard). */
export const CREATE_WORKSPACE_ROUTE = (id: string) => `/dashboard/create/${id}`;
