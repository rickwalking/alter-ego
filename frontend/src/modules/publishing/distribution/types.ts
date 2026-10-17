import type { CarouselProjectResponse } from "@/schemas/carousel";

export interface RegenerateStrategySectionProps {
  project: CarouselProjectResponse;
  projectId: string;
}

export type ViewerLanguage = "pt" | "en";

/** Inputs for the publish viewer's slide list (AE-0416). */
export interface ViewerSlideSource {
  project: CarouselProjectResponse;
  language: ViewerLanguage;
  /** 1-based numbers of the project's real slides (workflow state). */
  slideNumbers?: readonly number[];
}
