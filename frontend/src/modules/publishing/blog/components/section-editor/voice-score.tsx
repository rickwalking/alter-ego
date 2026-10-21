"use client";

import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonSelect } from "@/components/atoms/neon-select";
import {
  BLOG_EDITOR_I18N_NAMESPACE,
  BLOG_VOICE_SCORE_MIN,
} from "@/constants/blog-editor";
import { blogQualitySchema } from "@/schemas/blog-document";
import type { VoiceScoreProps } from "./types";

const PERSONA_SELECT_ID = "blog-voice-persona";

/**
 * Voice score of the shown language (`content.quality`, ADR-0003 bar 70)
 * with its breakdown, plus the persona "Rewrite in my voice" uses.
 */
export function VoiceScore({
  quality,
  personas,
  personaId,
  onPersonaChange,
}: Readonly<VoiceScoreProps>): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  const parsed = blogQualitySchema.safeParse(quality);
  const score = parsed.success ? Math.round(parsed.data.voice_score) : null;
  const breakdown = parsed.success
    ? Object.entries(parsed.data.voice_breakdown)
    : [];
  return (
    <div className="space-y-2 rounded border p-3" data-testid="voice-score">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">{t("voice.title")}</span>
        {score === null ? (
          <span className="text-xs text-text-muted">
            {t("voice.notScored")}
          </span>
        ) : (
          <NeonBadge
            variant={score >= BLOG_VOICE_SCORE_MIN ? "default" : "destructive"}
          >
            {t("voice.score", { score })}
          </NeonBadge>
        )}
      </div>
      {breakdown.length > 0 && (
        <ul className="space-y-1 text-xs">
          {breakdown
            .filter(([, value]) => typeof value === "number")
            .map(([key, value]) => (
              <li key={key} className="flex justify-between">
                <span>{key}</span>
                <span>{String(value)}</span>
              </li>
            ))}
        </ul>
      )}
      <label
        htmlFor={PERSONA_SELECT_ID}
        className="block text-xs font-semibold text-text-muted"
      >
        {t("voice.persona")}
      </label>
      <NeonSelect
        id={PERSONA_SELECT_ID}
        value={personaId ?? ""}
        onChange={(e) => onPersonaChange(e.target.value || null)}
      >
        {personas.length === 0 && (
          <option value="">{t("voice.noPersona")}</option>
        )}
        {personas.map((persona) => (
          <option key={persona.id} value={persona.id}>
            {persona.name}
          </option>
        ))}
      </NeonSelect>
    </div>
  );
}
