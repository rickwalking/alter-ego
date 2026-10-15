import { describe, expect, it } from "vitest";
import { carouselCreateRequestSchema } from "@/schemas/carousel";
import {
  DEFAULT_IMAGE_PRESET,
  FLAT_EDITORIAL_PRESET,
} from "@/constants/create";
import { buildCarouselCreateRequest } from "./helpers";
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
