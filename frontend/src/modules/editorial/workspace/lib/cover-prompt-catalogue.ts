import {
  COVER_IDEA_DEFAULT_THEME,
  COVER_IDEA_DIMENSIONS,
  COVER_IDEA_THEME_KEYWORDS,
  COVER_PROMPT_MAX_LENGTH,
  type CoverIdeaTheme,
} from "@/constants/cover-prompt-ideas";
import type { CoverIdeasPalette } from "@/schemas/cover-prompt-ideas";
import { colourName } from "./colour-name";
import { catalogueScenes } from "./cover-prompt-scenes";

const POOL_KEY_PREFIX = "pools.";
const PROP_KEY_PREFIX = "props.";
const COLOUR_KEY_PREFIX = "colorNames.";
const WORD_SPLIT = /[^a-z0-9]+/;
const DIACRITICS = /[\u0300-\u036f]/g;

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
 * the theme prop picked from the topic's words, in combinations that make
 * physical sense. The palette is named in colour words, never hex. The same
 * seed and round always give the same six; a new round ("Outras ideias") gives
 * scenes that share at most one value with any scene of the round before, and
 * mostly new props, without any AI call.
 */
export function buildCatalogueIdeas(
  t: CoverIdeasTranslator,
  { topic, palette, seed, round }: Readonly<CoverIdeaContext>,
): string[] {
  const theme = topicTheme(topic);
  const tones = colours(t, palette);
  return catalogueScenes(seed, theme, round).map((scene) => {
    const values: Record<string, string> = {
      colors: tones,
      prop: t(`${PROP_KEY_PREFIX}${theme}.${scene.prop}`),
    };
    for (const dimension of COVER_IDEA_DIMENSIONS) {
      values[dimension] = t(
        `${POOL_KEY_PREFIX}${dimension}.${scene[dimension]}`,
      );
    }
    return t("template", values).slice(0, COVER_PROMPT_MAX_LENGTH);
  });
}
