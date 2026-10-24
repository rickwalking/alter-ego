/** Curated cover-photo prompt ideas shown before any AI call, in display order. */
export const COVER_IDEA_CATALOGUE_IDS = [
  "frontal",
  "threeQuarter",
  "lowAngle",
  "desk",
  "gesture",
  "closeUp",
] as const;

/** Longest prompt the field keeps (the backend caps one AI idea at 400 too). */
export const COVER_PROMPT_MAX_LENGTH = 400;

/** Longest topic quoted inside a catalogue idea before it is cut. */
export const COVER_IDEA_TOPIC_MAX = 80;

/** Shortest topic the "Mais ideias" endpoint accepts (mirrors the backend). */
export const COVER_IDEA_TOPIC_MIN = 3;

/** Longest topic the "Mais ideias" endpoint accepts (mirrors the backend). */
export const COVER_IDEA_TOPIC_API_MAX = 500;

/** Marks a topic cut at {@link COVER_IDEA_TOPIC_MAX}. */
export const TOPIC_ELLIPSIS = "…";

/** Fewest AI ideas one "Mais ideias" answer carries (mirrors the backend). */
export const COVER_IDEA_COUNT_MIN = 3;

/** Most AI ideas one "Mais ideias" answer carries (mirrors the backend). */
export const COVER_IDEA_COUNT_MAX = 6;

/** How long the "Copiado" confirmation stays after a copy, in milliseconds. */
export const COVER_PROMPT_COPIED_MS = 2000;

/** The dashboard locales the ideas endpoint writes in. */
export const COVER_IDEA_LOCALES = ["pt", "en"] as const;

/** Where the ideas on screen came from. */
export const COVER_IDEA_SOURCES = {
  CATALOGUE: "catalogue",
  AI: "ai",
} as const;

export type CoverIdeaSource =
  (typeof COVER_IDEA_SOURCES)[keyof typeof COVER_IDEA_SOURCES];
