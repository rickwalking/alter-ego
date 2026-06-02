export { SectionNumber } from "./workspace/section-number";
export type { SectionNumberProps } from "./workspace/section-number";

export { CreateTopicSection } from "./workspace/create-topic-section";
export type { CreateTopicSectionProps } from "./workspace/create-topic-section";

export { CreateTemplateSection } from "./workspace/create-template-section";
export type { CreateTemplateSectionProps } from "./workspace/create-template-section";

export { CreateThemeSection } from "./workspace/create-theme-section";
export type { CreateThemeSectionProps } from "./workspace/create-theme-section";

export type { CreateCarouselFormState } from "./types";

export interface CreateFormSectionProps {
  form: import("./types").CreateCarouselFormState;
  onChange: (patch: Partial<import("./types").CreateCarouselFormState>) => void;
}
