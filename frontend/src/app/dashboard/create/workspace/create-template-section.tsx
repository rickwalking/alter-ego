"use client";

import {
  BG_CARD,
  NEON_CYAN,
  NEON_CYAN_DIM,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";
import { useTranslations } from "next-intl";
import { CREATE_TEMPLATES } from "@/app/dashboard/create/constants";
import { POV_TEMPLATES } from "@/constants/create";
import {
  isPovForm,
  type CreateCarouselFormState,
} from "@/app/dashboard/create/types";
import { SectionNumber } from "./section-number";
import {
  INPUT_FOCUS_CLASS,
  sectionCardStyle,
  sectionHeaderStyle,
} from "./section-styles";

const CYAN = NEON_CYAN;
const TEMPLATE_HEADING_ID = "create-template-heading";
const CYAN_DIM = NEON_CYAN_DIM;

export interface CreateTemplateSectionProps {
  form: CreateCarouselFormState;
  onChange: (patch: Partial<CreateCarouselFormState>) => void;
}

interface TemplateCard {
  icon: string;
  name: string;
  desc: string;
}

/**
 * The four POV formats in POV mode, the six Radar IA templates
 * otherwise. Radar names come from `create.templates`.
 */
function useTemplateCards(
  form: CreateCarouselFormState,
): readonly TemplateCard[] {
  const tPov = useTranslations("create.pov.formats");
  const tRadar = useTranslations("create.templates");
  if (!isPovForm(form)) {
    return CREATE_TEMPLATES.map((tpl) => ({
      icon: tpl.icon,
      name: tRadar(`${tpl.strategy}.name`),
      desc: tRadar(`${tpl.strategy}.desc`),
    }));
  }
  return POV_TEMPLATES.map((tpl) => ({
    icon: tpl.icon,
    name: tPov(`${tpl.format}.name`),
    desc: tPov(`${tpl.format}.desc`),
  }));
}

/**
 * The cards are a radio group of real buttons — the selection
 * is exposed as `aria-checked`, and Enter/Space come from the button itself.
 */
export function CreateTemplateSection({
  form,
  onChange,
}: Readonly<CreateTemplateSectionProps>): React.ReactElement {
  const t = useTranslations("create.form");
  const cards = useTemplateCards(form);
  return (
    <div style={sectionCardStyle}>
      <div style={sectionHeaderStyle} id={TEMPLATE_HEADING_ID}>
        <SectionNumber num={2} />
        {t("sectionTemplate")}
      </div>
      <div
        role="radiogroup"
        aria-labelledby={TEMPLATE_HEADING_ID}
        className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 md:grid-cols-3"
      >
        {cards.map((tpl, idx) => {
          const selected = idx === form.selectedTemplate;
          return (
            <button
              key={tpl.name}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange({ selectedTemplate: idx })}
              className={INPUT_FOCUS_CLASS}
              style={{
                background: selected ? CYAN_DIM : BG_CARD,
                border: selected
                  ? `1px solid ${CYAN}`
                  : "1px solid rgba(255,255,255,0.06)",
                borderRadius: "8px",
                padding: "14px",
                cursor: "pointer",
                transition: "all 0.2s",
                textAlign: "center",
                color: "inherit",
                fontFamily: "inherit",
              }}
            >
              <span
                aria-hidden="true"
                style={{
                  display: "block",
                  fontSize: "20px",
                  marginBottom: "4px",
                }}
              >
                {tpl.icon}
              </span>
              <span
                style={{
                  display: "block",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: TEXT,
                }}
              >
                {tpl.name}
              </span>
              <span
                style={{
                  display: "block",
                  fontSize: "10px",
                  color: TEXT_DIM,
                  margin: "4px 0 0",
                }}
              >
                {tpl.desc}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
