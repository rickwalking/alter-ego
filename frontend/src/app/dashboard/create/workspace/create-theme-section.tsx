"use client";

import { useTranslations } from "next-intl";
import {
  CAROUSEL_THEMES,
  FLAT_EDITORIAL_PRESET,
  IMAGE_PRESETS,
  isLightTheme,
  THEME_LABEL_KEYS,
} from "@/constants/create";
import { NEON_CYAN, TEXT_MUTED } from "@/constants/neon";
import type { CreateCarouselFormState } from "@/app/dashboard/create/types";
import { SectionNumber } from "./section-number";
import {
  inputStyle,
  sectionCardStyle,
  sectionHeaderStyle,
} from "./section-styles";

const THEME_OPTIONS = [
  CAROUSEL_THEMES.AUTO,
  CAROUSEL_THEMES.CYBERSECURITY,
  CAROUSEL_THEMES.AI_COMPETITION,
  CAROUSEL_THEMES.DEVELOPER_SKILLS,
  CAROUSEL_THEMES.SOURCE_CODE,
  CAROUSEL_THEMES.SOCIAL_ENGINEERING,
  CAROUSEL_THEMES.PLASMA_MAGENTA,
  CAROUSEL_THEMES.ACID_LIME,
  CAROUSEL_THEMES.MONO_INDIGO,
  CAROUSEL_THEMES.EMBER_CRIMSON,
  CAROUSEL_THEMES.BLUEPRINT,
  CAROUSEL_THEMES.RISOGRAPH,
  CAROUSEL_THEMES.PAPER_EDITORIAL,
  CAROUSEL_THEMES.CLINICAL_MINT,
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

  // Light palettes only render correctly with the flat_editorial preset, so
  // selecting one nudges the preset toward it to avoid a mismatched dark scene.
  const handleThemeChange = (theme: string): void => {
    const patch: Partial<CreateCarouselFormState> = {
      theme: theme as CreateCarouselFormState["theme"],
    };
    if (isLightTheme(theme) && form.imagePreset !== FLAT_EDITORIAL_PRESET) {
      patch.imagePreset = FLAT_EDITORIAL_PRESET;
    }
    onChange(patch);
  };

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
            onChange={(e) => handleThemeChange(e.target.value)}
            style={inputStyle}
          >
            {THEME_OPTIONS.map((theme) => (
              <option key={theme} value={theme}>
                {t(THEME_LABEL_KEYS[theme])}
              </option>
            ))}
          </select>
          {isLightTheme(form.theme) && (
            <p
              role="note"
              style={{
                fontSize: "11px",
                color: NEON_CYAN,
                marginTop: "6px",
              }}
            >
              {t("lightThemeHint")}
            </p>
          )}
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
