import {
  CONTENT_MODES,
  DEFAULT_CTA_GOAL,
  DEFAULT_IMAGE_PRESET,
  POV_SLIDE_COUNT_DEFAULT,
  type ContentMode,
  type CtaGoal,
} from "@/constants/create";
import type { CarouselCreateRequest } from "@/schemas/carousel";

export interface CreateCarouselFormState {
  topic: string;
  audience: string;
  niche: string;
  theme: CarouselCreateRequest["theme"];
  imagePreset: string;
  /** Index into the Radar IA templates, or the POV templates in POV mode. */
  selectedTemplate: number;
  /** Optional image-guidance text (scene/backdrop, max 500 chars). */
  customVisualDetails: string;
  /** Radar IA (default) or Ponto de Vista. */
  contentMode: ContentMode;
  /** POV: the owner's thesis (required in POV, max 280). */
  povThesis: string;
  /** POV: optional real experience that proves the thesis (max 500). */
  povPersonalProof: string;
  /** POV: 8, 9 or 10 slides. */
  slideCount: number;
  ctaGoal: CtaGoal;
  /** Persona id, or "" for none. */
  personaId: string;
  /** POV slide-1 photo (creator asset id), or "" for none. */
  hookAssetId: string;
}

export const INITIAL_CREATE_FORM_STATE: CreateCarouselFormState = {
  topic: "",
  audience: "",
  niche: "",
  theme: "auto",
  imagePreset: DEFAULT_IMAGE_PRESET,
  selectedTemplate: 0,
  customVisualDetails: "",
  contentMode: CONTENT_MODES.NEWS_ANALYSIS,
  povThesis: "",
  povPersonalProof: "",
  slideCount: POV_SLIDE_COUNT_DEFAULT,
  ctaGoal: DEFAULT_CTA_GOAL,
  personaId: "",
  hookAssetId: "",
};

/** The POV family (thesis, slide-1 photo, 8-10 slides). */
export function isPovMode(mode: ContentMode): boolean {
  return mode === CONTENT_MODES.POV || mode === CONTENT_MODES.POV_NEWS;
}

/** True in a POV-family mode: the wizard shows the POV inputs. */
export function isPovForm(form: CreateCarouselFormState): boolean {
  return isPovMode(form.contentMode);
}

/**
 * "POV: News" uses the news-analysis structure, so
 * the backend ignores the POV format; the wizard hides the format picker.
 */
export function showsFormatPicker(form: CreateCarouselFormState): boolean {
  return form.contentMode !== CONTENT_MODES.POV_NEWS;
}
