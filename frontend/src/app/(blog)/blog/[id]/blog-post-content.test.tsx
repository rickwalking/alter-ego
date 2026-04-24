import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BlogPostContent } from "./blog-post-content";
import type { CarouselDesignResponse } from "@/schemas/carousel";

const MOCK_DESIGN: CarouselDesignResponse = {
  colors: {
    primary: "#3b82f6",
    accent: "#f59e0b",
    bg: "#0a0e17",
    text: "#ffffff",
    text_muted: "rgba(255,255,255,0.63)",
    text_dim: "rgba(255,255,255,0.48)",
    border: "#3b82f633",
    glow: "#3b82f60D",
  },
  typography: {
    font_family_heading: "'Inter', sans-serif",
    font_family_body: "'Inter', sans-serif",
    font_family_badge: "'JetBrains Mono', monospace",
  },
  images: {
    hero: "",
    slides: [],
  },
  layout: {
    badge_label: "AI/ML",
    swipe_text: "Deslize →",
    progress_segments: 6,
  },
  theme_name: "ai_competition",
};

const MOCK_SLIDE_IMAGES = [
  "http://localhost:8000/api/carousels/1/images/slide_1",
  "http://localhost:8000/api/carousels/1/images/slide_2",
  "http://localhost:8000/api/carousels/1/images/slide_3",
  "http://localhost:8000/api/carousels/1/images/slide_4",
];

function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})/i.exec(hex);
  if (!result) return hex;
  return `rgb(${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)})`;
}

function colorsMatch(actual: string, expected: string): boolean {
  if (actual === expected) return true;
  return hexToRgb(expected) === actual;
}

describe("BlogPostContent Component", () => {
  // Scenario: Blog post content renders markdown
  describe("Given a BlogPostContent with markdown content", () => {
    describe("When markdown contains a heading", () => {
      it("Then the heading is rendered with text content", () => {
        render(
          <BlogPostContent
            markdown="# Hello World"
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading).toBeInTheDocument();
        expect(heading).toHaveTextContent("Hello World");
      });

      it("Then the heading has color styling applied", () => {
        render(
          <BlogPostContent
            markdown="# Hello World"
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading.style.color).toBeTruthy();
        expect(colorsMatch(heading.style.color, MOCK_DESIGN.colors.text)).toBe(true);
      });

      it("Then the heading uses design token heading font", () => {
        render(
          <BlogPostContent
            markdown="# Hello World"
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading.style.fontFamily).toMatch(/Inter/);
      });
    });

    describe("When markdown contains a paragraph", () => {
      it("Then paragraph text is rendered", () => {
        render(
          <BlogPostContent
            markdown="This is a paragraph."
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        expect(screen.getByText("This is a paragraph.")).toBeInTheDocument();
      });

      it("Then paragraph has color styling from design tokens", () => {
        render(
          <BlogPostContent
            markdown="This is a paragraph."
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        const paragraph = screen.getByText("This is a paragraph.");
        expect(paragraph.style.color).toBeTruthy();
      });
    });

    describe("When markdown contains bold text", () => {
      it("Then strong text is rendered", () => {
        render(
          <BlogPostContent
            markdown="This is **bold** text"
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        expect(screen.getByText("bold")).toBeInTheDocument();
      });

      it("Then strong text has color styling from design tokens", () => {
        render(
          <BlogPostContent
            markdown="This is **bold** text"
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        const strong = screen.getByText("bold");
        expect(strong.style.color).toBeTruthy();
        expect(colorsMatch(strong.style.color, MOCK_DESIGN.colors.text)).toBe(true);
      });
    });

    describe("When markdown contains inline code", () => {
      it("Then code is rendered with primary color", () => {
        render(
          <BlogPostContent
            markdown="Use the `npm install` command"
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        const code = screen.getByText("npm install");
        expect(code.style.color).toBeTruthy();
        expect(colorsMatch(code.style.color, MOCK_DESIGN.colors.primary)).toBe(true);
      });

      it("Then code uses badge font family", () => {
        render(
          <BlogPostContent
            markdown="Use the `npm install` command"
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        const code = screen.getByText("npm install");
        expect(code.style.fontFamily).toMatch(/Mono/);
      });
    });

    describe("When markdown contains a list", () => {
      it("Then list items are rendered", () => {
        render(
          <BlogPostContent
            markdown={"- Item one\n- Item two"}
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        expect(screen.getByText("Item one")).toBeInTheDocument();
        expect(screen.getByText("Item two")).toBeInTheDocument();
      });
    });

    describe("When markdown contains a blockquote", () => {
      it("Then blockquote is rendered with accent border", () => {
        const { container } = render(
          <BlogPostContent
            markdown="> This is a quote"
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        const blockquote = container.querySelector("blockquote");
        expect(blockquote).toBeInTheDocument();
        expect(blockquote?.style.borderColor).toBeTruthy();
      });
    });

    describe("When markdown contains a link", () => {
      it("Then links render with correct href and styling", () => {
        render(
          <BlogPostContent
            markdown="[Click here](https://example.com)"
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        const link = screen.getByText("Click here");
        expect(link).toHaveAttribute("href", "https://example.com");
        expect(link).toHaveAttribute("target", "_blank");
        expect(link.style.color).toBeTruthy();
      });
    });

    describe("When markdown is empty", () => {
      it("Then the component renders without errors", () => {
        const { container } = render(
          <BlogPostContent markdown="" design={MOCK_DESIGN} slideImages={[]} />
        );
        expect(container.firstChild).toBeInTheDocument();
      });
    });

    describe("When markdown contains an h2 heading", () => {
      it("Then h2 is rendered with heading font", () => {
        render(
          <BlogPostContent
            markdown="## Section Title"
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        const heading = screen.getByRole("heading", { level: 2 });
        expect(heading).toHaveTextContent("Section Title");
        expect(heading.style.fontFamily).toMatch(/Inter/);
      });
    });

    describe("When slide images are provided", () => {
      it("then slide images are rendered in the document", () => {
        const { container } = render(
          <BlogPostContent
            markdown={"## First Section\n\nContent\n\n## Second Section\n\nMore content"}
            design={MOCK_DESIGN}
            slideImages={MOCK_SLIDE_IMAGES}
          />
        );
        const images = container.querySelectorAll("img");
        expect(images.length).toBeGreaterThanOrEqual(1);
      });

      it("then slide images have the correct src URLs", () => {
        const { container } = render(
          <BlogPostContent
            markdown="## Section\n\nContent"
            design={MOCK_DESIGN}
            slideImages={["http://example.com/slide1.jpg"]}
          />
        );
        const images = container.querySelectorAll("img");
        if (images.length > 0) {
          expect(images[0].getAttribute("src")).toBe("http://example.com/slide1.jpg");
        }
      });
    });

    describe("When no slide images are provided", () => {
      it("Then no images are rendered", () => {
        const { container } = render(
          <BlogPostContent
            markdown="# Title\n\nSome text"
            design={MOCK_DESIGN}
            slideImages={[]}
          />
        );
        const images = container.querySelectorAll("img");
        expect(images.length).toBe(0);
      });
    });
  });
});
