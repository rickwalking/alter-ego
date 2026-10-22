"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import { useGeneratePalettes } from "@/modules/palette";
import type { PaletteCandidate } from "@/schemas/palette";
import { PaletteSwatch } from "./palette-swatch";

/** Shortest description the API accepts (mirrors the backend limit). */
const DESCRIPTION_MIN = 3;
/** Longest description the API accepts (mirrors the backend limit). */
const DESCRIPTION_MAX = 300;
const DESCRIPTION_ID = "palette-description";

interface PaletteGeneratorProps {
  onUse: (candidate: PaletteCandidate) => void;
}

/** The weakest of the candidate's three AA ratios, shown on its card. */
function weakestContrast(candidate: PaletteCandidate): string {
  const { text, primary, accent } = candidate.contrast;
  return Math.min(text, primary, accent).toFixed(1);
}

/**
 * "Descreva a paleta": one AI call returns up to three AA-checked candidates;
 * "Usar" hands one to the form. Nothing is saved here.
 */
export function PaletteGenerator({
  onUse,
}: Readonly<PaletteGeneratorProps>): React.ReactElement {
  const t = useTranslations("palettes.generator");
  const [description, setDescription] = useState("");
  const generate = useGeneratePalettes();
  const candidates = generate.data?.candidates ?? [];
  const canGenerate = description.trim().length >= DESCRIPTION_MIN;

  const handleGenerate = (): void => {
    if (canGenerate) generate.mutate({ description: description.trim() });
  };

  return (
    <section className="flex flex-col gap-2 rounded-md border border-dashed border-white/10 p-3">
      <label htmlFor={DESCRIPTION_ID} className="text-xs text-text-muted">
        {t("label")}
      </label>
      <NeonTextarea
        id={DESCRIPTION_ID}
        value={description}
        maxLength={DESCRIPTION_MAX}
        rows={2}
        placeholder={t("placeholder")}
        onChange={(e) => setDescription(e.target.value)}
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[11px] text-text-muted">{t("hint")}</span>
        <NeonButton
          variant="secondary"
          size="sm"
          loading={generate.isPending}
          disabled={!canGenerate}
          onClick={handleGenerate}
        >
          {candidates.length > 0 ? t("regenerate") : t("generate")}
        </NeonButton>
      </div>

      {generate.isError && (
        <NeonBadge variant="red" outline>
          <span role="alert">{t("error")}</span>
        </NeonBadge>
      )}

      {candidates.length > 0 && (
        <ul
          aria-label={t("candidates")}
          className="grid grid-cols-1 gap-2 sm:grid-cols-3"
        >
          {candidates.map((candidate) => (
            <li
              key={`${candidate.name}-${candidate.background}`}
              className="flex flex-col gap-2 rounded-md bg-white/5 p-2"
            >
              <PaletteSwatch
                primary={candidate.primary}
                accent={candidate.accent}
                background={candidate.background}
                label={candidate.name}
                height={32}
              />
              <span className="text-sm font-semibold text-text-primary break-words">
                {candidate.name}
              </span>
              <span className="text-[11px] text-text-muted">
                {t("contrast", { ratio: weakestContrast(candidate) })}
              </span>
              <NeonButton
                variant="ghost"
                size="sm"
                aria-label={`${t("use")} ${candidate.name}`}
                onClick={() => onUse(candidate)}
              >
                {t("use")}
              </NeonButton>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
