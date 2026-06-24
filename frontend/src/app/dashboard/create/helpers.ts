import { DEFAULT_IMAGE_PRESET, IMAGE_PRESETS } from "@/constants/create";
import type { CarouselCreateRequest } from "@/schemas/carousel";
import type { CreateCarouselFormState } from "@/app/dashboard/create/types";
import { CREATE_TEMPLATES } from "@/constants/create";
import { AUTO_THEME_VALUE } from "@/app/dashboard/create/theme-options";

function presetFromValue(value: string): { model: string; style: string } {
  const preset = IMAGE_PRESETS.find((p) => p.value === value);
  if (preset) {
    return { model: preset.model, style: preset.style };
  }
  const fallback = IMAGE_PRESETS[0];
  return { model: fallback.model, style: fallback.style };
}

const _TEMPLATE_STRATEGY_FALLBACK = "hero_content";

export function buildCarouselCreateRequest(
  form: CreateCarouselFormState,
): CarouselCreateRequest {
  const presetValue = form.imagePreset || DEFAULT_IMAGE_PRESET;
  const { model, style } = presetFromValue(presetValue);
  const template = CREATE_TEMPLATES[form.selectedTemplate];
  const strategy = template?.strategy ?? _TEMPLATE_STRATEGY_FALLBACK;

  return {
    topic: form.topic.trim(),
    audience: form.audience.trim(),
    niche: form.niche.trim() || form.topic.trim(),
    theme: form.theme || AUTO_THEME_VALUE,
    image_model: model as CarouselCreateRequest["image_model"],
    image_style: style as CarouselCreateRequest["image_style"],
    strategy,
  };
}
