import { describe, expect, it } from "vitest";
import { carouselCreateRequestSchema } from "@/schemas/carousel";
import {
  DEFAULT_IMAGE_PRESET,
  FLAT_EDITORIAL_PRESET,
} from "@/constants/create";
import { buildCarouselCreateRequest, canSubmitCreateForm } from "./helpers";
import { INITIAL_CREATE_FORM_STATE } from "./types";

// Scenarios: see tests/features/create-image-guidance.feature

const BASE_FORM = {
  ...INITIAL_CREATE_FORM_STATE,
  topic: "Topic",
  audience: "Audience",
  niche: "Niche",
};

describe("buildCarouselCreateRequest custom_visual_details (AE-0298)", () => {
  it("sends the trimmed guidance when filled", () => {
    const request = buildCarouselCreateRequest({
      ...BASE_FORM,
      customVisualDetails: "  misty harbor at dusk  ",
    });
    expect(request.custom_visual_details).toBe("misty harbor at dusk");
    expect(
      carouselCreateRequestSchema.parse(request).custom_visual_details,
    ).toBe("misty harbor at dusk");
  });

  it("sends null when the field is blank or whitespace", () => {
    expect(
      buildCarouselCreateRequest({ ...BASE_FORM, customVisualDetails: "" })
        .custom_visual_details,
    ).toBeNull();
    expect(
      buildCarouselCreateRequest({ ...BASE_FORM, customVisualDetails: "   " })
        .custom_visual_details,
    ).toBeNull();
  });

  it("rejects over-length guidance at the schema boundary", () => {
    const result = carouselCreateRequestSchema.safeParse({
      ...buildCarouselCreateRequest(BASE_FORM),
      custom_visual_details: "x".repeat(501),
    });
    expect(result.success).toBe(false);
  });
});

// Scenario: Missing image style falls back to flat editorial
// (tests/features/radar-ia-quick-fixes.feature, AE-0372)
describe("buildCarouselCreateRequest image defaults (AE-0372)", () => {
  it("defaults to the flat editorial preset", () => {
    expect(DEFAULT_IMAGE_PRESET).toBe(FLAT_EDITORIAL_PRESET);
    const request = buildCarouselCreateRequest({
      ...BASE_FORM,
      imagePreset: "",
    });
    expect(request.image_model).toBe("openai");
    expect(request.image_style).toBe("flat_editorial");
  });

  it("falls back to flat editorial for an unknown preset", () => {
    const request = buildCarouselCreateRequest({
      ...BASE_FORM,
      imagePreset: "nope__nope",
    });
    expect(request.image_style).toBe("flat_editorial");
  });

  it("keeps an explicit preset", () => {
    const request = buildCarouselCreateRequest({
      ...BASE_FORM,
      imagePreset: "openai__comic_neon",
    });
    expect(request.image_style).toBe("comic_neon");
  });
});

// Scenarios: tests/features/create-content-mode.feature (AE-0373)
describe("buildCarouselCreateRequest content mode (AE-0373)", () => {
  it("sends the POV fields in POV mode", () => {
    const request = buildCarouselCreateRequest({
      ...BASE_FORM,
      contentMode: "pov",
      povThesis: "  A IA escreve código.  ",
      povPersonalProof: "  ",
      selectedTemplate: 1,
      slideCount: 10,
      ctaGoal: "send",
      personaId: "6f1c2b8e-1d2a-4c3b-9a8e-1f2e3d4c5b6a",
    });
    expect(request).toMatchObject({
      content_mode: "pov",
      pov_thesis: "A IA escreve código.",
      pov_personal_proof: null,
      pov_format: "como_eu_faco",
      slide_count: 10,
      cta_goal: "send",
      strategy: "numbered_list",
      persona_id: "6f1c2b8e-1d2a-4c3b-9a8e-1f2e3d4c5b6a",
    });
    expect(carouselCreateRequestSchema.safeParse(request).success).toBe(true);
  });

  it("drops leftover POV fields in Radar IA mode", () => {
    const request = buildCarouselCreateRequest({
      ...BASE_FORM,
      povThesis: "sobra",
      selectedTemplate: 1,
    });
    expect(request.content_mode).toBe("news_analysis");
    expect(request.pov_thesis).toBeUndefined();
    expect(request.slide_count).toBeUndefined();
    expect(request.strategy).toBe("feature_grid");
    expect(request.persona_id).toBeNull();
  });

  it("requires the thesis to submit in POV mode", () => {
    const pov = { ...BASE_FORM, contentMode: "pov" as const };
    expect(canSubmitCreateForm(pov)).toBe(false);
    expect(canSubmitCreateForm({ ...pov, povThesis: "Tese" })).toBe(true);
    expect(canSubmitCreateForm(BASE_FORM)).toBe(true);
    expect(canSubmitCreateForm({ ...BASE_FORM, audience: " " })).toBe(false);
  });
});
