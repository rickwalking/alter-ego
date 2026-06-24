"use client";

import {
  BG_CARD,
  NEON_CYAN,
  NEON_CYAN_DIM,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";
import { CREATE_TEMPLATES } from "@/app/dashboard/create/constants";
import type { CreateCarouselFormState } from "@/app/dashboard/create/types";
import { SectionNumber } from "./section-number";
import { sectionCardStyle, sectionHeaderStyle } from "./section-styles";

const CYAN = NEON_CYAN;
const CYAN_DIM = NEON_CYAN_DIM;

export interface CreateTemplateSectionProps {
  form: CreateCarouselFormState;
  onChange: (patch: Partial<CreateCarouselFormState>) => void;
}

export function CreateTemplateSection({
  form,
  onChange,
}: CreateTemplateSectionProps): React.ReactElement {
  return (
    <div style={sectionCardStyle}>
      <div style={sectionHeaderStyle}>
        <SectionNumber num={2} />
        Template Style
      </div>
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 md:grid-cols-3">
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
            <div style={{ fontSize: "20px", marginBottom: "4px" }}>
              {tpl.icon}
            </div>
            <h4
              style={{
                fontSize: "12px",
                fontWeight: 600,
                color: TEXT,
                margin: 0,
              }}
            >
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
