import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeonBadge } from "@/components/atoms/neon-badge";

const LABEL = "Live";
const BASE_CLASSES = [
  "inline-flex",
  "items-center",
  "gap-1.5",
  "rounded-full",
  "font-semibold",
  "transition-colors",
];
const DOT_CLASSES = ["h-1.5", "w-1.5", "rounded-full", "shrink-0"];

function getDot(badge: HTMLElement): Element | null {
  return badge.querySelector('[aria-hidden="true"]');
}

describe("NeonBadge variant classes", () => {
  // Scenario: Cyan badge renders label text
  it("applies the base layout classes", () => {
    render(<NeonBadge>{LABEL}</NeonBadge>);
    expect(screen.getByText(LABEL)).toHaveClass(...BASE_CLASSES);
  });

  it("defaults to the md size and a transparent border", () => {
    render(<NeonBadge>{LABEL}</NeonBadge>);
    const badge = screen.getByText(LABEL);
    expect(badge).toHaveClass("px-2.5", "py-0.5", "text-xs");
    expect(badge).toHaveClass("border-transparent");
    expect(badge).not.toHaveClass("bg-transparent");
    expect(badge).not.toHaveClass("text-[10px]");
  });

  it("applies the sm size classes when requested", () => {
    render(<NeonBadge size="sm">{LABEL}</NeonBadge>);
    const badge = screen.getByText(LABEL);
    expect(badge).toHaveClass("px-2", "text-[10px]");
    expect(badge).not.toHaveClass("text-xs");
  });

  it("applies the outline classes when outline is true", () => {
    render(<NeonBadge outline>{LABEL}</NeonBadge>);
    const badge = screen.getByText(LABEL);
    expect(badge).toHaveClass("border", "bg-transparent");
    expect(badge).not.toHaveClass("border-transparent");
  });

  it("treats the legacy outline variant as an outlined badge", () => {
    render(<NeonBadge variant="outline">{LABEL}</NeonBadge>);
    expect(screen.getByText(LABEL)).toHaveClass("border", "bg-transparent");
  });

  it("keeps the filled classes when outline is explicitly false", () => {
    render(<NeonBadge outline={false}>{LABEL}</NeonBadge>);
    const badge = screen.getByText(LABEL);
    expect(badge).toHaveClass("border-transparent");
    expect(badge).not.toHaveClass("bg-transparent");
  });
});

describe("NeonBadge dot indicator", () => {
  // Scenario: Dot indicator renders when enabled
  it("renders the dot with its sizing classes", () => {
    render(<NeonBadge dot>{LABEL}</NeonBadge>);
    const dot = getDot(screen.getByText(LABEL));
    expect(dot).not.toBeNull();
    expect(dot).toHaveClass(...DOT_CLASSES);
    expect(dot).not.toHaveClass("animate-pulse");
  });

  it("renders an animated dot when pulse is set", () => {
    render(<NeonBadge pulse>{LABEL}</NeonBadge>);
    const dot = getDot(screen.getByText(LABEL));
    expect(dot).toHaveClass(...DOT_CLASSES);
    expect(dot).toHaveClass("animate-pulse", "motion-reduce:animate-none");
  });

  it("renders no dot by default", () => {
    render(<NeonBadge>{LABEL}</NeonBadge>);
    expect(getDot(screen.getByText(LABEL))).toBeNull();
  });
});

describe("NeonBadge display name", () => {
  it("exposes a stable display name", () => {
    expect(NeonBadge.displayName).toBe("NeonBadge");
  });
});
