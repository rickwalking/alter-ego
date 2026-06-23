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

/**
 * Available carousel themes. Dark variants pair with the neon/neo-anime image
 * styles; light/editorial themes (risograph, paper_editorial, clinical_mint)
 * pair with the flat_editorial style.
 */
export const CAROUSEL_THEMES = {
  CYBERSECURITY: "cybersecurity",
  AI_COMPETITION: "ai_competition",
  DEVELOPER_SKILLS: "developer_skills",
  SOURCE_CODE: "source_code",
  SOCIAL_ENGINEERING: "social_engineering",
  PLASMA_MAGENTA: "plasma_magenta",
  ACID_LIME: "acid_lime",
  MONO_INDIGO: "mono_indigo",
  EMBER_CRIMSON: "ember_crimson",
  BLUEPRINT: "blueprint",
  RISOGRAPH: "risograph",
  PAPER_EDITORIAL: "paper_editorial",
  CLINICAL_MINT: "clinical_mint",
  AUTO: "auto",
} as const;

/** Theme display labels for i18n keys (relative to "create" namespace). */
export const THEME_LABEL_KEYS = {
  cybersecurity: "themes.cybersecurity",
  ai_competition: "themes.ai_competition",
  developer_skills: "themes.developer_skills",
  source_code: "themes.source_code",
  social_engineering: "themes.social_engineering",
  plasma_magenta: "themes.plasma_magenta",
  acid_lime: "themes.acid_lime",
  mono_indigo: "themes.mono_indigo",
  ember_crimson: "themes.ember_crimson",
  blueprint: "themes.blueprint",
  risograph: "themes.risograph",
  paper_editorial: "themes.paper_editorial",
  clinical_mint: "themes.clinical_mint",
  auto: "themes.auto",
} as const;

/**
 * Theme keys whose palette uses a LIGHT background. These render correctly
 * only with the flat_editorial preset, so the create form nudges toward it.
 */
export const LIGHT_THEME_KEYS: readonly string[] = [
  CAROUSEL_THEMES.RISOGRAPH,
  CAROUSEL_THEMES.PAPER_EDITORIAL,
  CAROUSEL_THEMES.CLINICAL_MINT,
];

/** True when the theme's palette is light (pair with flat_editorial). */
export function isLightTheme(theme: string): boolean {
  return LIGHT_THEME_KEYS.includes(theme);
}

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
