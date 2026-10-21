"use client";

import { useTranslations } from "next-intl";
import type { CreateCarouselFormState } from "@/app/dashboard/create/types";
import { SectionNumber } from "./section-number";
import { sectionCardStyle, sectionHeaderStyle } from "./section-styles";
import { LabeledField } from "./labeled-field";
import { NICHE_MAX_LENGTH } from "@/app/dashboard/create/helpers";

const IMAGE_GUIDANCE_MAX_LENGTH = 500;
const TOPIC_MAX_LENGTH = 500;
const AUDIENCE_MAX_LENGTH = 500;

export interface CreateTopicSectionProps {
  form: CreateCarouselFormState;
  onChange: (patch: Partial<CreateCarouselFormState>) => void;
}

export function CreateTopicSection({
  form,
  onChange,
}: Readonly<CreateTopicSectionProps>): React.ReactElement {
  const t = useTranslations("create.form");
  return (
    <div style={sectionCardStyle}>
      <div style={sectionHeaderStyle}>
        <SectionNumber num={1} />
        {t("sectionTopic")}
      </div>
      <LabeledField
        label={t("topicLabel")}
        hint={t("maxChars", { max: TOPIC_MAX_LENGTH })}
        value={form.topic}
        onChange={(topic) => onChange({ topic })}
        placeholder={t("topicPlaceholder")}
        maxLength={TOPIC_MAX_LENGTH}
        marginBottom="14px"
      />
      <LabeledField
        label={t("audienceLabel")}
        hint={t("maxChars", { max: AUDIENCE_MAX_LENGTH })}
        value={form.audience}
        onChange={(audience) => onChange({ audience })}
        placeholder={t("audiencePlaceholder")}
        maxLength={AUDIENCE_MAX_LENGTH}
        marginBottom="14px"
      />
      <LabeledField
        label={t("briefLabel")}
        hint={t("briefHint", { max: NICHE_MAX_LENGTH })}
        value={form.niche}
        onChange={(niche) => onChange({ niche })}
        placeholder={t("briefPlaceholder")}
        maxLength={NICHE_MAX_LENGTH}
        multiline
        rows={4}
        marginBottom="14px"
      />
      <LabeledField
        label={t("imageGuidanceLabel")}
        hint={t("imageGuidanceHint")}
        value={form.customVisualDetails}
        onChange={(customVisualDetails) => onChange({ customVisualDetails })}
        placeholder={t("imageGuidancePlaceholder")}
        maxLength={IMAGE_GUIDANCE_MAX_LENGTH}
        multiline
        rows={3}
      />
    </div>
  );
}
