"use client";

import { useMemo } from "react";
import { useLocale, useTranslations } from "next-intl";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  COVER_IDEA_SOURCES,
  COVER_IDEA_TOPIC_MIN,
  COVER_PROMPT_MAX_LENGTH,
} from "@/constants/cover-prompt-ideas";
import { useCoverPromptIdeas } from "@/modules/editorial/workspace/hooks/use-cover-prompt-ideas";
import { buildCatalogueIdeas } from "@/modules/editorial/workspace/lib/cover-prompt-catalogue";
import { CoverPromptIdeas } from "./cover-prompt-ideas";
import type { CoverPromptFieldProps } from "./types";

const LOCALE_EN = "en";
const LOCALE_PT = "pt";

/**
 * The prompt for a new cover photo, editable, with suggestions under it: the
 * curated catalogue first (tailored to the topic and palette), then AI ideas on
 * "Mais ideias". Only the topic and the palette are sent; nothing is saved.
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
  const catalogue = useMemo(
    () => buildCatalogueIdeas(t, { topic, palette }),
    [t, topic, palette],
  );
  const aiIdeas = more.data?.ideas ?? [];
  const showAi = aiIdeas.length > 0;
  const trimmedTopic = topic.trim();

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
      <span className="text-[11px] text-text-muted">{t("hint")}</span>
      <CoverPromptIdeas
        ideas={showAi ? aiIdeas : catalogue}
        source={showAi ? COVER_IDEA_SOURCES.AI : COVER_IDEA_SOURCES.CATALOGUE}
        onPick={onChange}
        onMore={() => more.mutate({ topic: trimmedTopic, palette, locale })}
        canAskMore={trimmedTopic.length >= COVER_IDEA_TOPIC_MIN}
        loadingMore={more.isPending}
        moreFailed={more.isError}
      />
    </div>
  );
}
