import type { CREATE_TEMPLATES } from "@/constants/create";
import type { CarouselProjectResponse } from "@/schemas/carousel";

export interface RegenerateStrategySectionProps {
  project: CarouselProjectResponse;
  projectId: string;
}

export type ViewerLanguage = "pt" | "en";

/** Inputs for the publish viewer's slide list. */
export interface ViewerSlideSource {
  project: CarouselProjectResponse;
  language: ViewerLanguage;
  /** 1-based numbers of the project's real slides (workflow state). */
  slideNumbers?: readonly number[];
}

/** One layout template card of the regenerate section (AE-0446). */
export interface StrategyTemplateCardProps {
  template: (typeof CREATE_TEMPLATES)[number];
  active: boolean;
  onSelect: () => void;
}
