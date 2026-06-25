import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { BADGE_COLORS, type NeonBadgeVariant } from "@/schemas/neon-badge";

const VARIANTS: NeonBadgeVariant[] = [
  "cyan",
  "magenta",
  "teal",
  "amber",
  "green",
  "red",
];

// Feature: NeonBadge Component
describe("NeonBadge Component", () => {
  describe("When a cyan variant badge is rendered", () => {
    // Scenario: Cyan badge renders label text
    it("Then the badge text should be visible", () => {
      render(<NeonBadge variant="cyan">Active</NeonBadge>);
      expect(screen.getByText("Active")).toBeInTheDocument();
    });

    it("Then it should use cyan colors from BADGE_COLORS", () => {
      render(<NeonBadge variant="cyan">Active</NeonBadge>);
      const badge = screen.getByText("Active");
      expect(badge).toHaveStyle({
        color: BADGE_COLORS.cyan.text,
        background: BADGE_COLORS.cyan.bg,
      });
    });
  });

  describe("When each neon variant is rendered", () => {
    it.each(VARIANTS)(
      "Then variant %s should apply matching colors",
      (variant) => {
        render(<NeonBadge variant={variant}>{variant}</NeonBadge>);
        const badge = screen.getByText(variant);
        expect(badge).toHaveStyle({
          color: BADGE_COLORS[variant].text,
          background: BADGE_COLORS[variant].bg,
        });
      },
    );
  });

  describe("When dot prop is true", () => {
    // Scenario: Dot indicator renders when enabled
    it("Then a dot indicator should be rendered", () => {
      const { container } = render(
        <NeonBadge variant="green" dot>
          Live
        </NeonBadge>,
      );
      expect(
        container.querySelector('[aria-hidden="true"]'),
      ).toBeInTheDocument();
    });

    it("Then the dot should use the variant text color", () => {
      const { container } = render(
        <NeonBadge variant="green" dot>
          Live
        </NeonBadge>,
      );
      const dot = container.querySelector('[aria-hidden="true"]');
      expect(dot).toHaveStyle({ background: BADGE_COLORS.green.text });
    });
  });

  describe("When pulse prop is true", () => {
    // Scenario: a live state animates the dot, reduced-motion safe
    it("Then a dot renders even without dot, and it animates", () => {
      const { container } = render(
        <NeonBadge variant="cyan" pulse>
          Active
        </NeonBadge>,
      );
      const dot = container.querySelector('[aria-hidden="true"]');
      expect(dot).toBeInTheDocument();
      expect(dot).toHaveClass("animate-pulse");
      expect(dot).toHaveClass("motion-reduce:animate-none");
    });

    it("Then a non-pulsing dot does not animate", () => {
      const { container } = render(
        <NeonBadge variant="cyan" dot>
          Idle
        </NeonBadge>,
      );
      expect(container.querySelector(".animate-pulse")).toBeNull();
    });
  });

  describe("When outline prop is true", () => {
    it("Then background should be transparent", () => {
      render(
        <NeonBadge variant="cyan" outline>
          Outline
        </NeonBadge>,
      );
      expect(screen.getByText("Outline")).toHaveStyle({
        background: "transparent",
      });
    });

    it("Then border color should match variant text", () => {
      render(
        <NeonBadge variant="magenta" outline>
          Outline
        </NeonBadge>,
      );
      expect(screen.getByText("Outline")).toHaveStyle({
        borderColor: BADGE_COLORS.magenta.text,
      });
    });
  });

  describe("When outline legacy variant is used", () => {
    // Scenario: Outline legacy maps to cyan outline styling
    it("Then the badge should render with transparent background", () => {
      render(<NeonBadge variant="outline">Outline</NeonBadge>);
      expect(screen.getByText("Outline")).toHaveStyle({
        background: "transparent",
      });
    });
  });

  describe("When legacy shadcn variants are used", () => {
    it("Then default maps to cyan colors", () => {
      render(<NeonBadge variant="default">Default</NeonBadge>);
      expect(screen.getByText("Default")).toHaveStyle({
        color: BADGE_COLORS.cyan.text,
      });
    });

    it("Then secondary maps to teal colors", () => {
      render(<NeonBadge variant="secondary">Secondary</NeonBadge>);
      expect(screen.getByText("Secondary")).toHaveStyle({
        color: BADGE_COLORS.teal.text,
      });
    });

    it("Then destructive maps to red colors", () => {
      render(<NeonBadge variant="destructive">Destructive</NeonBadge>);
      expect(screen.getByText("Destructive")).toHaveStyle({
        color: BADGE_COLORS.red.text,
      });
    });
  });

  describe("When size prop is set", () => {
    it("Then sm size should include compact padding classes", () => {
      render(<NeonBadge size="sm">Small</NeonBadge>);
      expect(screen.getByText("Small").className).toMatch(/text-\[10px\]/);
    });

    it("Then md size should include default text classes", () => {
      render(<NeonBadge size="md">Medium</NeonBadge>);
      expect(screen.getByText("Medium").className).toMatch(/text-xs/);
    });
  });

  describe("When custom className is provided", () => {
    it("Then className should be merged", () => {
      render(<NeonBadge className="custom-badge">Tagged</NeonBadge>);
      expect(screen.getByText("Tagged")).toHaveClass("custom-badge");
    });
  });
});
