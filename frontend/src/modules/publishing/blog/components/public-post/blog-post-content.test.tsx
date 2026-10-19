import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { BlogPostContent } from "./blog-post-content";
import type { CarouselDesignResponse } from "@/schemas/carousel";

// Feature: Public blog body never renders carousel slides (AE-0422)
// frontend/tests/features/blog_no_carousel_slides_ae0422.feature

function createDesign(
  overrides: Partial<CarouselDesignResponse["images"]> = {},
): CarouselDesignResponse {
  return {
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
      ],
      rendered_slides_pt: [
        "/api/carousels/1/slide-images/pt/slide_1.jpg",
        "/api/carousels/1/slide-images/pt/slide_2.jpg",
      ],
      rendered_slides_en: null,
      blog_image_map: [
        { slide_number: 2, heading: "The Architecture", alt: "" },
      ],
      ...overrides,
    },
    layout: {
      badge_label: "Tech",
      swipe_text: "Swipe →",
      progress_segments: 3,
    },
    theme_name: "cybersecurity",
  };
}

function renderedImageSources(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll("img")).map(
    (img) => img.getAttribute("src") ?? "",
  );
}

describe("BlogPostContent (AE-0422)", () => {
  // Scenario: No rendered carousel slide appears in the body
  //   Given the carousel design exposes rendered_slides_pt
  //   When an anonymous visitor opens /blog/{id}
  //   Then no image in the article body has a src containing "/slide-images/"
  //   And the article body renders only text sections
  it("renders text sections without any rendered carousel slide", () => {
    const { container } = render(
      <BlogPostContent
        markdown={"# Title\n\nIntro paragraph.\n\n## The Architecture\n\nBody."}
        design={createDesign()}
      />,
    );

    const sources = renderedImageSources(container);
    expect(sources.some((src) => src.includes("/slide-images/"))).toBe(false);
    expect(screen.getByText("Intro paragraph.")).toBeInTheDocument();
    expect(screen.getByText("Body.")).toBeInTheDocument();
  });

  // Scenario: A section with no image renders text only
  //   Given a section whose image is absent
  //   When the blog page renders
  //   Then that section shows its heading and body text
  //   And no placeholder broken image is shown
  it("renders a section heading and body with no placeholder image", () => {
    const { container } = render(
      <BlogPostContent
        markdown={"## The Architecture\n\nBody."}
        design={createDesign()}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "The Architecture" }),
    ).toBeInTheDocument();
    expect(container.querySelectorAll("img")).toHaveLength(0);
  });

  // Scenario: Theme still comes from the carousel design
  //   Given the carousel design exposes colors and typography
  //   When the blog page renders
  //   Then the section headings use the design typography
  //   And no image URL is taken from the design
  it("applies the design typography without taking any design image", () => {
    const design = createDesign();
    const { container } = render(
      <BlogPostContent markdown={"## Heading\n\nBody."} design={design} />,
    );

    const heading = screen.getByRole("heading", { name: "Heading" });
    expect(heading.style.fontFamily).toMatch(/Segoe UI/);
    expect(renderedImageSources(container)).toEqual([]);
  });

  // Scenario: The title is rendered exactly once
  //   Given the stored legacy markdown starts with "# <title>"
  //   When the blog page renders
  //   Then the page contains exactly one H1 with the post title
  it("strips the leading H1 so the body has no duplicate title", () => {
    render(
      <BlogPostContent
        markdown={"# Opinião impopular\n\nBody text."}
        design={createDesign()}
      />,
    );

    expect(
      screen.queryByRole("heading", { name: "Opinião impopular" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Body text.")).toBeInTheDocument();
  });

  // Scenario: A design payload with blog_image_map is ignored
  //   Given the carousel design payload still contains blog_image_map
  //   When the public blog page renders the post
  //   Then the body does not map any image positionally
  //   And no carousel slide image is shown
  it("ignores a legacy blog_image_map and shows no slide image", () => {
    const design = createDesign({
      blog_image_map: [
        { slide_number: 2, heading: "The Architecture", alt: "" },
      ],
      slides: [
        "/api/carousels/1/images/slide_1",
        "/api/carousels/1/images/slide_2",
      ],
    });
    const { container } = render(
      <BlogPostContent
        markdown={"## The Architecture\n\nBody."}
        design={design}
      />,
    );

    expect(renderedImageSources(container)).toEqual([]);
  });
});
