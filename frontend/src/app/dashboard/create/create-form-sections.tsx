"use client";

import { useTranslations } from "next-intl";
import {
  CAROUSEL_THEMES,
  IMAGE_PRESETS,
  THEME_LABEL_KEYS,
} from "@/constants/create";
import {
  BG_CARD,
  NEON_CYAN,
  NEON_CYAN_DIM,
  TEXT,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
import { CREATE_TEMPLATES } from "@/app/dashboard/create/constants";
import type { CreateCarouselFormState } from "@/app/dashboard/create/types";

const CYAN = NEON_CYAN;
const CYAN_DIM = NEON_CYAN_DIM;

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
  color: TEXT,
  fontSize: "13px",
  outline: "none",
} as const;

function SectionNumber({ num }: { num: number }): React.ReactElement {
  return (
    <span
      style={{
        width: "22px",
        height: "22px",
        borderRadius: "50%",
        background: CYAN_DIM,
        color: CYAN,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontSize: "11px",
        fontWeight: 700,
      }}
    >
      {num}
    </span>
  );
}

export interface CreateFormSectionProps {
  form: CreateCarouselFormState;
  onChange: (patch: Partial<CreateCarouselFormState>) => void;
}

export function CreateTopicSection({
  form,
  onChange,
}: CreateFormSectionProps): React.ReactElement {
  return (
    <div style={sectionCardStyle}>
      <div style={sectionHeaderStyle}>
        <SectionNumber num={1} />
        Topic & Brief
      </div>
      <div style={{ marginBottom: "14px" }}>
        <label style={{ fontSize: "12px", color: TEXT_MUTED, marginBottom: "6px", display: "block" }}>
          Carousel Topic{" "}
          <span style={{ color: TEXT_DIM, fontSize: "11px" }}>(max 500 chars)</span>
        </label>
        <input
          type="text"
          value={form.topic}
          onChange={(e) => onChange({ topic: e.target.value })}
          style={inputStyle}
          placeholder="e.g., DeepSeek V4: Open-Source LLM Benchmark Performance"
          maxLength={500}
        />
      </div>
      <div style={{ marginBottom: "14px" }}>
        <label style={{ fontSize: "12px", color: TEXT_MUTED, marginBottom: "6px", display: "block" }}>
          Target Audience{" "}
          <span style={{ color: TEXT_DIM, fontSize: "11px" }}>(max 500 chars)</span>
        </label>
        <input
          type="text"
          value={form.audience}
          onChange={(e) => onChange({ audience: e.target.value })}
          style={inputStyle}
          placeholder="Who should read this carousel?"
          maxLength={500}
        />
      </div>
      <div>
        <label style={{ fontSize: "12px", color: TEXT_MUTED, marginBottom: "6px", display: "block" }}>
          Brief / Niche{" "}
          <span style={{ color: TEXT_DIM, fontSize: "11px" }}>(max 200 chars)</span>
        </label>
        <textarea
          value={form.niche}
          onChange={(e) => onChange({ niche: e.target.value })}
          rows={4}
          style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
          placeholder="What should this carousel cover?"
          maxLength={200}
        />
      </div>
    </div>
  );
}

export function CreateTemplateSection({
  form,
  onChange,
}: CreateFormSectionProps): React.ReactElement {
  return (
    <div style={sectionCardStyle}>
      <div style={sectionHeaderStyle}>
        <SectionNumber num={2} />
        Template Style
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "10px",
        }}
      >
        {CREATE_TEMPLATES.map((tpl, idx) => (
          <div
            key={tpl.name}
            role="button"
            tabIndex={0}
            onClick={() => onChange({ selectedTemplate: idx })}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                onChange({ selectedTemplate: idx });
              }
            }}
            style={{
              background: idx === form.selectedTemplate ? CYAN_DIM : BG_CARD,
              border:
                idx === form.selectedTemplate
                  ? `1px solid ${CYAN}`
                  : "1px solid rgba(255,255,255,0.06)",
              borderRadius: "8px",
              padding: "14px",
              cursor: "pointer",
              transition: "all 0.2s",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: "20px", marginBottom: "4px" }}>{tpl.icon}</div>
            <h4 style={{ fontSize: "12px", fontWeight: 600, color: TEXT, margin: 0 }}>
              {tpl.name}
            </h4>
            <p style={{ fontSize: "10px", color: TEXT_DIM, margin: "4px 0 0" }}>
              {tpl.desc}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

const THEME_OPTIONS = [
  CAROUSEL_THEMES.AUTO,
  CAROUSEL_THEMES.CYBERSECURITY,
  CAROUSEL_THEMES.AI_COMPETITION,
  CAROUSEL_THEMES.DEVELOPER_SKILLS,
  CAROUSEL_THEMES.SOURCE_CODE,
  CAROUSEL_THEMES.SOCIAL_ENGINEERING,
] as const;

export function CreateThemeSection({
  form,
  onChange,
}: CreateFormSectionProps): React.ReactElement {
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
          <label style={{ fontSize: "12px", color: TEXT_MUTED, marginBottom: "6px", display: "block" }}>
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
          <label style={{ fontSize: "12px", color: TEXT_MUTED, marginBottom: "6px", display: "block" }}>
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
