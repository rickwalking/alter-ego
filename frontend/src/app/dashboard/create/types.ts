import type { CarouselCreateRequest } from "@/schemas/carousel";

export interface CreateCarouselFormState {
  topic: string;
  audience: string;
  niche: string;
  theme: CarouselCreateRequest["theme"];
  imagePreset: string;
  selectedTemplate: number;
}

export const INITIAL_CREATE_FORM_STATE: CreateCarouselFormState = {
  topic: "",
  audience: "",
  niche: "",
  theme: "auto",
  imagePreset: "gemini__comic_neon",
  selectedTemplate: 0,
};
