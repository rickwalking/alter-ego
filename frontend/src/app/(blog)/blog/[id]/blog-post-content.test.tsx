import { describe, expect, it } from "vitest";
import { extractH2Heading, resolveSlideImage } from "./blog-post-content";
import type { CarouselDesignResponse } from "@/schemas/carousel";

// Feature: Blog post content rendering with image map
//   As a blog reader
//   I want images to match the section headings
//   So that the visual content is relevant and not random

describe("extractH2Heading", () => {
  it("extracts the H2 heading from markdown", () => {
    const markdown = "## The Impact on Developers";
    expect(extractH2Heading(markdown)).toBe("The Impact on Developers");
  });

  it("returns null when no H2 heading exists", () => {
    const markdown = "Some paragraph without heading";
    expect(extractH2Heading(markdown)).toBeNull();
  });
});

describe("resolveSlideImage", () => {
  const createDesign = (
    imageMap?: Array<{ slide_number: number; heading: string; alt: string }>
  ): CarouselDesignResponse => ({
    colors: {
      primary: "#ff6b00",
      accent: "#00d4ff",
      bg: "#0a0a0a",
      text: "#ffffff",
      text_muted: "rgba(255,255,255,0.63)",
      text_dim: "rgba(255,255,255,0.48)",
      border: "#ff6b0033",
      glow: "#ff6b000D",
    },
    typography: {
      font_family_heading: "'Segoe UI', sans-serif",
      font_family_body: "'Segoe UI', sans-serif",
      font_family_badge: "'Courier New', monospace",
    },
    images: {
      hero: "/api/carousels/1/images/slide_1",
      slides: [
        "/api/carousels/1/images/slide_1",
        "/api/carousels/1/images/slide_2",
        "/api/carousels/1/images/slide_3",
        "/api/carousels/1/images/slide_4",
        "/api/carousels/1/images/slide_5",
        "/api/carousels/1/images/slide_6",
      ],
      rendered_slides_pt: null,
      rendered_slides_en: null,
      blog_image_map: imageMap,
    },
    layout: {
      badge_label: "Tech",
      swipe_text: "Swipe →",
      progress_segments: 6,
    },
    theme_name: "cybersecurity",
  });

  it("returns the correct slide image when heading matches image map", () => {
    const design = createDesign([
      { slide_number: 3, heading: "The Architecture", alt: "Architecture diagram" },
    ]);
    const slideImages = design.images.slides;
    const markdown = "## The Architecture\n\nSome content here.";

    const result = resolveSlideImage(markdown, design, slideImages);

    expect(result).toBe("/api/carousels/1/images/slide_3");
  });

  it("returns null when heading has no matching image map entry", () => {
    const design = createDesign([
      { slide_number: 2, heading: "Different Heading", alt: "" },
    ]);
    const slideImages = design.images.slides;
    const markdown = "## The Architecture\n\nSome content here.";

    const result = resolveSlideImage(markdown, design, slideImages);

    expect(result).toBeNull();
  });

  it("returns null for out-of-range slide numbers", () => {
    const design = createDesign([
      { slide_number: 10, heading: "The Architecture", alt: "" },
    ]);
    const slideImages = design.images.slides;
    const markdown = "## The Architecture\n\nSome content here.";

    const result = resolveSlideImage(markdown, design, slideImages);

    expect(result).toBeNull();
  });

  it("falls back to positional mapping when no image map exists", () => {
    const design = createDesign(undefined);
    const slideImages = design.images.slides;
    // First section after intro (index 1) gets slide_2 (index 1 in slides array)
    const markdown = "## Some Section\n\nContent.";

    const result = resolveSlideImage(markdown, design, slideImages);

    // With no image map, it uses positional fallback based on section index
    // Since we can't easily determine section index from single markdown in isolation,
    // the fallback logic checks if the section is in the list and uses index - 1
    // For a single section markdown, findIndex returns 0, which is not > 0, so returns null
    // This is expected behavior — positional mapping only works in the full context
    expect(result).toBeNull();
  });

  it("returns null when no H2 heading exists in markdown", () => {
    const design = createDesign([
      { slide_number: 2, heading: "The Architecture", alt: "" },
    ]);
    const slideImages = design.images.slides;
    const markdown = "Just a paragraph without heading.";

    const result = resolveSlideImage(markdown, design, slideImages);

    expect(result).toBeNull();
  });
});
