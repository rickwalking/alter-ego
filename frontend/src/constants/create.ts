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
  /** "Foto + Editorial" for Ponto de Vista decks. */
  POV_EDITORIAL: "pov_editorial",
} as const;

/**
 * The compound (model, style) presets exposed in the UI. Only combos
 * the backend registers are selectable here — the API rejects anything
 * else with 422, so keeping the frontend list narrow prevents dead ends.
 */
/** The flat editorial preset value (see DEFAULT_ and LIGHT_THEME_IMAGE_PRESET). */
const FLAT_EDITORIAL_PRESET = "openai__flat_editorial";

export const IMAGE_PRESETS = [
  {
    /** Comic neon runs on OpenAI: prod has no Gemini key. */
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
  {
    /** Slide 1 is the owner's photo; only point slides get an illustration. */
    value: "openai__pov_editorial",
    model: IMAGE_MODELS.OPENAI,
    style: IMAGE_STYLES.POV_EDITORIAL,
    labelKey: "imagePresets.openai_pov_editorial",
  },
] as const;

/**
 * Flat editorial is the default in the wizard, the backend and the
 * autopilot, so not every post looks like the same neon AI art. It is also the
 * preset recommended for light themes.
 */
export const DEFAULT_IMAGE_PRESET = FLAT_EDITORIAL_PRESET;

/** The preset a light theme switches to (flat editorial reads best on light). */
export const LIGHT_THEME_IMAGE_PRESET = FLAT_EDITORIAL_PRESET;

/** The preset a Ponto de Vista deck switches to. */
export const POV_EDITORIAL_PRESET = "openai__pov_editorial";

/** Creator photo library roles. */
export const CREATOR_PHOTO_ROLES = {
  HOOK: "hook",
  CTA: "cta",
  POV: "pov",
} as const;

/** Phase 5 per-slide image-generation lifecycle. */
export const SLIDE_GENERATION_STATUS = {
  PENDING: "pending",
  IN_FLIGHT: "in_flight",
  DONE: "done",
  FAILED: "failed",
} as const;

export type SlideGenerationStatus =
  (typeof SLIDE_GENERATION_STATUS)[keyof typeof SLIDE_GENERATION_STATUS];

/** Pipeline phase display order. */
export const PIPELINE_PHASES = [
  "researching",
  "drafting",
  "designing",
  "generating_images",
  "exporting",
  "completed",
] as const;

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

/** Carousel content modes. NULL on the backend = Radar IA. */
export const CONTENT_MODES = {
  NEWS_ANALYSIS: "news_analysis",
  POV: "pov",
  /** News analysis through the owner's point of view. */
  POV_NEWS: "pov_news",
} as const;

export type ContentMode = (typeof CONTENT_MODES)[keyof typeof CONTENT_MODES];

/** "Ponto de Vista" input limits (growth plan 16.3 A). */
export const POV_THESIS_MAX_LENGTH = 280;
export const POV_PROOF_MAX_LENGTH = 500;
export const POV_SLIDE_COUNTS = [8, 9, 10] as const;
export const POV_SLIDE_COUNT_DEFAULT = 9;
/** Slide-1 hook limits (growth plan 16.3 C). */
export const HOOK_MAX_LENGTH = 60;
export const HOOK_MAX_WORDS = 10;

/** CTA goals: one specific action per carousel (growth plan 16.3 F). */
export const CTA_GOALS = ["follow", "send", "comment"] as const;
export type CtaGoal = (typeof CTA_GOALS)[number];
export const DEFAULT_CTA_GOAL: CtaGoal = "follow";

/** Persona preselected in the wizard when it exists (growth plan 16.3 G). */
export const DEFAULT_PERSONA_NAME = "Pedro";

/**
 * POV formats (growth plan 16.3 B). `format` is the backend `pov_format`;
 * `strategy` is the layout preferred for the point slides. Labels live in
 * i18n under `create.pov.formats.<format>`.
 */
export const POV_FORMATS = [
  "opiniao",
  "como_eu_faco",
  "erros_e_mitos",
  "comparacao",
] as const;
export type PovFormat = (typeof POV_FORMATS)[number];

export interface PovTemplate {
  readonly icon: string;
  readonly format: PovFormat;
  readonly strategy: string;
}

export const POV_TEMPLATES: readonly [PovTemplate, ...PovTemplate[]] = [
  { icon: "🔥", format: "opiniao", strategy: "insight_quote" },
  { icon: "🛠️", format: "como_eu_faco", strategy: "numbered_list" },
  { icon: "⚠️", format: "erros_e_mitos", strategy: "hero_content" },
  { icon: "⚖️", format: "comparacao", strategy: "feature_grid" },
] as const;
