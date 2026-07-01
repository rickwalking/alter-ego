import type { CarouselCreateRequest } from "@/schemas/carousel";

export interface CreateCarouselFormState {
  topic: string;
  audience: string;
  niche: string;
  theme: CarouselCreateRequest["theme"];
  imagePreset: string;
  selectedTemplate: number;
  /** AE-0298: optional image-guidance text (scene/backdrop, max 500 chars). */
  customVisualDetails: string;
}

export const INITIAL_CREATE_FORM_STATE: CreateCarouselFormState = {
  topic: "",
  audience: "",
  niche: "",
  theme: "auto",
  imagePreset: "openai__neo_anime",
  selectedTemplate: 0,
  customVisualDetails: "",
};
