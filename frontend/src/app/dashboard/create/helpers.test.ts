/**
 * Scenarios: tests/features/create-image-guidance.feature.
 */
import { describe, expect, it } from "vitest";
import { carouselCreateRequestSchema } from "@/schemas/carousel";
import { DEFAULT_IMAGE_PRESET } from "@/constants/create";
import {
  NICHE_MAX_LENGTH,
  buildCarouselCreateRequest,
  canSubmitCreateForm,
  fallbackNiche,
} from "./helpers";
import { INITIAL_CREATE_FORM_STATE, showsFormatPicker } from "./types";

const HOOK_PHOTO_ID = "0b7c1d2e-3f4a-4b5c-8d6e-7f8091a2b3c4";

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

/**
 * (tests/features/radar-ia-quick-fixes.feature)
 */
// Scenario: Missing image style falls back to flat editorial
describe("buildCarouselCreateRequest image defaults (AE-0372)", () => {
  it("defaults to the flat editorial preset", () => {
    expect(DEFAULT_IMAGE_PRESET).toBe("openai__flat_editorial");
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

/** Scenarios: tests/features/create-content-mode.feature. */
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
      hookAssetId: HOOK_PHOTO_ID,
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
      hook_asset_id: HOOK_PHOTO_ID,
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
    expect(request.hook_asset_id).toBeUndefined();
    expect(request.strategy).toBe("feature_grid");
    expect(request.persona_id).toBeNull();
  });

  it("requires the thesis and the slide-1 photo to submit in POV mode", () => {
    const pov = { ...BASE_FORM, contentMode: "pov" as const };
    expect(canSubmitCreateForm(pov)).toBe(false);
    expect(canSubmitCreateForm({ ...pov, povThesis: "Tese" })).toBe(false);
    expect(canSubmitCreateForm({ ...pov, hookAssetId: HOOK_PHOTO_ID })).toBe(
      false,
    );
    expect(
      canSubmitCreateForm({
        ...pov,
        povThesis: "Tese",
        hookAssetId: HOOK_PHOTO_ID,
      }),
    ).toBe(true);
    expect(canSubmitCreateForm(BASE_FORM)).toBe(true);
    expect(canSubmitCreateForm({ ...BASE_FORM, audience: " " })).toBe(false);
  });
});

// Scenario: "POV: News" create sends the POV fields (create-content-mode.feature, AE-0406)
describe("buildCarouselCreateRequest pov_news (AE-0406)", () => {
  it("sends the POV fields and needs the thesis and photo", () => {
    const news = {
      ...BASE_FORM,
      contentMode: "pov_news" as const,
      povThesis: "Agentes em paralelo são um gargalo de revisão.",
      hookAssetId: HOOK_PHOTO_ID,
    };
    const request = buildCarouselCreateRequest(news);
    expect(request).toMatchObject({
      content_mode: "pov_news",
      pov_thesis: "Agentes em paralelo são um gargalo de revisão.",
      slide_count: 9,
      hook_asset_id: HOOK_PHOTO_ID,
    });
    expect(request.pov_format).toBeUndefined();
    expect(carouselCreateRequestSchema.safeParse(request).success).toBe(true);
    expect(canSubmitCreateForm(news)).toBe(true);
    expect(canSubmitCreateForm({ ...news, povThesis: "" })).toBe(false);
  });
});

// Scenario: "POV: News" hides the format picker (create-content-mode.feature, AE-0406)
describe("showsFormatPicker (AE-0406)", () => {
  it("hides the POV format picker for POV: News only", () => {
    expect(showsFormatPicker({ ...BASE_FORM, contentMode: "pov_news" })).toBe(
      false,
    );
    expect(showsFormatPicker({ ...BASE_FORM, contentMode: "pov" })).toBe(true);
    expect(showsFormatPicker(BASE_FORM)).toBe(true);
  });
});

// Scenario: A long topic with an empty brief no longer breaks the niche limit
describe("niche fallback (AE-0415)", () => {
  const longTopic = `${"palavra ".repeat(56)}fim`;

  it("cuts a long topic at a word boundary to the niche limit", () => {
    const niche = fallbackNiche(longTopic);
    expect(niche.length).toBeLessThanOrEqual(NICHE_MAX_LENGTH);
    expect(niche.endsWith("palavra")).toBe(true);
    expect(longTopic.startsWith(niche)).toBe(true);
  });

  it("keeps a short topic as is (trimmed)", () => {
    expect(fallbackNiche("  short topic  ")).toBe("short topic");
    const exact = "a".repeat(NICHE_MAX_LENGTH);
    expect(fallbackNiche(exact)).toBe(exact);
  });

  it("hard-cuts a topic with no space inside the limit", () => {
    expect(fallbackNiche("x".repeat(450))).toBe("x".repeat(NICHE_MAX_LENGTH));
  });

  it("cuts on the space right after the limit", () => {
    const topic = `${"b".repeat(NICHE_MAX_LENGTH)} tail`;
    expect(fallbackNiche(topic)).toBe("b".repeat(NICHE_MAX_LENGTH));
  });

  it("builds a request the API schema accepts with an empty brief", () => {
    const request = buildCarouselCreateRequest({
      ...BASE_FORM,
      topic: longTopic,
      niche: "",
    });
    expect(request.niche.length).toBeLessThanOrEqual(NICHE_MAX_LENGTH);
    expect(() => carouselCreateRequestSchema.parse(request)).not.toThrow();
  });

  it("keeps the brief when one is filled", () => {
    expect(
      buildCarouselCreateRequest({ ...BASE_FORM, niche: " My brief " }).niche,
    ).toBe("My brief");
  });
});
