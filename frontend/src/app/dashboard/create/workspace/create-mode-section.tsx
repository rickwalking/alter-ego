"use client";

import { useTranslations } from "next-intl";
import {
  CONTENT_MODES,
  DEFAULT_IMAGE_PRESET,
  POV_EDITORIAL_PRESET,
  RUBRIC_POLICY_ONLY,
  type ContentMode,
} from "@/constants/create";
import {
  BG_CARD,
  NEON_CYAN,
  NEON_CYAN_DIM,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";
import {
  isPovMode,
  type CreateCarouselFormState,
} from "@/app/dashboard/create/types";
import { LabeledSelect } from "./labeled-select";
import { sectionCardStyle, sectionHeaderStyle } from "./section-styles";

export interface PersonaOption {
  id: string;
  name: string;
}

/** A quality rubric the wizard offers (applicable to carousels). */
export interface RubricOption {
  id: string;
  name: string;
  isDefault: boolean;
}

export interface CreateModeSectionProps {
  form: CreateCarouselFormState;
  onChange: (patch: Partial<CreateCarouselFormState>) => void;
  personas: readonly PersonaOption[];
  rubrics: readonly RubricOption[];
}

/** POV decks switch to the "Foto + Editorial" preset, Radar IA back. */
function modePatch(mode: ContentMode): Partial<CreateCarouselFormState> {
  const imagePreset = isPovMode(mode)
    ? POV_EDITORIAL_PRESET
    : DEFAULT_IMAGE_PRESET;
  return { contentMode: mode, selectedTemplate: 0, imagePreset };
}

const MODE_KEYS: Record<ContentMode, string> = {
  [CONTENT_MODES.NEWS_ANALYSIS]: "radar",
  [CONTENT_MODES.POV]: "pov",
  [CONTENT_MODES.POV_NEWS]: "povNews",
};

/**
 * Modo (Radar IA / Ponto de Vista) drives the rest of the wizard;
 * the persona and the quality rubric apply to both modes.
 */
export function CreateModeSection({
  form,
  onChange,
  personas,
  rubrics,
}: Readonly<CreateModeSectionProps>): React.ReactElement {
  const t = useTranslations("create.mode");
  const personaOptions = [
    { value: "", label: t("personaNone") },
    ...personas.map((p) => ({ value: p.id, label: p.name })),
  ];
  const rubricOptions = [
    ...rubrics.map((r) => ({
      value: r.id,
      label: r.isDefault ? t("rubricDefault", { name: r.name }) : r.name,
    })),
    { value: RUBRIC_POLICY_ONLY, label: t("rubricNone") },
  ];
  return (
    <div style={sectionCardStyle}>
      <div style={sectionHeaderStyle}>{t("title")}</div>
      <div
        role="radiogroup"
        aria-label={t("title")}
        className="mb-3.5 grid grid-cols-1 gap-2.5 sm:grid-cols-2"
      >
        {Object.values(CONTENT_MODES).map((mode) => {
          const selected = form.contentMode === mode;
          return (
            <button
              key={mode}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(modePatch(mode))}
              style={{
                background: selected ? NEON_CYAN_DIM : BG_CARD,
                border: selected
                  ? `1px solid ${NEON_CYAN}`
                  : "1px solid rgba(255,255,255,0.06)",
                borderRadius: "8px",
                padding: "14px",
                textAlign: "left",
                cursor: "pointer",
              }}
            >
              <span style={{ fontSize: "13px", fontWeight: 600, color: TEXT }}>
                {t(`${MODE_KEYS[mode]}.name`)}
              </span>
              <span
                style={{
                  display: "block",
                  fontSize: "11px",
                  color: TEXT_DIM,
                  marginTop: "4px",
                }}
              >
                {t(`${MODE_KEYS[mode]}.desc`)}
              </span>
            </button>
          );
        })}
      </div>
      <LabeledSelect
        label={t("personaLabel")}
        value={form.personaId}
        options={personaOptions}
        onChange={(personaId) => onChange({ personaId })}
      />
      <LabeledSelect
        label={t("rubricLabel")}
        value={form.rubricId || RUBRIC_POLICY_ONLY}
        options={rubricOptions}
        onChange={(rubricId) => onChange({ rubricId })}
      />
    </div>
  );
}
