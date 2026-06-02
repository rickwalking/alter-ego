import {
  CAROUSEL_THEMES,
  DEFAULT_IMAGE_PRESET,
  IMAGE_PRESETS,
} from "@/constants/create";
import type { CarouselCreateRequest } from "@/schemas/carousel";
import type { CreateCarouselFormState } from "@/app/dashboard/create/types";

function presetFromValue(value: string): { model: string; style: string } {
  const preset = IMAGE_PRESETS.find((p) => p.value === value);
  if (preset) {
    return { model: preset.model, style: preset.style };
  }
  const fallback = IMAGE_PRESETS[0];
  return { model: fallback.model, style: fallback.style };
}

export function buildCarouselCreateRequest(
  form: CreateCarouselFormState,
): CarouselCreateRequest {
  const presetValue = form.imagePreset || DEFAULT_IMAGE_PRESET;
  const { model, style } = presetFromValue(presetValue);

  return {
    topic: form.topic.trim(),
    audience: form.audience.trim(),
    niche: form.niche.trim() || form.topic.trim(),
    theme: form.theme || CAROUSEL_THEMES.AUTO,
    image_model: model as CarouselCreateRequest["image_model"],
    image_style: style as CarouselCreateRequest["image_style"],
  };
}
