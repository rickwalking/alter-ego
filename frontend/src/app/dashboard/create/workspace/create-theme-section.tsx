"use client";

import { useTranslations } from "next-intl";
import { FLAT_EDITORIAL_PRESET, IMAGE_PRESETS } from "@/constants/create";
import { NEON_CYAN, TEXT_MUTED } from "@/constants/neon";
import type { CreateCarouselFormState } from "@/app/dashboard/create/types";
import {
  findThemeMode,
  type ThemeOption,
} from "@/app/dashboard/create/theme-options";
import { PALETTE_MODES } from "@/schemas/palette";
import { SectionNumber } from "./section-number";
import {
  inputStyle,
  sectionCardStyle,
  sectionHeaderStyle,
} from "./section-styles";

export interface CreateThemeSectionProps {
  form: CreateCarouselFormState;
  onChange: (patch: Partial<CreateCarouselFormState>) => void;
  /** Theme options from the dynamic catalog (roots + active custom + auto). */
  themeOptions: readonly ThemeOption[];
}

export function CreateThemeSection({
  form,
  onChange,
  themeOptions,
}: CreateThemeSectionProps): React.ReactElement {
  const t = useTranslations("create");
  const selectedIsLight =
    findThemeMode(themeOptions, form.theme) === PALETTE_MODES[0];

  // Light palettes only render correctly with the flat_editorial preset, so
  // selecting one nudges the preset toward it to avoid a mismatched dark scene.
  const handleThemeChange = (theme: string): void => {
    const patch: Partial<CreateCarouselFormState> = {
      theme: theme as CreateCarouselFormState["theme"],
    };
    const isLight = findThemeMode(themeOptions, theme) === PALETTE_MODES[0];
    if (isLight && form.imagePreset !== FLAT_EDITORIAL_PRESET) {
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
            {themeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {selectedIsLight && (
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
