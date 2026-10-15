"use client";

import { useTranslations } from "next-intl";
import {
  CTA_GOALS,
  POV_PROOF_MAX_LENGTH,
  POV_SLIDE_COUNTS,
  POV_THESIS_MAX_LENGTH,
  type CtaGoal,
} from "@/constants/create";
import { NEON_AMBER } from "@/constants/neon";
import type { CreateCarouselFormState } from "@/app/dashboard/create/types";
import { LabeledField } from "./labeled-field";
import { LabeledSelect } from "./labeled-select";
import { sectionCardStyle, sectionHeaderStyle } from "./section-styles";

export interface CreatePovSectionProps {
  form: CreateCarouselFormState;
  onChange: (patch: Partial<CreateCarouselFormState>) => void;
}

/**
 * AE-0373: the "Ponto de Vista" inputs. The thesis is the owner's actual
 * opinion: the model may sharpen it but never invent it.
 */
export function CreatePovSection({
  form,
  onChange,
}: CreatePovSectionProps): React.ReactElement {
  const t = useTranslations("create.pov");
  const thesisMissing = form.povThesis.trim().length === 0;
  return (
    <div style={sectionCardStyle}>
      <div style={sectionHeaderStyle}>{t("title")}</div>
      <LabeledField
        label={t("thesisLabel")}
        hint={t("thesisHint")}
        value={form.povThesis}
        onChange={(povThesis) => onChange({ povThesis })}
        placeholder={t("thesisPlaceholder")}
        maxLength={POV_THESIS_MAX_LENGTH}
        multiline
        rows={3}
        marginBottom="6px"
      />
      {thesisMissing && (
        <p
          role="note"
          style={{ fontSize: "11px", color: NEON_AMBER, marginBottom: "14px" }}
        >
          {t("thesisRequired")}
        </p>
      )}
      <LabeledField
        label={t("proofLabel")}
        hint={t("proofHint")}
        value={form.povPersonalProof}
        onChange={(povPersonalProof) => onChange({ povPersonalProof })}
        placeholder={t("proofPlaceholder")}
        maxLength={POV_PROOF_MAX_LENGTH}
        multiline
        rows={3}
        marginBottom="14px"
      />
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
        <LabeledSelect
          label={t("slideCountLabel")}
          value={String(form.slideCount)}
          options={POV_SLIDE_COUNTS.map((count) => ({
            value: String(count),
            label: t("slideCountOption", { count }),
          }))}
          onChange={(value) => onChange({ slideCount: Number(value) })}
        />
        <LabeledSelect
          label={t("ctaGoalLabel")}
          value={form.ctaGoal}
          options={CTA_GOALS.map((goal) => ({
            value: goal,
            label: t(`ctaGoals.${goal}`),
          }))}
          onChange={(value) => onChange({ ctaGoal: value as CtaGoal })}
        />
      </div>
    </div>
  );
}
