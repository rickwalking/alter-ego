import {
  COVER_IDEA_CATALOGUE_SIZE,
  COVER_IDEA_DEFAULT_THEME,
  COVER_IDEA_DIMENSIONS,
  COVER_IDEA_POOL_SIZE,
  COVER_IDEA_PROP_POOL_SIZE,
  COVER_IDEA_THEME_KEYWORDS,
  COVER_PROMPT_MAX_LENGTH,
  type CoverIdeaTheme,
} from "@/constants/cover-prompt-ideas";
import type { CoverIdeasPalette } from "@/schemas/cover-prompt-ideas";
import { colourName } from "./colour-name";

const POOL_KEY_PREFIX = "pools.";
const PROP_KEY_PREFIX = "props.";
const COLOUR_KEY_PREFIX = "colorNames.";
const SEED_SEPARATOR = ":";
const WORD_SPLIT = /[^a-z0-9]+/;
const DIACRITICS = /[\u0300-\u036f]/g;
const FNV_OFFSET = 2166136261;
const FNV_PRIME = 16777619;
const PROP_DIMENSION = "prop";

/** The translator of the `create.coverIdeas` namespace. */
export type CoverIdeasTranslator = (
  key: string,
  values?: Record<string, string>,
) => string;

/** What the curated ideas are tailored to, and which round of them to show. */
export interface CoverIdeaContext {
  topic: string;
  palette: CoverIdeasPalette | null;
  seed: string;
  round: number;
}

function hashSeed(seed: string): number {
  let hash = FNV_OFFSET;
  for (let i = 0; i < seed.length; i += 1) {
    hash = Math.imul(hash ^ seed.charCodeAt(i), FNV_PRIME);
  }
  return hash >>> 0;
}

/** ``size`` distinct indices out of ``0..poolSize-1`` in an order fixed by ``key``. */
function pick(key: string, poolSize: number, size: number): number[] {
  const rank = (index: number): number =>
    hashSeed(`${key}${SEED_SEPARATOR}${index}`);
  return Array.from({ length: poolSize }, (_, i) => i)
    .sort((a, b) => rank(a) - rank(b))
    .slice(0, size);
}

/** The prop pool whose keywords appear in ``topic`` (accents ignored). */
export function topicTheme(topic: string): CoverIdeaTheme {
  const words = new Set(
    topic
      .normalize("NFD")
      .replace(DIACRITICS, "")
      .toLowerCase()
      .split(WORD_SPLIT),
  );
  const themes = Object.entries(COVER_IDEA_THEME_KEYWORDS) as [
    CoverIdeaTheme,
    readonly string[],
  ][];
  const match = themes.find(([, keywords]) =>
    keywords.some((word) => words.has(word)),
  );
  return match ? match[0] : COVER_IDEA_DEFAULT_THEME;
}

function colours(
  t: CoverIdeasTranslator,
  palette: CoverIdeasPalette | null,
): string {
  if (!palette) return t("colorsFallback");
  return t("colors", {
    background: t(COLOUR_KEY_PREFIX + colourName(palette.background)),
    accent: t(COLOUR_KEY_PREFIX + colourName(palette.accent)),
  });
}

/**
 * The curated catalogue of cover-photo prompts: six scenes that differ from
 * each other on every dimension (shot, pose, wardrobe, location, light) and on
 * the theme prop picked from the topic's words. The palette is named in colour
 * words, never hex. The same seed and round always give the same six; a new
 * round ("Outras ideias") gives a new combination without any AI call.
 */
export function buildCatalogueIdeas(
  t: CoverIdeasTranslator,
  { topic, palette, seed, round }: Readonly<CoverIdeaContext>,
): string[] {
  const key = (dimension: string): string =>
    [seed, String(round), dimension].join(SEED_SEPARATOR);
  const picks = COVER_IDEA_DIMENSIONS.map((dimension) => ({
    dimension,
    indices: pick(
      key(dimension),
      COVER_IDEA_POOL_SIZE,
      COVER_IDEA_CATALOGUE_SIZE,
    ),
  }));
  const props = pick(
    key(PROP_DIMENSION),
    COVER_IDEA_PROP_POOL_SIZE,
    COVER_IDEA_CATALOGUE_SIZE,
  );
  const theme = topicTheme(topic);
  const tones = colours(t, palette);
  return props.map((propIndex, slot) => {
    const values: Record<string, string> = {
      colors: tones,
      prop: t(`${PROP_KEY_PREFIX}${theme}.${propIndex}`),
    };
    for (const { dimension, indices } of picks) {
      values[dimension] = t(
        `${POOL_KEY_PREFIX}${dimension}.${indices[slot] ?? slot}`,
      );
    }
    return t("template", values).slice(0, COVER_PROMPT_MAX_LENGTH);
  });
}
