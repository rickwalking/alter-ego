"use client";

import {
  BG_CARD,
  NEON_CYAN,
  NEON_CYAN_DIM,
  TEXT,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
import { CREATE_TEMPLATES } from "@/app/dashboard/create/constants";

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

export function CreateTopicSection(): React.ReactElement {
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
          defaultValue="DeepSeek V4 Analysis"
          style={{
            width: "100%",
            padding: "10px 12px",
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            background: "rgba(6,10,18,0.6)",
            color: TEXT,
            fontSize: "13px",
            outline: "none",
          }}
          placeholder="e.g., DeepSeek V4: Open-Source LLM Benchmark Performance"
        />
      </div>
      <div style={{ marginBottom: "14px" }}>
        <label style={{ fontSize: "12px", color: TEXT_MUTED, marginBottom: "6px", display: "block" }}>
          Target Audience{" "}
          <span style={{ color: TEXT_DIM, fontSize: "11px" }}>(max 500 chars)</span>
        </label>
        <input
          type="text"
          defaultValue="AI/ML Engineers, Software Developers"
          style={{
            width: "100%",
            padding: "10px 12px",
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            background: "rgba(6,10,18,0.6)",
            color: TEXT,
            fontSize: "13px",
            outline: "none",
          }}
          placeholder="Who should read this carousel?"
        />
      </div>
      <div>
        <label style={{ fontSize: "12px", color: TEXT_MUTED, marginBottom: "6px", display: "block" }}>
          Brief / Description{" "}
          <span style={{ color: TEXT_DIM, fontSize: "11px" }}>(max 200 chars)</span>
        </label>
        <textarea
          defaultValue="Analyze DeepSeek V4's architecture, benchmark performance against open-source LLMs, pricing strategy, and implications for the open-source AI landscape."
          rows={4}
          style={{
            width: "100%",
            padding: "10px 12px",
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            background: "rgba(6,10,18,0.6)",
            color: TEXT,
            fontSize: "13px",
            outline: "none",
            resize: "vertical",
            fontFamily: "inherit",
          }}
          placeholder="What should this carousel cover?"
        />
      </div>
    </div>
  );
}

export interface CreateTemplateSectionProps {
  selectedTemplate: number;
  onSelectTemplate: (index: number) => void;
}

export function CreateTemplateSection({
  selectedTemplate,
  onSelectTemplate,
}: CreateTemplateSectionProps): React.ReactElement {
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
            onClick={() => onSelectTemplate(idx)}
            style={{
              background: idx === selectedTemplate ? CYAN_DIM : BG_CARD,
              border:
                idx === selectedTemplate
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

export function CreateThemeSection(): React.ReactElement {
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
            Theme <span style={{ color: TEXT_DIM, fontSize: "11px" }}>(enum)</span>
          </label>
          <select
            style={{
              width: "100%",
              padding: "10px 12px",
              borderRadius: "6px",
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(6,10,18,0.45)",
              color: TEXT,
              fontSize: "13px",
              outline: "none",
            }}
          >
            <option value="auto">Auto-detect</option>
            <option value="cybersecurity">Cybersecurity</option>
            <option value="ai_competition">AI Competition</option>
            <option value="developer_skills">Developer Skills</option>
            <option value="source_code">Source Code</option>
            <option value="social_engineering">Social Engineering</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: "12px", color: TEXT_MUTED, marginBottom: "6px", display: "block" }}>
            Image Preset{" "}
            <span style={{ color: TEXT_DIM, fontSize: "11px" }}>(model + style)</span>
          </label>
          <select
            style={{
              width: "100%",
              padding: "10px 12px",
              borderRadius: "6px",
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(6,10,18,0.45)",
              color: TEXT,
              fontSize: "13px",
              outline: "none",
            }}
          >
            <option value="default">Default (SDXL + realistic)</option>
            <option value="cyberpunk">Cyberpunk</option>
            <option value="minimal">Minimal</option>
            <option value="tech">Tech</option>
          </select>
        </div>
      </div>
    </div>
  );
}
