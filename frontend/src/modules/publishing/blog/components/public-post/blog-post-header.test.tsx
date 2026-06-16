import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BlogPostHeader } from "./blog-post-header";
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

describe("BlogPostHeader Component", () => {
  // Scenario: Blog post header renders badge with design tokens
  describe("Given a BlogPostHeader with cybersecurity design tokens", () => {
    const defaultProps = {
      title: "Understanding Zero Trust Architecture",
      badge: "Cybersecurity",
      design: MOCK_DESIGN,
    };

    describe("When the component is rendered", () => {
      it("Then the badge text comes from layout.badge_label", () => {
        render(<BlogPostHeader {...defaultProps} />);
        expect(screen.getByText("Cybersecurity")).toBeInTheDocument();
      });

      it("Then the title is displayed", () => {
        render(<BlogPostHeader {...defaultProps} />);
        expect(
          screen.getByText("Understanding Zero Trust Architecture"),
        ).toBeInTheDocument();
      });

      it("Then the badge color uses colors.primary", () => {
        render(<BlogPostHeader {...defaultProps} />);
        const badge = screen.getByText("Cybersecurity");
        const badgeContainer = badge.closest("div");
        expect(badgeContainer).toHaveStyle({
          color: MOCK_DESIGN.colors.primary,
        });
      });

      it("Then the badge uses font_family_badge", () => {
        render(<BlogPostHeader {...defaultProps} />);
        const badge = screen.getByText("Cybersecurity");
        const badgeContainer = badge.closest("div");
        expect(badgeContainer?.style.fontFamily).toMatch(/Mono/);
      });
    });

    describe("When a subtitle is provided", () => {
      it("Then the subtitle is rendered", () => {
        render(<BlogPostHeader {...defaultProps} subtitle="A deep dive" />);
        expect(screen.getByText("A deep dive")).toBeInTheDocument();
      });
    });

    describe("When no subtitle is provided", () => {
      it("Then no subtitle element is rendered", () => {
        render(<BlogPostHeader {...defaultProps} />);
        expect(screen.queryByText("A deep dive")).not.toBeInTheDocument();
      });
    });

    describe("When the swipe text is rendered", () => {
      it("Then it displays the swipe_text from design layout", () => {
        render(<BlogPostHeader {...defaultProps} />);
        expect(
          screen.getByText(MOCK_DESIGN.layout.swipe_text),
        ).toBeInTheDocument();
      });
    });
  });
});
