import { describe, expect, it } from "vitest";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import { viewerSlidePaths, viewerSlideTitle } from "./viewer-slides";

/** Gherkin: tests/features/qa-followups-ae0416.feature. */

function project(
  overrides: Partial<CarouselProjectResponse>,
): CarouselProjectResponse {
  return {
    id: "p1",
    topic: "Topic",
    title: null,
    design_tokens: null,
    ...overrides,
  } as CarouselProjectResponse;
}

describe("viewerSlidePaths (AE-0416)", () => {
  // Scenario: The viewer counts the real slide list
  it("builds one path per real slide, in slide order", () => {
    expect(
      viewerSlidePaths({
        project: project({}),
        language: "pt",
        slideNumbers: [3, 1, 2],
      }),
    ).toEqual(["slide_1.jpg", "slide_2.jpg", "slide_3.jpg"]);
  });

  // Scenario: The viewer falls back to the design tokens without a slide list
  it("falls back to the rendered design-token slides", () => {
    const tokens = {
      images: { slides: ["raw_1.jpg"], rendered_slides_pt: ["pt_1.jpg"] },
    };
    const source = project({ design_tokens: tokens });
    expect(viewerSlidePaths({ project: source, language: "pt" })).toEqual([
      "pt_1.jpg",
    ]);
    expect(viewerSlidePaths({ project: source, language: "en" })).toEqual([
      "pt_1.jpg",
    ]);
  });

  it("uses the legacy slides list, or nothing, without rendered slides", () => {
    const legacy = project({
      design_tokens: { images: { slides: ["a.jpg"] } },
    });
    expect(viewerSlidePaths({ project: legacy, language: "pt" })).toEqual([
      "a.jpg",
    ]);
    expect(viewerSlidePaths({ project: project({}), language: "en" })).toEqual(
      [],
    );
  });
});

describe("viewerSlideTitle (AE-0416)", () => {
  it("uses the English title on the EN tab and the PT title otherwise", () => {
    const both = project({ title: "Título", title_en: "Title" });
    expect(viewerSlideTitle(both, "en")).toBe("Title");
    expect(viewerSlideTitle(both, "pt")).toBe("Título");
  });

  it("falls back to the PT title, then the topic", () => {
    expect(viewerSlideTitle(project({ title: "Título" }), "en")).toBe("Título");
    expect(viewerSlideTitle(project({}), "en")).toBe("Topic");
  });
});
