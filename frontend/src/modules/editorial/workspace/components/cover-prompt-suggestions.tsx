"use client";

import { useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import {
  COVER_IDEA_SOURCES,
  COVER_IDEA_TOPIC_MIN,
} from "@/constants/cover-prompt-ideas";
import { useCoverPromptIdeas } from "@/modules/editorial/workspace/hooks/use-cover-prompt-ideas";
import { buildCatalogueIdeas } from "@/modules/editorial/workspace/lib/cover-prompt-catalogue";
import type { CoverIdeasPalette } from "@/schemas/cover-prompt-ideas";
import { CoverPromptIdeas } from "./cover-prompt-ideas";
import type { CoverAiIdeas, CoverPromptSuggestionsProps } from "./types";

const LOCALE_EN = "en";
const LOCALE_PT = "pt";

/** One string per topic/palette pair: AI ideas only show for the pair they answer. */
function contextKey(topic: string, palette: CoverIdeasPalette | null): string {
  return JSON.stringify([topic, palette]);
}

/**
 * Prompt suggestions for a new cover image: the curated catalogue first
 * (six varied scenes, stable per ``seed`` and reshuffled by "Outras ideias"
 * without an AI call), then AI ideas on "Mais ideias". AI
 * ideas stay on screen while more load and give way to the catalogue when the
 * topic or palette changes. Tapping one hands it to ``onPick``. Only the topic
 * and the palette are sent; nothing is saved. Used by the create wizard's
 * slide-1 photo prompt and the publish step's cover generation.
 */
export function CoverPromptSuggestions({
  topic,
  palette,
  seed,
  onPick,
}: Readonly<CoverPromptSuggestionsProps>): React.ReactElement {
  const t = useTranslations("create.coverIdeas");
  const locale = useLocale() === LOCALE_EN ? LOCALE_EN : LOCALE_PT;
  const more = useCoverPromptIdeas();
  const [ai, setAi] = useState<CoverAiIdeas | null>(null);
  const [round, setRound] = useState(0);
  const trimmedTopic = topic.trim();
  const context = contextKey(trimmedTopic, palette);
  const catalogue = useMemo(
    () =>
      buildCatalogueIdeas(t, {
        topic,
        palette,
        seed: seed ?? topic.trim(),
        round,
      }),
    [t, topic, palette, seed, round],
  );
  const aiIdeas = ai?.context === context ? ai.ideas : [];
  const showAi = aiIdeas.length > 0;
  const askedHere =
    more.variables !== undefined &&
    contextKey(more.variables.topic.trim(), more.variables.palette) === context;
  const askMore = (): void =>
    more.mutate(
      { topic: trimmedTopic, palette, locale },
      { onSuccess: (data) => setAi({ context, ideas: data.ideas }) },
    );

  return (
    <CoverPromptIdeas
      ideas={showAi ? aiIdeas : catalogue}
      source={showAi ? COVER_IDEA_SOURCES.AI : COVER_IDEA_SOURCES.CATALOGUE}
      onPick={onPick}
      onMore={askMore}
      onShuffle={() => {
        setAi(null);
        setRound((current) => current + 1);
      }}
      canAskMore={trimmedTopic.length >= COVER_IDEA_TOPIC_MIN}
      loadingMore={more.isPending}
      moreFailed={more.isError && askedHere}
    />
  );
}
