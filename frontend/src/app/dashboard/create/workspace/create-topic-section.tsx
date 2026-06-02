"use client";

import { BG_CARD, TEXT, TEXT_DIM, TEXT_MUTED } from "@/constants/neon";
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
  color: TEXT,
  fontSize: "13px",
  outline: "none",
} as const;

export interface CreateTopicSectionProps {
  form: CreateCarouselFormState;
  onChange: (patch: Partial<CreateCarouselFormState>) => void;
}

export function CreateTopicSection({
  form,
  onChange,
}: CreateTopicSectionProps): React.ReactElement {
  return (
    <div style={sectionCardStyle}>
      <div style={sectionHeaderStyle}>
        <SectionNumber num={1} />
        Topic & Brief
      </div>
      <div style={{ marginBottom: "14px" }}>
        <label
          style={{
            fontSize: "12px",
            color: TEXT_MUTED,
            marginBottom: "6px",
            display: "block",
          }}
        >
          Carousel Topic{" "}
          <span style={{ color: TEXT_DIM, fontSize: "11px" }}>
            (max 500 chars)
          </span>
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
        <label
          style={{
            fontSize: "12px",
            color: TEXT_MUTED,
            marginBottom: "6px",
            display: "block",
          }}
        >
          Target Audience{" "}
          <span style={{ color: TEXT_DIM, fontSize: "11px" }}>
            (max 500 chars)
          </span>
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
        <label
          style={{
            fontSize: "12px",
            color: TEXT_MUTED,
            marginBottom: "6px",
            display: "block",
          }}
        >
          Brief / Niche{" "}
          <span style={{ color: TEXT_DIM, fontSize: "11px" }}>
            (max 200 chars)
          </span>
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
