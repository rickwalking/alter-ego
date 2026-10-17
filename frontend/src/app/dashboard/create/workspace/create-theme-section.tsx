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
  INPUT_FOCUS_CLASS,
  inputStyle,
  sectionCardStyle,
  sectionHeaderStyle,
} from "./section-styles";

const THEME_SELECT_ID = "create-theme-select";
const IMAGE_PRESET_SELECT_ID = "create-image-preset-select";

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
        {t("form.sectionTheme")}
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label
            htmlFor={THEME_SELECT_ID}
            style={{
              fontSize: "12px",
              color: TEXT_MUTED,
              marginBottom: "6px",
              display: "block",
            }}
          >
            {t("form.themeLabel")}
          </label>
          <select
            id={THEME_SELECT_ID}
            value={form.theme}
            onChange={(e) => handleThemeChange(e.target.value)}
            className={INPUT_FOCUS_CLASS}
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
            htmlFor={IMAGE_PRESET_SELECT_ID}
            style={{
              fontSize: "12px",
              color: TEXT_MUTED,
              marginBottom: "6px",
              display: "block",
            }}
          >
            {t("form.imagePresetLabel")}
          </label>
          <select
            id={IMAGE_PRESET_SELECT_ID}
            value={form.imagePreset}
            onChange={(e) => onChange({ imagePreset: e.target.value })}
            className={INPUT_FOCUS_CLASS}
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
