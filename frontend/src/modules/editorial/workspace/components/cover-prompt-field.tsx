"use client";

import { useTranslations } from "next-intl";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import { COVER_PROMPT_MAX_LENGTH } from "@/constants/cover-prompt-ideas";
import { CoverPromptCopy } from "./cover-prompt-copy";
import { CoverPromptSuggestions } from "./cover-prompt-suggestions";
import type { CoverPromptFieldProps } from "./types";

/**
 * The prompt for a new cover photo, editable, with ``CoverPromptSuggestions``
 * under it (the curated catalogue, then AI ideas on "Mais ideias"). Only the
 * topic and the palette are sent; nothing is saved.
 */
export function CoverPromptField({
  id,
  topic,
  palette,
  value,
  onChange,
}: Readonly<CoverPromptFieldProps>): React.ReactElement {
  const t = useTranslations("create.coverIdeas");
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
      <CoverPromptSuggestions
        topic={topic}
        palette={palette}
        onPick={onChange}
      />
    </div>
  );
}
