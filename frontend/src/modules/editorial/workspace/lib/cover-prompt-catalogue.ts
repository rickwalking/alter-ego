import {
  COVER_IDEA_CATALOGUE_IDS,
  COVER_IDEA_TOPIC_MAX,
  TOPIC_ELLIPSIS,
} from "@/constants/cover-prompt-ideas";
import type { CoverIdeasPalette } from "@/schemas/cover-prompt-ideas";

const CATALOGUE_KEY_PREFIX = "catalogue.";

/** The translator of the `create.coverIdeas` namespace. */
export type CoverIdeasTranslator = (
  key: string,
  values?: Record<string, string>,
) => string;

/** What the curated ideas are tailored to. */
export interface CoverIdeaContext {
  topic: string;
  palette: CoverIdeasPalette | null;
}

function shortTopic(topic: string): string {
  const trimmed = topic.trim().replace(/\s+/g, " ");
  if (trimmed.length <= COVER_IDEA_TOPIC_MAX) return trimmed;
  return `${trimmed.slice(0, COVER_IDEA_TOPIC_MAX).trimEnd()}${TOPIC_ELLIPSIS}`;
}

function paletteValues(
  t: CoverIdeasTranslator,
  palette: CoverIdeasPalette | null,
): Record<string, string> {
  if (!palette) {
    return {
      palette: t("fallback.palette"),
      background: t("fallback.background"),
      accent: t("fallback.accent"),
    };
  }
  return {
    palette: palette.name,
    background: palette.background,
    accent: palette.accent,
  };
}

/**
 * The curated catalogue of cover-photo prompts (angle, background, mood), filled
 * with the palette's name and colours and, when there is one, a nod to the topic.
 */
export function buildCatalogueIdeas(
  t: CoverIdeasTranslator,
  { topic, palette }: Readonly<CoverIdeaContext>,
): string[] {
  const values = paletteValues(t, palette);
  const subject = shortTopic(topic);
  const suffix = subject ? t("topicSuffix", { topic: subject }) : "";
  return COVER_IDEA_CATALOGUE_IDS.map(
    (id) => t(CATALOGUE_KEY_PREFIX + id, values) + suffix,
  );
}
