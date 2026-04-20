import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BlogPostHero } from "./blog-post-hero";
import type { CarouselDesignResponse } from "@/schemas/carousel";

const MOCK_DESIGN: CarouselDesignResponse = {
  colors: {
    primary: "#ef4444",
    accent: "#00d4ff",
    bg: "#0a0e17",
    text: "#ffffff",
    text_muted: "rgba(255,255,255,0.63)",
    text_dim: "rgba(255,255,255,0.48)",
    border: "#ef444433",
    glow: "#ef44440D",
  },
  typography: {
    font_family_heading: "'Inter', sans-serif",
    font_family_body: "'Inter', sans-serif",
    font_family_badge: "'JetBrains Mono', monospace",
  },
  images: {
    hero: "/api/carousels/1/images/hero",
    slides: [],
  },
  layout: {
    badge_label: "Cybersecurity",
    swipe_text: "Swipe →",
    progress_segments: 10,
  },
  theme_name: "cybersecurity",
};

describe("BlogPostHero Component", () => {
  // Scenario: Blog post hero renders image with design styling
  describe("Given a BlogPostHero with an image URL and design tokens", () => {
    const defaultProps = {
      imageUrl: "/api/carousels/1/images/hero",
      title: "Understanding Zero Trust",
      design: MOCK_DESIGN,
    };

    describe("When the component is rendered", () => {
      it("Then the image is rendered with correct alt text", () => {
        render(<BlogPostHero {...defaultProps} />);
        const img = screen.getByRole("img");
        expect(img).toHaveAttribute("alt", "Understanding Zero Trust");
      });

      it("Then the image src points to the provided URL", () => {
        render(<BlogPostHero {...defaultProps} />);
        const img = screen.getByRole("img");
        expect(img).toHaveAttribute("src", "/api/carousels/1/images/hero");
      });

      it("Then the container has border styling from design tokens", () => {
        const { container } = render(<BlogPostHero {...defaultProps} />);
        const wrapper = container.firstElementChild as HTMLElement;
        expect(wrapper.style.border).toBeTruthy();
        expect(wrapper.style.border).toContain("1px solid");
      });

      it("Then the container has shadow styling from design tokens", () => {
        const { container } = render(<BlogPostHero {...defaultProps} />);
        const wrapper = container.firstElementChild as HTMLElement;
        expect(wrapper.style.boxShadow).toBeTruthy();
      });
    });
  });
});