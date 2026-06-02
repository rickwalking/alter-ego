"use client";

import { useTranslations } from "next-intl";
import {
  CAROUSEL_THEMES,
  IMAGE_PRESETS,
  THEME_LABEL_KEYS,
} from "@/constants/create";
import { BG_CARD, TEXT_MUTED } from "@/constants/neon";
import type { CreateCarouselFormState } from "@/app/dashboard/create/types";
import { SectionNumber } from "./section-number";

const sectionCardStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "24px",
};

const sectionHeaderStyle = {
  fontSize: "14px",
  fontWeight: 700,
  marginBottom: "12px",
  display: "flex",
  alignItems: "center",
  gap: "8px",
};

const inputStyle = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: "6px",
  border: "1px solid rgba(255,255,255,0.08)",
  background: "rgba(6,10,18,0.6)",
  color: "rgba(255,255,255,0.88)",
  fontSize: "13px",
  outline: "none",
} as const;

const THEME_OPTIONS = [
  CAROUSEL_THEMES.AUTO,
  CAROUSEL_THEMES.CYBERSECURITY,
  CAROUSEL_THEMES.AI_COMPETITION,
  CAROUSEL_THEMES.DEVELOPER_SKILLS,
  CAROUSEL_THEMES.SOURCE_CODE,
  CAROUSEL_THEMES.SOCIAL_ENGINEERING,
] as const;

export interface CreateThemeSectionProps {
  form: CreateCarouselFormState;
  onChange: (patch: Partial<CreateCarouselFormState>) => void;
}

export function CreateThemeSection({
  form,
  onChange,
}: CreateThemeSectionProps): React.ReactElement {
  const t = useTranslations("create");

  return (
    <div style={sectionCardStyle}>
      <div style={sectionHeaderStyle}>
        <SectionNumber num={3} />
        Theme & Voice
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "12px",
        }}
      >
        <div>
          <label
            style={{
              fontSize: "12px",
              color: TEXT_MUTED,
              marginBottom: "6px",
              display: "block",
            }}
          >
            Theme
          </label>
          <select
            value={form.theme}
            onChange={(e) =>
              onChange({
                theme: e.target.value as CreateCarouselFormState["theme"],
              })
            }
            style={inputStyle}
          >
            {THEME_OPTIONS.map((theme) => (
              <option key={theme} value={theme}>
                {t(THEME_LABEL_KEYS[theme])}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label
            style={{
              fontSize: "12px",
              color: TEXT_MUTED,
              marginBottom: "6px",
              display: "block",
            }}
          >
            Image Preset (model + style)
          </label>
          <select
            value={form.imagePreset}
            onChange={(e) => onChange({ imagePreset: e.target.value })}
            style={inputStyle}
          >
            {IMAGE_PRESETS.map((preset) => (
              <option key={preset.value} value={preset.value}>
                {t(preset.labelKey)}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
