"use client";

import type { CreateCarouselFormState } from "@/app/dashboard/create/types";
import { SectionNumber } from "./section-number";
import { sectionCardStyle, sectionHeaderStyle } from "./section-styles";
import { LabeledField } from "./labeled-field";

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
      <LabeledField
        label="Carousel Topic"
        hint="max 500 chars"
        value={form.topic}
        onChange={(topic) => onChange({ topic })}
        placeholder="e.g., DeepSeek V4: Open-Source LLM Benchmark Performance"
        maxLength={500}
        marginBottom="14px"
      />
      <LabeledField
        label="Target Audience"
        hint="max 500 chars"
        value={form.audience}
        onChange={(audience) => onChange({ audience })}
        placeholder="Who should read this carousel?"
        maxLength={500}
        marginBottom="14px"
      />
      <LabeledField
        label="Brief / Niche"
        hint="max 200 chars"
        value={form.niche}
        onChange={(niche) => onChange({ niche })}
        placeholder="What should this carousel cover?"
        maxLength={200}
        multiline
        rows={4}
      />
    </div>
  );
}
