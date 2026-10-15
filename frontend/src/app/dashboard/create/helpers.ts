import {
  CREATE_TEMPLATES,
  DEFAULT_IMAGE_PRESET,
  IMAGE_PRESETS,
  POV_TEMPLATES,
} from "@/constants/create";
import type { CarouselCreateRequest } from "@/schemas/carousel";
import {
  isPovForm,
  type CreateCarouselFormState,
} from "@/app/dashboard/create/types";
import { AUTO_THEME_VALUE } from "@/app/dashboard/create/theme-options";

function presetFromValue(value: string): { model: string; style: string } {
  const preset = IMAGE_PRESETS.find((p) => p.value === value);
  if (preset) {
    return { model: preset.model, style: preset.style };
  }
  // AE-0372: an unknown value falls back to the default (flat editorial),
  // not to whichever preset happens to be listed first.
  const fallback =
    IMAGE_PRESETS.find((p) => p.value === DEFAULT_IMAGE_PRESET) ??
    IMAGE_PRESETS[0];
  return { model: fallback.model, style: fallback.style };
}

const _TEMPLATE_STRATEGY_FALLBACK = "hero_content";

type ContentModeRequest = Pick<
  CarouselCreateRequest,
  | "content_mode"
  | "pov_thesis"
  | "pov_personal_proof"
  | "pov_format"
  | "slide_count"
  | "cta_goal"
  | "hook_asset_id"
>;

/** AE-0373: POV fields only in POV mode (the API rejects them on Radar IA). */
function contentModeFields(form: CreateCarouselFormState): ContentModeRequest {
  if (!isPovForm(form)) {
    return { content_mode: form.contentMode, cta_goal: form.ctaGoal };
  }
  const template = POV_TEMPLATES[form.selectedTemplate] ?? POV_TEMPLATES[0];
  return {
    content_mode: form.contentMode,
    pov_thesis: form.povThesis.trim(),
    pov_personal_proof: form.povPersonalProof.trim() || null,
    pov_format: template.format,
    slide_count: form.slideCount,
    cta_goal: form.ctaGoal,
    // PR #106 review: the slide-1 photo is required for POV.
    hook_asset_id: form.hookAssetId,
  };
}

function templateStrategy(form: CreateCarouselFormState): string {
  const templates = isPovForm(form) ? POV_TEMPLATES : CREATE_TEMPLATES;
  return (
    templates[form.selectedTemplate]?.strategy ?? _TEMPLATE_STRATEGY_FALLBACK
  );
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
    theme: form.theme || AUTO_THEME_VALUE,
    image_model: model as CarouselCreateRequest["image_model"],
    image_style: style as CarouselCreateRequest["image_style"],
    strategy: templateStrategy(form),
    custom_visual_details: form.customVisualDetails.trim() || null,
    persona_id: form.personaId || null,
    ...contentModeFields(form),
  };
}

/** AE-0373: the wizard can submit (POV needs a thesis and the slide-1 photo). */
export function canSubmitCreateForm(form: CreateCarouselFormState): boolean {
  if (!form.topic.trim() || !form.audience.trim()) {
    return false;
  }
  if (!isPovForm(form)) {
    return true;
  }
  return form.povThesis.trim().length > 0 && form.hookAssetId.length > 0;
}
