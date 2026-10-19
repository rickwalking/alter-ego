import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { BlogPostContent } from "./blog-post-content";
import type { BlogImage, BlogSection } from "@/schemas/blog-document";
import type { CarouselDesignResponse } from "@/schemas/carousel";

// Feature: Public blog body never renders carousel slides (AE-0422)
// frontend/tests/features/blog_no_carousel_slides_ae0422.feature
// Feature: Public blog renders the v2 document (AE-0423)
// frontend/tests/features/blog_sections_ae0423.feature

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

function section(
  id: string,
  heading: string | null,
  extra: { body: string; image?: BlogImage | null },
): BlogSection {
  return { id, heading, body_md: extra.body, image: extra.image ?? null };
}

describe("BlogPostContent (AE-0422, AE-0423)", () => {
  // Scenario: No rendered carousel slide appears in the body (AE-0422)
  // Scenario: No carousel slide image is ever used (AE-0423)
  it("renders text sections without any rendered carousel slide", () => {
    const { container } = render(
      <BlogPostContent
        sections={[
          section("sec_1", null, { body: "Intro paragraph." }),
          section("sec_2", "The Architecture", { body: "Body." }),
        ]}
        design={createDesign()}
      />,
    );

    const sources = renderedImageSources(container);
    expect(sources.some((src) => src.includes("/slide-images/"))).toBe(false);
    expect(screen.getByText("Intro paragraph.")).toBeInTheDocument();
    expect(screen.getByText("Body.")).toBeInTheDocument();
  });

  // Scenario: Each section renders its own heading, body and image
  // Scenario: Outstanding section image alt is never empty in the DOM
  it("renders each section's own image with its stored alt", () => {
    render(
      <BlogPostContent
        sections={[
          section("sec_1", "Um", {
            body: "Corpo um.",
            image: {
              url: "https://cdn.example/1.jpg",
              alt: "Diagrama do fluxo",
            },
          }),
          section("sec_2", "Dois", {
            body: "Corpo dois.",
            image: {
              url: "https://cdn.example/2.jpg",
              alt: "Gráfico de custos",
            },
          }),
        ]}
        design={createDesign()}
      />,
    );

    const images = screen.getAllByRole("img");
    expect(images.map((img) => img.getAttribute("alt"))).toEqual([
      "Diagrama do fluxo",
      "Gráfico de custos",
    ]);
    const paths = images.map(
      (img) => new URL(img.getAttribute("src") ?? "", "http://x").pathname,
    );
    expect(paths).toEqual(["/1.jpg", "/2.jpg"]);
    expect(screen.getByRole("heading", { name: "Um" })).toBeInTheDocument();
    expect(screen.getByText("Corpo dois.")).toBeInTheDocument();
  });

  // Scenario: A section with no image renders text only
  it("renders a section heading and body with no placeholder image", () => {
    const { container } = render(
      <BlogPostContent
        sections={[section("sec_1", "The Architecture", { body: "Body." })]}
        design={createDesign()}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "The Architecture" }),
    ).toBeInTheDocument();
    expect(container.querySelectorAll("img")).toHaveLength(0);
  });

  // Scenario: Theme still comes from the carousel design (AE-0422)
  it("applies the design typography without taking any design image", () => {
    const { container } = render(
      <BlogPostContent
        sections={[section("sec_1", "Heading", { body: "Body." })]}
        design={createDesign()}
      />,
    );

    const heading = screen.getByRole("heading", { name: "Heading" });
    expect(heading.style.fontFamily).toMatch(/Segoe UI/);
    expect(renderedImageSources(container)).toEqual([]);
  });

  // Scenario: The title renders exactly once
  it("never renders an H1 from a section body", () => {
    const { container } = render(
      <BlogPostContent
        sections={[
          section("sec_1", null, { body: "# Stray title\n\nBody text." }),
        ]}
        design={createDesign()}
      />,
    );

    expect(container.querySelectorAll("h1")).toHaveLength(0);
    expect(
      screen.getByRole("heading", { level: 2, name: "Stray title" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Body text.")).toBeInTheDocument();
  });

  // Scenario: Markdown is rendered through the sanitizing allow-list
  it("does not render raw HTML or markdown images from a body", () => {
    const { container } = render(
      <BlogPostContent
        sections={[
          section("sec_1", "H", {
            body: "<script>alert(1)</script>\n\n![slide](/api/carousels/1/slide-images/pt/slide_1.jpg)\n\nSafe.",
          }),
        ]}
        design={createDesign()}
      />,
    );

    expect(container.querySelector("script")).toBeNull();
    expect(container.innerHTML).not.toContain("alert(1)</script>");
    expect(renderedImageSources(container)).toEqual([]);
    expect(screen.getByText("Safe.")).toBeInTheDocument();
  });

  // Scenario: A design payload with blog_image_map is ignored (AE-0422)
  it("ignores a legacy blog_image_map and shows no slide image", () => {
    const design = createDesign({
      blog_image_map: [
        { slide_number: 2, heading: "The Architecture", alt: "" },
      ],
    });
    const { container } = render(
      <BlogPostContent
        sections={[section("sec_1", "The Architecture", { body: "Body." })]}
        design={design}
      />,
    );

    expect(renderedImageSources(container)).toEqual([]);
  });
});
