"use client";

import { useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  COVER_IDEA_SOURCES,
  COVER_IDEA_TOPIC_MIN,
  COVER_PROMPT_MAX_LENGTH,
} from "@/constants/cover-prompt-ideas";
import { useCoverPromptIdeas } from "@/modules/editorial/workspace/hooks/use-cover-prompt-ideas";
import { buildCatalogueIdeas } from "@/modules/editorial/workspace/lib/cover-prompt-catalogue";
import type { CoverIdeasPalette } from "@/schemas/cover-prompt-ideas";
import { CoverPromptCopy } from "./cover-prompt-copy";
import { CoverPromptIdeas } from "./cover-prompt-ideas";
import type { CoverAiIdeas, CoverPromptFieldProps } from "./types";

const LOCALE_EN = "en";
const LOCALE_PT = "pt";

/** One string per topic/palette pair: AI ideas only show for the pair they answer. */
function contextKey(topic: string, palette: CoverIdeasPalette | null): string {
  return JSON.stringify([topic, palette]);
}

/**
 * The prompt for a new cover photo, editable, with suggestions under it: the
 * curated catalogue first (tailored to the topic and palette), then AI ideas on
 * "Mais ideias". AI ideas stay on screen while more load and give way to the
 * catalogue when the topic or palette changes. Only the topic and the palette
 * are sent; nothing is saved.
 */
export function CoverPromptField({
  id,
  topic,
  palette,
  value,
  onChange,
}: Readonly<CoverPromptFieldProps>): React.ReactElement {
  const t = useTranslations("create.coverIdeas");
  const locale = useLocale() === LOCALE_EN ? LOCALE_EN : LOCALE_PT;
  const more = useCoverPromptIdeas();
  const [ai, setAi] = useState<CoverAiIdeas | null>(null);
  const trimmedTopic = topic.trim();
  const context = contextKey(trimmedTopic, palette);
  const catalogue = useMemo(
    () => buildCatalogueIdeas(t, { topic, palette }),
    [t, topic, palette],
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
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-xs text-text-muted">
        {t("label")}
      </label>
      <NeonTextarea
        id={id}
        value={value}
        rows={3}
        maxLength={COVER_PROMPT_MAX_LENGTH}
        placeholder={t("placeholder")}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[11px] text-text-muted">{t("hint")}</span>
        <CoverPromptCopy text={value} />
      </div>
      <CoverPromptIdeas
        ideas={showAi ? aiIdeas : catalogue}
        source={showAi ? COVER_IDEA_SOURCES.AI : COVER_IDEA_SOURCES.CATALOGUE}
        onPick={onChange}
        onMore={askMore}
        canAskMore={trimmedTopic.length >= COVER_IDEA_TOPIC_MIN}
        loadingMore={more.isPending}
        moreFailed={more.isError && askedHere}
      />
    </div>
  );
}
